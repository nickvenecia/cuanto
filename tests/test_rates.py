"""The rate library (core/rates.py): lines from rates, rates from lines, merging."""

from __future__ import annotations

from cuanto.core import rates, templates
from cuanto.core.model import Line, Rate


def test_a_line_from_a_rate_takes_its_fringes_by_name():
    b = templates.build("feature", "x")
    r = Rate(name="Gaffer", rate="725", unit="days", fringes=["fica", "Union P&H", "Not in this budget"])
    ln = rates.line_from(r, b)
    assert ln.description == "Gaffer" and ln.rate == "725" and ln.units == "shoot_days" and ln.rate_id == r.id
    assert [b.fringe(f).name for f in ln.fringes] == ["FICA", "Union P&H"]


def test_a_rate_from_a_line_works_out_a_formula():
    b = templates.build("feature", "x")
    ln = Line(description="Key Grip", rate="shoot_days * 25", unit="days", fringes=[b.fringes[0].id])
    r = rates.rate_from(ln, b, "Grip")
    assert r.rate == "500.00" and r.department == "Grip" and r.fringes == ["FICA"]


def test_merging_updates_the_same_entry():
    lib: dict[str, Rate] = {}
    a = Rate(name="Gaffer", department="Electric", union=True, rate="700")
    assert rates.merge(lib, [a]) == (1, 0)
    again = Rate(name="gaffer", department="electric", union=True, rate="725")
    other = Rate(name="Gaffer", department="Electric", union=False, rate="500")
    assert rates.merge(lib, [again, other]) == (1, 1)
    assert lib[a.id].rate == "725" and len(lib) == 2
