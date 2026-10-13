"""Undo and redo (core/history.py)."""

from __future__ import annotations

from cuanto.core import sample
from cuanto.core.history import History
from cuanto.core.model import Line
from cuanto.core.store import Library


def test_undo_and_redo_a_line(data_folder):
    lib = sample.fill(Library(data_folder).load())
    h = History(lib)
    b = lib.ordered_budgets()[0]
    acc = b.categories[0].accounts[0]
    acc.lines.append(Line(description="New Line", rate="100"))
    lib.save_budget(b)
    assert h.mark()
    assert h.undo() == b.name
    again = Library(data_folder).load().budgets[b.id]
    assert all(ln.description != "New Line" for _c, _a, ln in again.lines())
    assert h.redo() == b.name
    assert any(ln.description == "New Line" for _c, _a, ln in lib.budgets[b.id].lines())


def test_a_change_taken_straight_back_leaves_no_step(data_folder):
    lib = sample.fill(Library(data_folder).load())
    h = History(lib)
    b = lib.ordered_budgets()[0]
    old = b.name
    b.name = "Something Else"
    h.mark()
    b.name = old
    h.mark()
    assert not h.can_undo()


def test_saving_alone_is_not_a_change(data_folder):
    lib = sample.fill(Library(data_folder).load())
    h = History(lib)
    for b in lib.budgets.values():
        lib.save_budget(b)  # stamps the time
    assert not h.mark()


def test_undo_brings_back_a_deleted_budget_and_rates(data_folder):
    lib = sample.fill(Library(data_folder).load())
    h = History(lib)
    b = lib.ordered_budgets()[0]
    lib.delete_budget(b.id)
    lib.rates.clear()
    lib.save_rates()
    h.mark()
    h.undo()
    again = Library(data_folder).load()
    assert b.id in again.budgets and again.rates
