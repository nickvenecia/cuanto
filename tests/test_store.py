"""Saving and loading (core/store.py), and the made-up sample."""

from __future__ import annotations

import json

from cuanto.core import calc, sample, templates
from cuanto.core.store import Library


def test_round_trip_keeps_every_number(data_folder):
    lib = sample.fill(Library(data_folder).load())
    again = Library(data_folder).load()
    assert len(again.budgets) == 2 and len(again.profiles) == 1 and len(again.rates) == len(lib.rates)
    for bid, b in lib.budgets.items():
        assert calc.totals(again.budgets[bid]).grand == calc.totals(b).grand
        assert again.budgets[bid].to_dict() == b.to_dict()


def test_a_broken_file_is_set_aside_not_lost(data_folder):
    (data_folder / "budgets").mkdir(parents=True)
    (data_folder / "budgets" / "abc.json").write_text("{not json")
    (data_folder / "rates.json").write_text("[{")
    lib = Library(data_folder).load()
    assert lib.budgets == {} and lib.rates == {}
    assert any(p.name.startswith("abc.json.unreadable-") for p in (data_folder / "budgets").iterdir())
    assert any(p.name.startswith("rates.json.unreadable-") for p in data_folder.iterdir())


def test_a_budget_with_a_broken_line_keeps_the_rest(data_folder):
    lib = Library(data_folder).load()
    b = lib.add_budget(templates.build("short", "Short"))
    raw = b.to_dict()
    raw["categories"][0]["accounts"][0]["lines"].append("not a line")
    raw["categories"][0]["accounts"][0]["lines"][0]["unit"] = "fortnights"
    (data_folder / "budgets" / f"{b.id}.json").write_text(json.dumps(raw))
    again = Library(data_folder).load().budgets[b.id]
    assert again.categories[0].accounts[0].lines[0].unit == "allow"  # an unknown unit reads as an allowance
    assert len(again.categories[0].accounts[0].lines) == len(b.categories[0].accounts[0].lines)
    assert any(".partly-unreadable-" in p.name for p in (data_folder / "budgets").iterdir())


def test_old_files_load_with_defaults(data_folder):
    (data_folder / "budgets").mkdir(parents=True)
    old = {"id": "old1", "name": "Old", "categories": [{"name": "Camera", "accounts": [
        {"name": "Crew", "lines": [{"description": "DP", "rate": "900", "future_field": 1}]}]}]}  # fmt: skip
    (data_folder / "budgets" / "old1.json").write_text(json.dumps(old))
    b = Library(data_folder).load().budgets["old1"]
    ln = b.categories[0].accounts[0].lines[0]
    assert b.stage == "bid" and b.currency == "USD" and b.categories[0].section == "production"
    assert ln.amount == "1" and ln.units == "1" and ln.fringes == [] and ln.currency == ""
    assert calc.totals(b).grand == 900


def test_a_file_is_saved_under_its_own_name(data_folder):
    (data_folder / "budgets").mkdir(parents=True)
    (data_folder / "budgets" / "mine.json").write_text(json.dumps({"id": "../../evil", "name": "X"}))
    lib = Library(data_folder).load()
    assert list(lib.budgets) == ["mine"]


def test_duplicate_keeps_line_ids_and_starts_as_a_bid(data_folder):
    lib = sample.fill(Library(data_folder).load())
    src = next(iter(lib.budgets.values()))
    src.stage = "locked"
    copy = lib.duplicate_budget(src)
    assert copy.id != src.id and copy.stage == "bid" and copy.name.endswith("(Copy)")
    assert [ln.id for _c, _a, ln in copy.lines()] == [ln.id for _c, _a, ln in src.lines()]
    copy.categories[0].name = "Changed"
    assert src.categories[0].name != "Changed"


def test_deleting_a_profile_leaves_budgets_on_the_one_in_use(data_folder):
    lib = sample.fill(Library(data_folder).load())
    p = next(iter(lib.profiles.values()))
    b = next(iter(lib.budgets.values()))
    b.profile_id = p.id
    lib.delete_profile(p.id)
    assert b.profile_id == "" and lib.profile(b) is None


def test_a_snapshot_is_kept_before_a_big_change(data_folder):
    lib = sample.fill(Library(data_folder).load())
    b = next(iter(lib.budgets.values()))
    path = lib.snapshot(b.id, "Import CSV")
    assert path is not None and path.exists() and json.loads(path.read_text())["id"] == b.id
