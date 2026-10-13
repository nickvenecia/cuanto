"""No words cut off on any screen (tests/cut_off.py): the window in every state, at its usual size and its
smallest, every side panel, and every dialog and Settings pane. A new screen gets a line here.

Each check runs twice: with the fonts as this computer draws them, and a tenth wider (fonts are wider on some
computers than others, a Mac's than Linux's), so words that only just fit here don't get cut off there."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QPushButton

from cuanto.core import sample, templates, update
from cuanto.core.store import Library
from cuanto.ui.style import tokens
from tests.cut_off import cut_off

LONG = "Name, logo and how you get paid, on every page you send out"


@pytest.fixture(params=[100, 110], ids=["fonts as drawn here", "fonts a tenth wider"])
def fonts(qapp, request):
    """The app's font as it is, or spaced a tenth wider (every window made in the test uses it)."""
    before = QFont(qapp.font())
    wider = QFont(before)
    wider.setLetterSpacing(QFont.SpacingType.PercentageSpacing, request.param)
    QApplication.setFont(wider)
    yield request.param
    QApplication.setFont(before)


def wait(ms: int = tokens.DOCK_MS + 60) -> None:
    """Long enough for the side panel to finish sliding in."""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


class Seen:
    """What was cut off, screen by screen."""

    def __init__(self):
        self.found: list[str] = []

    def check(self, where: str, w) -> None:
        wait()
        self.found += [f"{where}: {x}" for x in cut_off(w)]


def window(lib, size):
    from cuanto.ui.window.main_window import MainWindow

    w = MainWindow(lib)
    w._restored = True
    w.resize(*size)
    w.show()
    wait()
    return w


def test_the_checker_finds_cut_off_words(qapp):
    label, button = QLabel(LONG), QPushButton(LONG)
    for w in (label, button):
        w.setFixedWidth(60)
        w.show()
    assert len(cut_off(label)) == 1 and len(cut_off(button)) == 1
    label.setWordWrap(True)
    label.setFixedHeight(label.heightForWidth(60))
    assert cut_off(label) == []


@pytest.mark.parametrize("size", [tokens.WINDOW_SIZE, tokens.WINDOW_MIN], ids=["usual", "smallest"])
def test_no_words_cut_off_in_the_window(fonts, data_folder, size):
    seen = Seen()
    w = window(Library(data_folder).load(), size)
    assert (w.width(), w.height()) == size
    seen.check("first launch", w)
    w.close()

    lib = Library(data_folder).load()
    lib.add_budget(templates.build("blank", "Blank"))
    w = window(lib, size)
    w.go(f"budget:{next(iter(lib.budgets))}")
    for place in ("top", "sec:atl", "sec:production", "globals", "fringes", "rates"):
        w.go(place)
        seen.check(f"empty {place}", w)
    w.close()

    lib = sample.fill(Library(data_folder).load())
    b = next(x for x in lib.budgets.values() if x.kind == "feature")
    w = window(lib, size)
    w.go("budgets")
    seen.check("all budgets", w)
    w.open("budget", b.id)
    seen.check("a budget", w)
    w.go(f"budget:{b.id}")
    seen.check("top sheet", w)
    w.open("category", b.categories[0].id)
    seen.check("a category", w)
    w.open("adjustment", b.adjustments[0].id)
    seen.check("a fee", w)
    for s in ("atl", "production", "post", "other"):
        w.go(f"sec:{s}")
        w.deselect()
        seen.check(s, w)
    w.go("sec:production")
    _c, a, ln = next(b.lines())
    w.open("account", a.id)
    seen.check("an account", w)
    w.open("line", ln.id)
    seen.check("a line", w)
    w.go("globals")
    w.open("global", b.globals[0].id)
    seen.check("a global", w)
    w.go("fringes")
    w.open("fringe", b.fringes[0].id)
    seen.check("a fringe", w)
    w.go("rates")
    seen.check("rate library", w)
    w.open("rate", lib.ordered_rates()[0].id)
    seen.check("a rate", w)
    w.go("sec:production")
    w.search.setText("camera")
    seen.check("search", w)
    w.close()
    assert seen.found == []


def test_no_words_cut_off_in_any_dialog(fonts, data_folder, monkeypatch):
    seen = Seen()
    lib = sample.fill(Library(data_folder).load())
    b = next(x for x in lib.budgets.values() if x.kind == "feature")
    w = window(lib, tokens.WINDOW_MIN)
    w.go(f"budget:{b.id}")
    names = iter(())

    def look(self, *_a):
        self.show()
        seen.check(next(names), self)
        self.close()
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(QDialog, "exec", look)

    from cuanto.ui.dialogs.common import about, ask_name, notice
    from cuanto.ui.dialogs.pickers import AccountPicker, RatePicker
    from cuanto.ui.dialogs.update import UpdateDialog

    names = iter(["new budget"])
    w.new_budget()
    names = iter(["save as template"])
    w.save_as_template(b.id)
    lib.add_template(templates.from_budget(b, "Our Feature With a Long Name"))
    names = iter(["new budget, with yours"])
    w.new_budget()
    names = iter(["rate picker"])
    RatePicker(lib.ordered_rates(), w, "").exec()
    names = iter(["account picker"])
    AccountPicker(b, "Move to Account", "Move", parent=w).exec()
    names = iter(["delete alert"])
    w.delete_many([("category", b.categories[0].id)])
    names = iter(["notice"])
    notice(w, "Cuánto couldn't read that file.", "Put Description and Rate (or Total) in one row.")
    names = iter(["ask name"])
    ask_name(w, "Rename", "Rename", "The Long Night")
    names = iter(["about"])
    about(w, "1.1.0", str(data_folder))
    names = iter(["feedback"])
    w.open_feedback()
    names = iter(["update"])
    UpdateDialog(update.Release("9.9.9", "## 9.9.9\n\n- Something new."), parent=w).exec()
    names = iter(["pages both", "pages top sheet", "pages detail"])
    w.show_pages("both")
    w.show_pages("topsheet")
    w.show_pages("detail")
    for pane in ("general", "profiles", "templates", "account", "shortcuts", "data"):
        names = iter([f"settings {pane}"])
        w.open_settings(pane)
    names = iter(["settings, adding a profile"])
    w.edit_profile(add=True)
    for t in list(lib.templates):
        lib.delete_template(t)
    names = iter(["settings, no templates"])
    w.open_settings("templates")
    w.close()
    assert seen.found == []
