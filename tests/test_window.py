"""The window, offscreen: making a budget, editing lines in the panel and in the table, fringes, globals,
deleting, undo, importing and exporting, the page window, and what's dropped when left empty."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from cuanto.core import calc, sample
from cuanto.core.store import Library


@pytest.fixture
def win(qapp, data_folder):
    from cuanto.ui.window.main_window import MainWindow

    w = MainWindow(sample.fill(Library(data_folder).load()))
    w._restored = True
    w.resize(1600, 1000)
    w.show()
    yield w
    w.close()


def feature(w):
    return next(b for b in w.lib.budgets.values() if b.kind == "feature")


def say_yes(monkeypatch) -> None:
    monkeypatch.setattr("cuanto.ui.window.editing.confirm", lambda *a, **k: True)


def test_first_launch_shows_the_ways_to_start(qapp, data_folder):
    from cuanto.ui.window.main_window import MainWindow

    w = MainWindow(Library(data_folder).load())
    w.show()
    assert w.pages.currentWidget() is w.empty and len(w.empty.tiles) == 5
    assert not w.search.isVisibleTo(w) and not w.sidebar.heads["open"].isVisibleTo(w.sidebar)
    w.close()


def test_a_new_budget_from_a_template(qapp, data_folder, monkeypatch):
    from cuanto.ui.dialogs import pickers
    from cuanto.ui.window.main_window import MainWindow

    w = MainWindow(Library(data_folder).load())
    w.show()
    monkeypatch.setattr(pickers.NewBudgetDialog, "exec", lambda self: (self.field.setText("Spot"), 1)[1])
    monkeypatch.setattr(pickers.NewBudgetDialog, "kind", property(lambda self: "commercial"))
    w.new_budget()
    assert w.budget is not None and w.budget.name == "Spot" and w.view_key == "top"
    assert w.sidebar.heads["open"].label.full_text() == "Spot"
    assert Library(data_folder).load().budgets[w.budget.id].kind == "commercial"
    w.close()


def test_typing_a_line_in_its_panel_saves_and_adds_up(win):
    b = feature(win)
    win.go(f"budget:{b.id}")
    camera = next(c for c in b.categories if c.name == "Camera")
    acc = camera.accounts[0]
    win.new_line(account_id=acc.id)
    panel = win.line_panel
    ln = panel.ln
    assert win.view_key == "sec:production" and ln in acc.lines
    panel.name.setPlainText("Steadicam Operator")  # typing
    panel.units.setText("shoot_days")
    panel.units.textEdited.emit("shoot_days")
    panel.rate.setText("1200")
    panel.rate.textEdited.emit("1200")
    fica = b.fringes[0]
    panel.fringe_rows[fica.id].setChecked(True)
    win.flush()
    again = Library(win.lib.root).load().budgets[b.id]
    got = again.find_line(ln.id)[2]
    assert got.description == "Steadicam Operator" and got.units == "shoot_days" and got.rate == "1200"
    assert got.fringes == [fica.id]
    t = calc.totals(again)
    assert t.lines[ln.id].subtotal == Decimal("24000.00") and t.lines[ln.id].fringes == Decimal("1836.00")
    assert panel.total.text() == "$25,836.00"


def test_typing_over_a_line_in_the_table(win):
    b = feature(win)
    win.go("sec:production")
    win.go(f"budget:{b.id}")
    win.go("sec:production")
    ln = next(ln for _c, _a, ln in b.lines() if ln.description == "Grips")
    win.cell_edited(ln.id, "units", "shoot_days + 5")
    win.cell_edited(ln.id, "unit", "weeks")
    got = Library(win.lib.root).load().budgets[b.id].find_line(ln.id)[2]
    assert got.units == "shoot_days + 5" and got.unit == "weeks"
    row = win.tables["section"].find("line", ln.id)
    assert row is not None and row.text(win.tables["section"].col("units")) == "25"


def test_changing_a_global_changes_every_line(win):
    b = feature(win)
    win.go(f"budget:{b.id}")
    before = calc.totals(b).grand
    g = b.global_named("shoot_days")
    win.open("global", g.id)
    win.global_panel.value.setText("25")
    win.global_panel.value.textEdited.emit("25")
    win.flush()
    win.refresh()
    assert calc.totals(Library(win.lib.root).load().budgets[b.id]).grand > before
    win.global_panel.name.setText("days_shooting")
    win.global_panel.name.editingFinished.emit()
    assert g.name == "days_shooting" and calc.uses_of(b, "days_shooting") > 10
    assert not calc.totals(b).problems()


def test_an_account_switch_puts_a_fringe_on_every_line(win):
    b = feature(win)
    win.go(f"budget:{b.id}")
    acc = next(a for _c, a in b.accounts() if a.name == "Camera Equipment")
    union = next(f for f in b.fringes if f.name == "Union P&H")
    win.open("account", acc.id)
    win.account_panel.fringe_rows[union.id].setChecked(True)
    assert all(union.id in ln.fringes for ln in acc.lines)
    win.account_panel.fringe_rows[union.id].setChecked(False)
    assert not any(union.id in ln.fringes for ln in acc.lines)


def test_a_new_line_left_empty_is_not_kept(win):
    b = feature(win)
    win.go(f"budget:{b.id}")
    before = sum(1 for _ in b.lines())
    win.new_line()
    assert sum(1 for _ in b.lines()) == before + 1
    win.deselect()  # Esc
    assert sum(1 for _ in b.lines()) == before
    assert sum(1 for _ in Library(win.lib.root).load().budgets[b.id].lines()) == before


def test_deleting_asks_first_and_undo_brings_it_back(win, monkeypatch):
    b = feature(win)
    win.go(f"budget:{b.id}")
    cat = next(c for c in b.categories if c.name == "Camera")
    asked = []
    monkeypatch.setattr(
        "cuanto.ui.window.editing.confirm",
        lambda _w, title, text, *a, **k: asked.append((title, text)) or True,
    )
    win.delete_many([("category", cat.id)])
    assert asked == [("Delete 2700 Camera?", "Its 2 accounts and 6 lines go too.")]
    assert win.budget.find_category(cat.id) is None
    win.undo()
    assert win.budget.find_category(cat.id) is not None
    assert Library(win.lib.root).load().budgets[b.id].find_category(cat.id) is not None


def test_deleting_a_fringe_takes_it_off_every_line(win, monkeypatch):
    say_yes(monkeypatch)
    b = feature(win)
    win.go(f"budget:{b.id}")
    fica = b.fringes[0]
    win.delete_many([("fringe", fica.id)])
    assert not any(fica.id in ln.fringes for _c, _a, ln in b.lines())


def test_moving_lines_and_categories(win):
    b = feature(win)
    win.go(f"budget:{b.id}")
    acc = next(a for _c, a in b.accounts() if a.name == "Camera Crew")
    first, second = acc.lines[0], acc.lines[1]
    win.step("line", first.id, 1)
    assert acc.lines[0] is second and acc.lines[1] is first
    atl = [c for c in b.categories if c.section == "atl"]
    win.step("category", atl[0].id, 1)
    assert [c for c in b.categories if c.section == "atl"][1] is atl[0]


def test_rates_go_onto_lines_and_lines_into_the_library(win, monkeypatch):
    from cuanto.ui.dialogs import pickers

    b = feature(win)
    win.go(f"budget:{b.id}")
    ln = next(x for _c, _a, x in b.lines() if x.description == "Gaffer")
    gaffer = next(r for r in win.lib.rates.values() if r.name == "Gaffer" and r.union)
    monkeypatch.setattr(pickers.RatePicker, "exec", lambda self: 1)
    monkeypatch.setattr(pickers.RatePicker, "rate_id", property(lambda self: gaffer.id))
    win.use_rate(ln.id)
    assert ln.rate == "725" and ln.rate_id == gaffer.id
    assert {b.fringe(f).name for f in ln.fringes} == {"FICA", "Union P&H"}
    n = len(win.lib.rates)
    dit = next(x for _c, _a, x in b.lines() if x.description == "DIT")
    win.save_rate(dit.id)
    assert len(win.lib.rates) == n + 1 and dit.rate_id in win.lib.rates


def test_import_csv_into_the_open_budget_and_json_from_another_tool(win, tmp_path):
    b = feature(win)
    win.go(f"budget:{b.id}")
    win.go("sec:production")
    sheet = tmp_path / "extra.csv"
    sheet.write_text(
        "Category,Category Code,Account,Description,Units,Unit,Rate\nCamera,2700,Camera Crew,Steadicam,5,days,1100\n"
    )
    win.import_file(sheet)
    assert any(ln.description == "Steadicam" for _c, _a, ln in b.lines())
    assert list((win.lib.root / "backups").glob(f"{b.id}-*.json"))  # a copy was kept first
    crew = tmp_path / "crew.json"
    crew.write_text(json.dumps({"format": "cuanto.exchange", "version": 1,
                                "schedule": {"globals": {"shoot_days": 30}},
                                "crew": [{"role": "Gaffer", "name": "A. Rivera", "account": "2901", "rate": "700"}]}))  # fmt: skip
    win.import_file(crew)
    assert b.global_named("shoot_days").value == "30"
    assert any(ln.description == "Gaffer — A. Rivera" for _c, _a, ln in b.lines())


def test_exports_and_the_page_window(win, tmp_path, monkeypatch):
    from openpyxl import load_workbook

    from cuanto.ui.dialogs.preview import PageDialog

    b = feature(win)
    win.go(f"budget:{b.id}")
    out = iter([tmp_path / "b.xlsx", tmp_path / "b.json", tmp_path / "b.pdf"])
    monkeypatch.setattr(
        "cuanto.ui.window.transfer.QFileDialog.getSaveFileName", lambda *a, **k: (str(next(out)), "")
    )
    win.export_xlsx()
    assert load_workbook(tmp_path / "b.xlsx").sheetnames[0] == "Top Sheet"
    win.export_json()
    assert json.loads((tmp_path / "b.json").read_text())["format"] == "cuanto.budget"
    shown = []

    def page(d):
        shown.append(d.panel.view.pages)
        d.panel.save_pdf.emit()
        return 0

    monkeypatch.setattr(PageDialog, "exec", page)
    win.show_pages("both")
    assert shown and len(shown[0]) >= 3
    assert (tmp_path / "b.pdf").read_bytes().startswith(b"%PDF")


def test_search_and_the_lines_filter(win):
    from cuanto.ui.window.tables import ID, KIND

    b = feature(win)
    win.go(f"budget:{b.id}")
    win.go("sec:production")
    t = win.tables["section"]
    win.search.setText("gaffer")
    shown = [r.data(0, ID) for r in t.showing_rows() if r.data(0, KIND) == "line"]
    assert len(shown) == 1
    win.search.clear()
    ln = next(x for _c, _a, x in b.lines() if x.description == "Grips")
    ln.rate = ""
    win.refresh()
    win.filter_btn._pick("show", "no_rate")
    lines = [r.data(0, ID) for r in t.showing_rows() if r.data(0, KIND) == "line"]
    assert ln.id in lines and all(not b.find_line(i)[2].rate for i in lines)
    win.filter_btn._clear()


def test_a_problem_shows_in_the_table_and_the_panel(win):
    b = feature(win)
    win.go(f"budget:{b.id}")
    win.go("sec:production")
    ln = next(x for _c, _a, x in b.lines() if x.description == "Grips")
    win.cell_edited(ln.id, "units", "shoot_dayz")
    row = win.tables["section"].find("line", ln.id)
    assert row.text(win.tables["section"].col("total")) == "—"
    win.open("line", ln.id)
    assert (
        win.line_panel.problem.isVisibleTo(win.line_panel) and "shoot_dayz" in win.line_panel.problem.text()
    )


def test_deleting_the_open_budget_goes_back_to_all_budgets(win, monkeypatch):
    say_yes(monkeypatch)
    b = feature(win)
    win.go(f"budget:{b.id}")
    win.delete_many([("budget", b.id)])
    assert win.budget is None and win.view_key == "budgets" and b.id not in win.lib.budgets
    assert not (Path(win.lib.root) / "budgets" / f"{b.id}.json").exists()
