"""Templates (core/templates.py): Cuánto's own, and yours, saved from a budget and started from."""

from __future__ import annotations

import json

from cuanto.core import calc, sample, templates
from cuanto.core.history import History
from cuanto.core.store import Library


def _spot(lib: Library):
    return next(b for b in lib.budgets.values() if b.kind == "commercial")


def test_a_template_keeps_the_shape_but_not_the_production(data_folder):
    b = _spot(sample.fill(Library(data_folder).load()))
    b.info.client, b.info.dates, b.info.company = "Agua Clara", "Nov 3–5", "Mesa Alta Pictures"
    ln = next(ln for _c, _a, ln in b.lines() if ln.rate)
    ln.actual = "999"
    t = templates.from_budget(b, "Our Spot")
    tb = t.budget
    assert t.name == tb.name == "Our Spot" and tb.stage == "bid"
    assert tb.info.client == "" and tb.info.dates == "" and tb.info.company == "Mesa Alta Pictures"
    assert [g.name for g in tb.globals] == [g.name for g in b.globals]
    assert sum(1 for _ in tb.lines()) == sum(1 for _ in b.lines())
    kept = tb.find_line(ln.id)[2]
    assert kept.rate == ln.rate and kept.actual == ""
    assert b.info.client == "Agua Clara" and ln.actual == "999"  # the budget itself is left alone


def test_a_template_can_leave_the_rates_out(data_folder):
    b = _spot(sample.fill(Library(data_folder).load()))
    t = templates.from_budget(b, "Bare", keep_rates=False)
    assert all(ln.rate == "" and ln.rate_id == "" for _c, _a, ln in t.budget.lines())
    assert any(ln.rate for _c, _a, ln in b.lines())


def test_a_budget_from_your_template_is_new_throughout_and_adds_up_the_same(data_folder):
    lib = sample.fill(Library(data_folder).load())
    b = _spot(lib)
    t = lib.add_template(templates.from_budget(b, "Our Spot"))
    new = templates.start(templates.MINE + t.id, "Next Spot", lib.templates)
    assert new.name == "Next Spot" and new.kind == "commercial" and new.stage == "bid"
    old_ids = {b.id} | {x.id for x in (*b.globals, *b.fringes, *b.adjustments, *b.categories)}
    old_ids |= {a.id for _c, a in b.accounts()} | {ln.id for _c, _a, ln in b.lines()}
    new_ids = {new.id} | {x.id for x in (*new.globals, *new.fringes, *new.adjustments, *new.categories)}
    new_ids |= {a.id for _c, a in new.accounts()} | {ln.id for _c, _a, ln in new.lines()}
    assert not old_ids & new_ids
    fringe_ids = {f.id for f in new.fringes}
    assert all(set(ln.fringes) <= fringe_ids for _c, _a, ln in new.lines())
    assert sum(len(ln.fringes) for _c, _a, ln in new.lines()) == sum(
        len(ln.fringes) for _c, _a, ln in b.lines()
    )
    assert calc.totals(new).grand == calc.totals(b).grand
    again = templates.start(templates.MINE + t.id, "", lib.templates)
    assert again.id != new.id and again.categories[0].id != new.categories[0].id


def test_a_template_thats_gone_starts_a_blank_budget():
    b = templates.start(templates.MINE + "gone", "X", {})
    assert b.name == "X" and b.kind == "blank" and not b.categories


def test_templates_are_saved_and_one_with_the_same_name_is_replaced(data_folder):
    lib = sample.fill(Library(data_folder).load())
    first = lib.add_template(templates.from_budget(_spot(lib), "Our Spot"))
    feature = next(b for b in lib.budgets.values() if b.kind == "feature")
    second = lib.add_template(templates.from_budget(feature, "our spot "))
    again = Library(data_folder).load()
    assert list(again.templates) == [first.id] and second.id == first.id
    assert again.templates[first.id].budget.kind == "feature"
    lib.delete_template(first.id)
    assert Library(data_folder).load().templates == {}


def test_a_broken_template_is_set_aside_and_the_rest_kept(data_folder):
    lib = sample.fill(Library(data_folder).load())
    good = lib.add_template(templates.from_budget(_spot(lib), "Good"))
    raw = json.loads((data_folder / "templates.json").read_text())
    raw.append({"id": "bad", "name": "No budget"})
    (data_folder / "templates.json").write_text(json.dumps(raw))
    again = Library(data_folder).load()
    assert list(again.templates) == [good.id]
    assert any(p.name.startswith("templates.json.partly-unreadable-") for p in data_folder.iterdir())


def test_undo_brings_back_a_deleted_template(data_folder):
    lib = sample.fill(Library(data_folder).load())
    t = lib.add_template(templates.from_budget(_spot(lib), "Our Spot"))
    h = History(lib)
    lib.delete_template(t.id)
    h.mark()
    assert h.undo() == "templates"
    assert t.id in lib.templates and t.id in Library(data_folder).load().templates
