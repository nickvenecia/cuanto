"""Every string on a page, worked out before anything is drawn.

build() turns a budget into DocViews, plain text in the order it reads: the Top Sheet (one row per category,
by section, then the fees and the grand total) and the Detail (every account and line under its category).
doc/render.py lays them out on paper; nothing there decides what a page says. No Qt here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from cuanto.core import calc, dates, money
from cuanto.core.model import (
    BASE_NAMES,
    KIND_NAMES,
    SECTION_NAMES,
    SECTIONS,
    STAGE_NAMES,
    SYMBOLS,
    UNIT_NAMES,
    Budget,
    Profile,
)

PAGES = [("topsheet", "Top Sheet"), ("detail", "Detail"), ("both", "Both")]


@dataclass
class Col:
    title: str
    width: float  # a share of the table's width
    align: str = "left"  # left / right / center
    mono: bool = False


@dataclass
class Row:
    cells: list[str]
    kind: str = "line"  # section / heading (a category) / account / line / fringe / subtotal
    depth: int = 0
    note: str = ""  # a second, smaller line under the name (a line's notes)


@dataclass
class Table:
    cols: list[Col]
    rows: list[Row] = field(default_factory=list)
    name_col: int = 1


@dataclass
class DocView:
    kind: str  # topsheet / detail
    title: str
    business: str = ""
    tagline: str = ""
    contact: list[str] = field(default_factory=list)
    big_label: str = ""
    big_value: str = ""
    big_sub: str = ""
    strip: list[tuple[str, str]] = field(default_factory=list)
    blocks: list[tuple[str, str]] = field(default_factory=list)
    table: Table | None = None
    totals: list[tuple[str, str, bool]] = field(default_factory=list)
    paragraphs_title: str = ""
    paragraphs: list[str] = field(default_factory=list)
    note: str = ""
    footer: str = ""


def _contact(p: Profile | None) -> list[str]:
    if p is None:
        return []
    line = "  ·  ".join(x.strip() for x in (p.email, p.phone, p.website) if x.strip())
    out = [line] if line else []
    addr = p.address.strip().replace("\n", ", ")
    if addr:
        out.append(addr)
    return out


def symbol(b: Budget) -> str:
    return SYMBOLS.get(b.currency, "")


def fmt(d: Decimal, b: Budget) -> str:
    """Money as it reads on the paper: "$12,500.00" (the currency's code after it when it has no sign)."""
    sym = symbol(b)
    return money.fmt(d, sym) if sym else f"{money.fmt(d, '')} {b.currency}"


def _qty(d: Decimal) -> str:
    return money.fmt_qty(money.cents(d)) if d != d.to_integral_value() else money.fmt_qty(d)


def _head(b: Budget, p: Profile | None, t: calc.Totals, kind: str, title: str) -> DocView:
    v = DocView(kind=kind, title=title)
    v.business = p.name if p and p.name else (b.info.company or "")
    v.tagline = p.tagline if p else ""
    v.contact = _contact(p)
    v.big_label = "Grand Total"
    v.big_value = fmt(t.grand, b)
    v.big_sub = " · ".join(x for x in (STAGE_NAMES.get(b.stage, ""), b.currency) if x)
    i = b.info
    v.strip = [
        ("Production", b.name or "Untitled Budget"),
        ("Type", KIND_NAMES.get(b.kind, "")),
        ("Shoot Dates", i.dates or "—"),
        ("Prepared", dates.fmt(dates.today())),
    ]
    blocks = []
    if i.client:
        blocks.append(("Client", i.client))
    people = "\n".join(x for x in (
        f"Director: {i.director}" if i.director else "",
        f"Producer: {i.producer}" if i.producer else "",
    ) if x)  # fmt: skip
    if i.company or people:
        blocks.append(
            ("Production Company", (i.company or v.business or "—") + (f"\n{people}" if people else ""))
        )
    where = "\n".join(x for x in (i.location, i.format) if x)
    if where:
        blocks.append(("Location & Format", where))
    v.blocks = blocks[:3]
    v.footer = b.name or "Untitled Budget"
    return v


def topsheet(b: Budget, p: Profile | None, t: calc.Totals | None = None) -> DocView:
    t = t or calc.totals(b)
    v = _head(b, p, t, "topsheet", "Top Sheet")
    table = Table(
        cols=[Col("Acct #", 0.9, mono=True), Col("Category", 4.6), Col("Fringes", 1.5, "right"), Col("Total", 1.8, "right")],
        name_col=1,
    )  # fmt: skip
    for s in SECTIONS:
        cats = [c for c in b.categories if c.section == s]
        if not cats:
            continue
        table.rows.append(Row(["", SECTION_NAMES[s], "", fmt(t.sections[s].total, b)], "section"))
        for c in cats:
            cs = t.categories[c.id]
            table.rows.append(
                Row(
                    [
                        c.code,
                        c.name or "Untitled Category",
                        fmt(cs.fringes, b) if cs.fringes else "",
                        fmt(cs.total, b),
                    ]
                )
            )
    v.table = table
    rows: list[tuple[str, str, bool]] = [
        ("Total Above the Line", fmt(t.atl.total, b), False),
        ("Total Below the Line", fmt(t.btl.total, b), False),
    ]
    if t.adjustments:
        rows.append(("Above and Below the Line", fmt(t.direct.total, b), False))
    for adj, a in zip(b.adjustments, t.adjustments, strict=False):
        label = a.name or "Fee"
        if adj.kind == "percent":
            label += f" {money.fmt_qty(money.parse(adj.rate))}%"
            if adj.base != "atl_btl":
                label += f" of {BASE_NAMES[adj.base]}"
        rows.append((label, fmt(a.amount, b), False))
    rows.append(("Grand Total", fmt(t.grand, b), True))
    v.totals = rows
    if b.info.notes.strip():
        v.paragraphs_title = "Notes"
        v.paragraphs = [x.strip() for x in b.info.notes.split("\n\n") if x.strip()]
    v.note = p.note if p else ""
    return v


def detail(b: Budget, p: Profile | None, t: calc.Totals | None = None, show_empty: bool = False) -> DocView:
    """Every category, account and line. Lines, accounts and categories that come to nothing are left out
    unless `show_empty` (a budget still being filled in prints only what has money in it)."""
    t = t or calc.totals(b)
    v = _head(b, p, t, "detail", "Budget Detail")
    v.blocks = []  # who it's for is on the top sheet
    table = Table(
        cols=[Col("Acct #", 0.9, mono=True), Col("Description", 3.6), Col("Amt", 0.7, "right"),
              Col("Units", 1.2, "right"), Col("Rate", 1.3, "right"), Col("Total", 1.6, "right")],
        name_col=1,
    )  # fmt: skip
    for c in b.categories:
        cs = t.categories[c.id]
        if not show_empty and cs.total == 0:
            continue
        table.rows.append(
            Row([c.code, c.name or "Untitled Category", "", "", "", fmt(cs.total, b)], "heading")
        )
        for a in c.accounts:
            s = t.accounts[a.id]
            if not show_empty and s.total == 0:
                continue
            table.rows.append(
                Row([a.code, a.name or "Untitled Account", "", "", "", fmt(s.total, b)], "account")
            )
            for ln in a.lines:
                lt = t.lines[ln.id]
                if not show_empty and lt.subtotal == 0:
                    continue
                units = _qty(lt.units)
                if ln.unit not in ("allow", "flat"):
                    units += f" {UNIT_NAMES[ln.unit]}"
                elif lt.units == 1:
                    units = UNIT_NAMES[ln.unit]
                table.rows.append(
                    Row(
                        ["", ln.description or "Untitled Line", _qty(lt.amount), units, fmt(lt.rate, b), fmt(lt.subtotal, b)],
                        "line",
                        depth=1,
                        note=ln.notes.strip().split("\n")[0][:200] if ln.notes.strip() else "",
                    )
                )  # fmt: skip
            if s.fringes:
                table.rows.append(Row(["", "Fringes", "", "", "", fmt(s.fringes, b)], "fringe", depth=1))
    v.table = table
    v.totals = [
        ("Total Above the Line", fmt(t.atl.total, b), False),
        ("Total Below the Line", fmt(t.btl.total, b), False),
        ("Fees", fmt(t.fees, b), False),
        ("Grand Total", fmt(t.grand, b), True),
    ]
    if not t.adjustments:
        v.totals.pop(2)
    return v


def build(b: Budget, p: Profile | None, which: str = "both") -> list[DocView]:
    """The pages to print: the top sheet, the detail, or both (top sheet first)."""
    t = calc.totals(b)
    if which == "topsheet":
        return [topsheet(b, p, t)]
    if which == "detail":
        return [detail(b, p, t)]
    return [topsheet(b, p, t), detail(b, p, t)]


def summary_text(b: Budget, p: Profile | None) -> str:
    """The top sheet as plain text, for pasting into an email."""
    v = topsheet(b, p)
    out = [b.name or "Untitled Budget", ""]
    for row in v.table.rows if v.table else []:
        if row.kind == "section":
            out.append(f"{row.cells[1]}: {row.cells[3]}")
        else:
            out.append(f"  {(row.cells[0] + ' ') if row.cells[0] else ''}{row.cells[1]}: {row.cells[3]}")
    out.append("")
    out += [f"{k}: {val}" for k, val, _s in v.totals]
    return "\n".join(out)
