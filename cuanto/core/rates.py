"""The rate library: crew and vendor rates you keep once and reuse in every budget.

A line made from a rate takes its name, rate and unit, and the budget's fringes with the rate's fringe names
("FICA", "Union P&H"). A line saved to the library gives its description, rate (worked out, if it was a
formula), unit and fringe names. No Qt here.
"""

from __future__ import annotations

from cuanto.core import calc, formula, money
from cuanto.core.formula import FormulaError
from cuanto.core.model import Budget, Line, Rate, now_iso


def fringe_ids(budget: Budget, names: list[str]) -> list[str]:
    """The budget's fringes with these names (whatever their capitals), in the budget's order."""
    wanted = {n.strip().casefold() for n in names if n.strip()}
    return [f.id for f in budget.fringes if f.name.strip().casefold() in wanted]


def default_units(budget: Budget, unit: str) -> str:
    """What a new line from a day rate runs for: the shoot, when the budget has a shoot_days global."""
    if unit == "days" and budget.global_named("shoot_days") is not None:
        return "shoot_days"
    return "1"


def apply(rate: Rate, ln: Line, budget: Budget) -> None:
    """Put a library rate on a line: its rate, unit and fringes (the line keeps its amount and units)."""
    ln.rate = rate.rate
    if ln.unit != rate.unit:
        ln.unit = rate.unit
    ln.rate_id = rate.id
    if not ln.description.strip():
        ln.description = rate.name
    found = fringe_ids(budget, rate.fringes)
    if found:
        ln.fringes = found


def line_from(rate: Rate, budget: Budget) -> Line:
    ln = Line(description=rate.name, units=default_units(budget, rate.unit), unit=rate.unit)
    apply(rate, ln, budget)
    return ln


def rate_from(ln: Line, budget: Budget, department: str = "") -> Rate:
    """A library entry from a line (its rate worked out to a number if it was a formula)."""
    value = ln.rate.strip()
    if value and not formula.is_plain(value):
        values, problems = calc.resolve_globals(budget)
        try:
            value = str(money.cents(formula.evaluate(value, calc.lookup(values, problems))))
        except FormulaError:
            value = ""
    names = [f.name for fid in ln.fringes if (f := budget.fringe(fid)) is not None]
    return Rate(name=ln.description.strip(), department=department, rate=value, unit=ln.unit, fringes=names)


def same(a: Rate, b: Rate) -> bool:
    """The same entry, for importing: name, department and union or not."""
    return (
        a.name.strip().casefold() == b.name.strip().casefold()
        and a.department.strip().casefold() == b.department.strip().casefold()
        and a.union == b.union
        and a.kind == b.kind
    )


def merge(rates: dict[str, Rate], incoming: list[Rate]) -> tuple[int, int]:
    """Add rates to the library; one that's already there gets the new numbers. (added, updated)."""
    added = updated = 0
    for r in incoming:
        if not r.name.strip():
            continue
        mine = next((x for x in rates.values() if same(x, r)), None)
        if mine is None:
            rates[r.id] = r
            added += 1
            continue
        changed = False
        for k in ("rate", "unit", "local", "vendor", "link", "notes"):
            v = getattr(r, k)
            if v and v != getattr(mine, k):
                setattr(mine, k, v)
                changed = True
        if r.fringes and r.fringes != mine.fringes:
            mine.fringes = list(r.fringes)
            changed = True
        if changed:
            mine.updated = now_iso()
            updated += 1
    return added, updated


def haystack(r: Rate) -> str:
    """Everything a search looks through."""
    union = "union" if r.union else "non-union nonunion"
    return " ".join((r.name, r.department, r.local, r.vendor, r.notes, union, " ".join(r.fringes))).casefold()
