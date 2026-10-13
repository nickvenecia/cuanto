"""Every number in a budget, worked out in one place. The window, the paper, the exports and the exchange
format all ask here; nothing else computes money.

    a line's subtotal   amount × units × rate, rounded to the cent (in the budget's currency)
    its fringes         each fringe on it: a percent of the subtotal (counting no more than the fringe's
                        cap, when it has one), or a flat amount for each unit (rate × amount × units)
    its total           subtotal + fringes
    an account          its lines added up; a category, its accounts; a section, its categories
    above the line      the Above the Line section; below the line: Production + Post + Other
    adjustments         in order: a percent of their base (above + below the line, below the line only, the
                        Production section only, or everything above it, earlier adjustments included), or a
                        flat amount
    grand total         above + below the line + every adjustment

Exact decimals, never floats. A problem (a global that doesn't exist, a global that uses itself, a typo in
a formula) never stops the sums: that number counts as 0 and the problem is kept, in plain words, for the
line or global it's on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from cuanto.core import formula, money
from cuanto.core.formula import FormulaError
from cuanto.core.model import BELOW_THE_LINE, SECTIONS, Budget, Fringe, Line

ZERO = Decimal(0)
ONE = Decimal(1)
HUNDRED = Decimal(100)


@dataclass
class Sum:
    """Money added up: before fringes, the fringes, and both together."""

    subtotal: Decimal = ZERO
    fringes: Decimal = ZERO
    lines: int = 0

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.fringes

    def add(self, other: Sum) -> None:
        self.subtotal += other.subtotal
        self.fringes += other.fringes
        self.lines += other.lines


@dataclass
class LineTotal:
    amount: Decimal = ONE
    units: Decimal = ONE
    rate: Decimal = ZERO
    subtotal: Decimal = ZERO
    fringes: Decimal = ZERO
    by_fringe: dict[str, Decimal] = field(default_factory=dict)  # fringe id -> its amount on this line
    problem: str = ""

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.fringes

    def as_sum(self) -> Sum:
        return Sum(self.subtotal, self.fringes, 1)


@dataclass
class AdjustmentTotal:
    id: str
    name: str
    base: Decimal  # what a percent is a percent of (ZERO for a flat one)
    amount: Decimal
    problem: str = ""


@dataclass
class Totals:
    lines: dict[str, LineTotal] = field(default_factory=dict)
    accounts: dict[str, Sum] = field(default_factory=dict)
    categories: dict[str, Sum] = field(default_factory=dict)
    sections: dict[str, Sum] = field(default_factory=dict)
    atl: Sum = field(default_factory=Sum)
    btl: Sum = field(default_factory=Sum)
    adjustments: list[AdjustmentTotal] = field(default_factory=list)
    fringes: dict[str, Decimal] = field(default_factory=dict)  # fringe id -> its total, everywhere
    fringe_lines: dict[str, int] = field(default_factory=dict)  # fringe id -> how many lines it's on
    globals: dict[str, Decimal] = field(default_factory=dict)  # name (casefolded) -> its value
    global_problems: dict[str, str] = field(default_factory=dict)  # name (casefolded) -> what's wrong
    fringe_problems: dict[str, str] = field(default_factory=dict)  # fringe id -> what's wrong

    @property
    def direct(self) -> Sum:
        """Above and below the line together: every line, before the top sheet's adjustments."""
        s = Sum()
        s.add(self.atl)
        s.add(self.btl)
        return s

    @property
    def fees(self) -> Decimal:
        return sum((a.amount for a in self.adjustments), ZERO)

    @property
    def grand(self) -> Decimal:
        return self.direct.total + self.fees

    def problems(self) -> list[tuple[str, str]]:
        """(line id, what's wrong) for every line that has a problem."""
        return [(lid, t.problem) for lid, t in self.lines.items() if t.problem]


# ---------------------------------------------------------------------------- globals
def resolve_globals(budget: Budget) -> tuple[dict[str, Decimal], dict[str, str]]:
    """Every global's value (by casefolded name), and what's wrong with the ones that can't be worked out
    (a typo, a missing global, one that uses itself, directly or through others)."""
    by_name = {g.name.casefold(): g for g in budget.globals if g.name.strip()}
    values: dict[str, Decimal] = {}
    problems: dict[str, str] = {}

    def get(name: str, using: tuple[str, ...]) -> Decimal:
        if name in values:
            return values[name]
        if name in problems:
            raise FormulaError(problems[name])
        g = by_name.get(name)
        if g is None:
            raise FormulaError(f"There's no global called “{name}”.")
        if name in using:
            raise FormulaError(f"“{g.name}” ends up using itself.")
        try:
            v = formula.evaluate(g.value, lambda n: get(n, (*using, name)))
        except FormulaError as e:
            problems[name] = str(e)
            raise
        values[name] = v
        return v

    for name in by_name:
        try:
            get(name, ())
        except FormulaError:
            pass
    return values, problems


def lookup(values: dict[str, Decimal], problems: dict[str, str]):
    def look(name: str) -> Decimal:
        if name in values:
            return values[name]
        if name in problems:
            raise FormulaError(f"The global “{name}” has a problem: {problems[name]}")
        raise FormulaError(f"There's no global called “{name}”.")

    return look


# ---------------------------------------------------------------------------- lines
def _fringe_numbers(f: Fringe, look) -> tuple[Decimal, Decimal | None]:
    """A fringe's rate (a percent as a fraction, or a flat amount) and its cap (None: no cap)."""
    rate = formula.evaluate(f.rate, look)
    cap = formula.evaluate(f.cap, look) if f.cap.strip() else None
    if f.kind == "percent":
        rate = rate / HUNDRED
    return rate, cap


def line_total(
    budget: Budget, ln: Line, look, fringes: dict[str, tuple[Fringe, Decimal, Decimal | None]]
) -> LineTotal:
    """One line, worked out. `fringes`: the budget's usable fringes (id -> fringe, rate, cap)."""
    t = LineTotal()
    try:
        t.amount = formula.evaluate(ln.amount, look, blank=ONE)
        t.units = formula.evaluate(ln.units, look, blank=ONE)
        t.rate = formula.evaluate(ln.rate, look)
        sub = t.amount * t.units * t.rate
        cur = (ln.currency or budget.currency).upper()
        if cur != budget.currency.upper():
            fx = money.parse(budget.fx.get(cur, ""))
            if fx <= 0:
                raise FormulaError(f"There's no exchange rate for {cur} yet.")
            sub = sub / fx
        if abs(sub) >= formula.LIMIT:
            raise FormulaError("That comes out too big.")
        t.subtotal = money.cents(sub)
    except FormulaError as e:
        t.subtotal = ZERO
        t.problem = str(e)
        return t
    for fid in ln.fringes:
        got = fringes.get(fid)
        if got is None:
            continue
        f, rate, cap = got
        if f.kind == "percent":
            base = t.subtotal if cap is None else min(t.subtotal, cap)
            amount = base * rate
        else:
            amount = rate * t.amount * t.units
        amount = money.cents(amount)
        t.by_fringe[fid] = t.by_fringe.get(fid, ZERO) + amount
        t.fringes += amount
    return t


# ---------------------------------------------------------------------------- the whole budget
def totals(budget: Budget) -> Totals:
    """Everything in `budget`, added up."""
    out = Totals()
    values, problems = resolve_globals(budget)
    out.globals, out.global_problems = values, problems
    look = lookup(values, problems)
    usable: dict[str, tuple[Fringe, Decimal, Decimal | None]] = {}
    for f in budget.fringes:
        try:
            rate, cap = _fringe_numbers(f, look)
        except FormulaError as e:
            out.fringe_problems[f.id] = str(e)
            continue
        usable[f.id] = (f, rate, cap)
        out.fringes[f.id] = ZERO
        out.fringe_lines[f.id] = 0
    for s in SECTIONS:
        out.sections[s] = Sum()
    for c in budget.categories:
        cs = Sum()
        for a in c.accounts:
            acc = Sum()
            for ln in a.lines:
                lt = line_total(budget, ln, look, usable)
                out.lines[ln.id] = lt
                acc.add(lt.as_sum())
                for fid, amount in lt.by_fringe.items():
                    out.fringes[fid] += amount
                    out.fringe_lines[fid] += 1
            out.accounts[a.id] = acc
            cs.add(acc)
        out.categories[c.id] = cs
        out.sections[c.section].add(cs)
    out.atl.add(out.sections["atl"])
    for s in BELOW_THE_LINE:
        out.btl.add(out.sections[s])
    running = out.direct.total
    for adj in budget.adjustments:
        base = {
            "atl_btl": out.direct.total,
            "btl": out.btl.total,
            "production": out.sections["production"].total,
        }.get(adj.base, running)
        try:
            rate = formula.evaluate(adj.rate, look)
            if adj.kind == "percent":
                amount = money.cents(base * rate / HUNDRED)
            else:
                amount, base = money.cents(rate), ZERO
            out.adjustments.append(AdjustmentTotal(adj.id, adj.name, base, amount))
        except FormulaError as e:
            out.adjustments.append(AdjustmentTotal(adj.id, adj.name, base, ZERO, str(e)))
            amount = ZERO
        running += amount
    return out


def uses_of(budget: Budget, name: str) -> int:
    """How many lines, globals, fringes and fees use the global `name`."""
    key = name.casefold()
    n = 0
    for _c, _a, ln in budget.lines():
        if any(key in formula.names(t) for t in (ln.amount, ln.units, ln.rate)):
            n += 1
    n += sum(1 for g in budget.globals if key in formula.names(g.value))
    n += sum(1 for f in budget.fringes if key in formula.names(f.rate) or key in formula.names(f.cap))
    n += sum(1 for a in budget.adjustments if key in formula.names(a.rate))
    return n


def rename_global(budget: Budget, old: str, new: str) -> int:
    """Rename a global everywhere it's used. Returns how many formulas changed."""
    changed = 0

    def swap(obj, attr: str) -> None:
        nonlocal changed
        before = getattr(obj, attr)
        after = formula.rename(before, old, new)
        if after != before:
            setattr(obj, attr, after)
            changed += 1

    for _c, _a, ln in budget.lines():
        for attr in ("amount", "units", "rate"):
            swap(ln, attr)
    for g in budget.globals:
        swap(g, "value")
    for f in budget.fringes:
        swap(f, "rate")
        swap(f, "cap")
    for a in budget.adjustments:
        swap(a, "rate")
    return changed
