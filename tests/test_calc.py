"""The numbers (core/calc.py): lines, fringes, roll-ups, the top sheet's fees."""

from __future__ import annotations

from decimal import Decimal

from cuanto.core import calc, templates
from cuanto.core.model import Account, Adjustment, Budget, Category, Fringe, Global, Line


def _budget() -> Budget:
    fica = Fringe(name="FICA", kind="percent", rate="7.65")
    capped = Fringe(name="FUTA", kind="percent", rate="0.6", cap="7000")
    ph = Fringe(name="P&H", kind="flat", rate="10")
    dp = Line(description="DP", amount="1", units="shoot_days", unit="days", rate="1000",
              fringes=[fica.id, capped.id, ph.id])  # fmt: skip
    truck = Line(description="Truck", units="shoot_days / 5", unit="weeks", rate="2500")
    director = Line(description="Director", unit="flat", rate="50000", fringes=[fica.id])
    return Budget(
        globals=[Global(name="shoot_days", value="20"), Global(name="prep_days", value="shoot_days / 2")],
        fringes=[fica, capped, ph],
        categories=[
            Category(
                code="1300",
                name="Director",
                section="atl",
                accounts=[Account(name="Director", lines=[director])],
            ),
            Category(
                code="2700",
                name="Camera",
                section="production",
                accounts=[Account(name="Crew", lines=[dp, truck])],
            ),
        ],
        adjustments=[
            Adjustment(name="Contingency", rate="10", base="atl_btl"),
            Adjustment(name="Fee", rate="5", base="running"),
            Adjustment(name="Flat Thing", kind="flat", rate="1000"),
        ],
    )


def test_a_line_is_amount_times_units_times_rate():
    b = _budget()
    t = calc.totals(b)
    truck = t.lines[b.categories[1].accounts[0].lines[1].id]
    assert truck.units == 4 and truck.subtotal == Decimal("10000.00") and truck.fringes == 0


def test_fringes_percent_capped_and_flat_per_unit():
    b = _budget()
    t = calc.totals(b)
    dp = t.lines[b.categories[1].accounts[0].lines[0].id]
    assert dp.subtotal == Decimal("20000.00")
    fica, futa, ph = b.fringes
    assert dp.by_fringe[fica.id] == Decimal("1530.00")
    assert dp.by_fringe[futa.id] == Decimal("42.00")  # 0.6% of the first 7,000 only
    assert dp.by_fringe[ph.id] == Decimal("200.00")  # $10 for each of 20 days
    assert dp.total == Decimal("21772.00")
    assert t.fringes[fica.id] == Decimal("1530.00") + Decimal("3825.00") and t.fringe_lines[fica.id] == 2


def test_everything_rolls_up_to_the_grand_total():
    b = _budget()
    t = calc.totals(b)
    assert t.atl.total == Decimal("53825.00")
    assert t.btl.total == Decimal("31772.00")
    assert t.direct.total == Decimal("85597.00")
    contingency, fee, flat = t.adjustments
    assert contingency.amount == Decimal("8559.70")
    assert fee.amount == Decimal("4707.84")  # 5% of everything above it, contingency included
    assert flat.amount == Decimal("1000.00")
    assert t.grand == t.direct.total + contingency.amount + fee.amount + flat.amount
    assert sum(t.categories[c.id].total for c in b.categories) == t.direct.total


def test_changing_a_global_recalculates_everything():
    b = _budget()
    before = calc.totals(b).grand
    b.globals[0].value = "25"
    after = calc.totals(b)
    assert after.grand > before and after.globals["prep_days"] == Decimal("12.5")


def test_problems_count_as_zero_and_say_why():
    b = _budget()
    b.globals.append(Global(name="loop_a", value="loop_b + 1"))
    b.globals.append(Global(name="loop_b", value="loop_a"))
    ln = b.categories[1].accounts[0].lines[1]
    ln.units = "loop_a"
    t = calc.totals(b)
    assert "loop_a" in t.global_problems and t.lines[ln.id].subtotal == 0 and t.lines[ln.id].problem
    ln.units = "missing_days"
    assert "no global" in calc.totals(b).lines[ln.id].problem


def test_production_only_fees_skip_the_rest():
    b = _budget()
    b.adjustments = [Adjustment(name="Production Fee", rate="20", base="production")]
    t = calc.totals(b)
    assert t.adjustments[0].amount == Decimal("6354.40")  # 20% of the Camera category only


def test_a_line_in_another_currency_converts():
    b = _budget()
    b.fx = {"MXN": "20"}
    ln = Line(description="Location", rate="20000", currency="MXN")
    b.categories[1].accounts[0].lines.append(ln)
    t = calc.totals(b)
    assert t.lines[ln.id].subtotal == Decimal("1000.00")
    b.fx = {}
    assert "exchange rate" in calc.totals(b).lines[ln.id].problem


def test_renaming_a_global_follows_it_everywhere():
    b = _budget()
    n = calc.rename_global(b, "shoot_days", "days_shooting")
    assert n == 3 and calc.uses_of(b, "days_shooting") == 3 and calc.uses_of(b, "shoot_days") == 0
    b.globals[0].name = "days_shooting"
    assert not calc.totals(b).problems()


def test_every_template_adds_up_without_problems():
    for kind, _name in templates.choices():
        b = templates.build(kind, kind)
        t = calc.totals(b)
        assert not t.problems() and not t.global_problems and not t.fringe_problems, kind
        assert t.grand == 0  # rates start empty
        assert all(f in {x.id for x in b.fringes} for _c, _a, ln in b.lines() for f in ln.fringes)
