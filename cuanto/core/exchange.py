"""The exchange format: plain JSON, so other tools can send rates, a schedule and crew into Cuánto, and take
a budget (a locked one, for invoicing) back out. Nothing here knows about any other app; the format is
written up in docs/exchange.md.

In (File › Import JSON…):

    {"format": "cuanto.exchange", "version": 1,
     "rates":    [{"name": "Gaffer", "department": "Electric", "union": true, "local": "IATSE 728",
                   "rate": "725", "unit": "days", "fringes": ["FICA"]}],
     "schedule": {"globals": {"shoot_days": 22, "prep_days": 10}},
     "crew":     [{"role": "Gaffer", "name": "A. Rivera", "account": "2901", "rate": "725", "unit": "days",
                   "units": "shoot_days", "fringes": ["FICA", "Union P&H"]}]}

  rates go into the rate library (an entry that's already there gets the new numbers); the schedule's globals
  are set on the open budget (made if missing); crew become lines in the open budget's matching account (by
  code, else by account or category name, else "Imported Crew"), and importing the same crew again updates
  those lines instead of adding them twice.

Out (File › Export JSON…):

    {"format": "cuanto.budget", "version": 1, "budget": {…every field, as saved…},
     "totals": {"currency": "USD", "grand": "…", "categories": […], "accounts": […], "lines": […]}}

  money in "totals" is text with two decimals ("12500.00"), so nothing is lost to floating point. A
  "cuanto.budget" file imported back becomes a budget of its own.

Anything from outside is data: it goes through the model's from_dict() (lengths capped, unknown keys ignored,
wrong types dropped), never run or evaluated. No Qt here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from cuanto import __version__
from cuanto.core import calc, formula, money, rates
from cuanto.core.model import SECTIONS, Account, Budget, Category, Global, Line, Rate, new_id, now_iso

FORMAT_IN = "cuanto.exchange"
FORMAT_BUDGET = "cuanto.budget"
VERSION = 1
MAX_BYTES = 10_000_000  # a bigger file isn't a budget or a crew list
MAX_RECORDS = 20_000
CREW_CATEGORY = "Crew"
CREW_ACCOUNT = "Imported Crew"


class ExchangeError(ValueError):
    """A file that isn't in the exchange format; the message says what's wrong, in plain words."""


@dataclass
class Report:
    """What an import did, for a toast."""

    rates_added: int = 0
    rates_updated: int = 0
    globals_set: int = 0
    lines_added: int = 0
    lines_updated: int = 0
    skipped: int = 0

    def words(self) -> str:
        parts = []
        if self.rates_added or self.rates_updated:
            parts.append(_n(self.rates_added + self.rates_updated, "rate"))
        if self.globals_set:
            parts.append(_n(self.globals_set, "global"))
        if self.lines_added or self.lines_updated:
            parts.append(_n(self.lines_added + self.lines_updated, "crew line"))
        if not parts:
            return "Nothing to bring in."
        return (
            "Brought in "
            + (parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1])
            + "."
        )


def _n(n: int, word: str) -> str:
    return f"{n:,} {word}{'s' if n != 1 else ''}"


# ---------------------------------------------------------------------------- reading a file
def read(path: Path) -> dict:
    """A JSON file in either format. Raises ExchangeError (or OSError if it can't be opened)."""
    if path.stat().st_size > MAX_BYTES:
        raise ExchangeError(f"{path.name} is too big to be a budget or a crew list.")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (ValueError, RecursionError) as e:
        raise ExchangeError(f"{path.name} isn't JSON Cuánto can read.") from e
    return check(data, path.name)


def check(data: Any, name: str = "That file") -> dict:
    if not isinstance(data, dict) or data.get("format") not in (FORMAT_IN, FORMAT_BUDGET):
        raise ExchangeError(f"{name} isn't in Cuánto's exchange format.")
    try:
        version = int(data.get("version", 1))
    except (TypeError, ValueError):
        version = 0
    if version < 1:
        raise ExchangeError(f"{name} has no version Cuánto knows.")
    if version > VERSION:
        raise ExchangeError(f"{name} is from a newer Cuánto. Update Cuánto, then try again.")
    return data


def is_budget(data: dict) -> bool:
    return data.get("format") == FORMAT_BUDGET


# ---------------------------------------------------------------------------- out
def _m(d: Decimal) -> str:
    return f"{money.cents(d):f}"


def export_budget(b: Budget) -> dict:
    """A budget and every number in it, for another tool (an invoice, a cost report)."""
    t = calc.totals(b)
    cats, accts, lines = [], [], []
    for c in b.categories:
        s = t.categories[c.id]
        cats.append({"id": c.id, "code": c.code, "name": c.name, "section": c.section,
                     "subtotal": _m(s.subtotal), "fringes": _m(s.fringes), "total": _m(s.total)})  # fmt: skip
        for a in c.accounts:
            s = t.accounts[a.id]
            accts.append({"id": a.id, "category_id": c.id, "code": a.code, "name": a.name,
                          "subtotal": _m(s.subtotal), "fringes": _m(s.fringes), "total": _m(s.total)})  # fmt: skip
            for ln in a.lines:
                lt = t.lines[ln.id]
                lines.append({
                    "id": ln.id, "account_id": a.id, "category_code": c.code, "account_code": a.code,
                    "description": ln.description, "amount": f"{lt.amount.normalize():f}",
                    "units": f"{lt.units.normalize():f}", "unit": ln.unit, "rate": _m(lt.rate),
                    "subtotal": _m(lt.subtotal), "fringes": _m(lt.fringes), "total": _m(lt.total),
                    "problem": lt.problem,
                })  # fmt: skip
    totals = {
        "currency": b.currency,
        "sections": {s: _m(t.sections[s].total) for s in SECTIONS},
        "above_the_line": _m(t.atl.total),
        "below_the_line": _m(t.btl.total),
        "fringes": _m(t.direct.fringes),
        "adjustments": [{"id": a.id, "name": a.name, "amount": _m(a.amount)} for a in t.adjustments],
        "grand": _m(t.grand),
        "categories": cats,
        "accounts": accts,
        "lines": lines,
    }
    return {
        "format": FORMAT_BUDGET,
        "version": VERSION,
        "app": f"Cuánto {__version__}",
        "exported": now_iso(),
        "budget": b.to_dict(),
        "totals": totals,
    }


# ---------------------------------------------------------------------------- in
def budget_from(data: dict, taken: set[str]) -> Budget:
    """A "cuanto.budget" file as a budget of its own (a new id if its id is already in use)."""
    raw = data.get("budget")
    if not isinstance(raw, dict):
        raise ExchangeError("That file has no budget in it.")
    b = Budget.from_dict(raw)
    if b.id in taken:
        b.id = new_id()
    b.family = b.family or b.id
    return b


def _records(data: dict, key: str) -> list[dict]:
    raw = data.get(key)
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ExchangeError(f"“{key}” should be a list.")
    if len(raw) > MAX_RECORDS:
        raise ExchangeError(f"There are too many {key} in that file.")
    return [d for d in raw if isinstance(d, dict)]


def _text(v: Any) -> str:
    return "" if v is None or isinstance(v, (dict, list)) else str(v).strip()


def apply(data: dict, library_rates: dict[str, Rate], budget: Budget | None) -> Report:
    """Bring a "cuanto.exchange" file in: rates into `library_rates`, the schedule and crew into `budget`
    (left out when no budget is open). Changes them in place; saving is the caller's."""
    rep = Report()
    incoming = []
    for d in _records(data, "rates"):
        r = Rate.from_dict({k: v for k, v in d.items() if k not in ("id", "updated")})
        if r.name.strip():
            incoming.append(r)
        else:
            rep.skipped += 1
    rep.rates_added, rep.rates_updated = rates.merge(library_rates, incoming)
    if budget is None:
        rep.skipped += len(_schedule(data)) + len(_records(data, "crew"))
        return rep
    for name, label, value, unit in _schedule(data):
        key = formula.clean_name(name)
        if not key:
            rep.skipped += 1
            continue
        g = budget.global_named(key)
        if g is None:
            budget.globals.append(Global(name=key, label=label or name, value=value, unit=unit))
        else:
            g.value = value
            if label:
                g.label = label
        rep.globals_set += 1
    for d in _records(data, "crew"):
        if _crew_line(budget, d, rep) is None:
            rep.skipped += 1
    return rep


def _schedule(data: dict) -> list[tuple[str, str, str, str]]:
    """(name, label, value, unit) from the schedule's globals: a {name: value} map or a list of records."""
    sched = data.get("schedule")
    if not isinstance(sched, dict):
        return []
    raw = sched.get("globals")
    out = []
    if isinstance(raw, dict):
        for k, v in list(raw.items())[:MAX_RECORDS]:
            out.append((_text(k), "", _text(v), ""))
    elif isinstance(raw, list):
        for d in raw[:MAX_RECORDS]:
            if isinstance(d, dict):
                g = Global.from_dict(d)
                out.append((g.name, g.label, g.value, g.unit))
    return [x for x in out if x[0]]


def _account_for(budget: Budget, d: dict) -> Account:
    """Where a crew member's line goes: the account with their code, else one named like their department,
    else the first account of a category named like it, else Imported Crew (made once)."""
    code = _text(d.get("account")).casefold()
    dept = _text(d.get("department")).casefold()
    if code:
        for _c, a in budget.accounts():
            if a.code.strip().casefold() == code or a.name.strip().casefold() == code:
                return a
    if dept:
        for _c, a in budget.accounts():
            if a.name.strip().casefold() == dept:
                return a
        for c in budget.categories:
            if c.name.strip().casefold() == dept and c.accounts:
                return c.accounts[0]
    for _c, a in budget.accounts():
        if a.name == CREW_ACCOUNT:
            return a
    c = next((c for c in budget.categories if c.name == CREW_CATEGORY), None)
    if c is None:
        c = Category(name=CREW_CATEGORY, section="production")
        budget.categories.append(c)
    a = Account(name=CREW_ACCOUNT)
    c.accounts.append(a)
    return a


def _crew_line(budget: Budget, d: dict, rep: Report) -> Line | None:
    role, who = _text(d.get("role"))[:200], _text(d.get("name"))[:200]
    if not role and not who:
        return None
    description = f"{role} — {who}" if role and who else (role or who)
    probe = Line.from_dict({k: d.get(k) for k in ("amount", "units", "unit", "rate", "notes") if k in d})
    fr = d.get("fringes")
    names = [_text(x) for x in fr] if isinstance(fr, list) else []
    a = _account_for(budget, d)
    ln = next((x for x in a.lines if x.description.strip().casefold() == description.casefold()), None)
    if ln is None:
        ln = Line(description=description, units=rates.default_units(budget, probe.unit))
        a.lines.append(ln)
        rep.lines_added += 1
    else:
        rep.lines_updated += 1
    ln.unit = probe.unit if "unit" in d else ln.unit
    for k in ("amount", "units", "rate", "notes"):
        if k in d:
            setattr(ln, k, getattr(probe, k))
    if names:
        ln.fringes = rates.fringe_ids(budget, names)
    return ln
