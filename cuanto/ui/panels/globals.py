"""A global on the right: a named number lines can use (shoot_days = 20). Renaming it renames it in every
formula that uses it; changing its value changes every line that does."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from cuanto.core import calc, formula
from cuanto.core.model import UNIT_NAMES, UNITS, Budget, Global
from cuanto.ui.components.widgets import Section, TitleEdit, combo, hbox, set_combo
from cuanto.ui.panels.base import DetailsBase, Numbers, field, formula_field, offer_globals, set_text
from cuanto.ui.style import tokens
from cuanto.ui.window.tables import qty


class GlobalPanel(DetailsBase):
    KEY = "global"
    TITLE = "Global"
    MORE_TIP = "Delete"

    delete_wanted = Signal(str)
    renamed = Signal(str, str, str)  # global id, old name, new name

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.budget: Budget | None = None
        self.g: Global | None = None
        f = self.form_lay
        self.label = TitleEdit()
        self.label.setPlaceholderText("What it is: Shoot Days")
        self.label.textEdited.connect(self._label)
        f.addWidget(self.label)
        sec, self.name = field(
            "Name in Formulas", "shoot_days", "Letters, numbers and _. Lines use this name."
        )
        self.name.editingFinished.connect(self._rename)
        f.addWidget(sec)
        row = hbox(spacing=tokens.SPACE_2)
        sec, self.value = formula_field("Value", "20", "A number, or a formula with other globals")
        self.value.textEdited.connect(self._value)
        row.addWidget(sec, 2)
        sec = Section("Unit")
        self.unit = combo([("", "Number", ""), *[(u, UNIT_NAMES[u], "") for u in UNITS]], "")
        self.unit.activated.connect(lambda _i: self._unit())
        sec.add(self.unit)
        row.addWidget(sec, 1)
        f.addLayout(row)
        self.sums = Numbers("", [("result", "Comes To"), ("used", "Used In")])
        f.addWidget(self.sums)
        self.menu_action("trash", "Delete…", lambda: self.g and self.delete_wanted.emit(self.g.id))
        self.show_empty("Nothing selected")

    def load(self, budget: Budget, g: Global) -> None:
        self._loading = True
        self.budget, self.g = budget, g
        if self.label.text() != g.label:
            self.label.setText(g.label)
        set_text(self.name, g.name)
        set_text(self.value, g.value)
        offer_globals(self.value, [x.name for x in budget.globals if x.name and x.id != g.id])
        set_combo(self.unit, g.unit)
        self._loading = False
        self.numbers()
        self.show_form()

    def numbers(self) -> None:
        b, g = self.budget, self.g
        if b is None or g is None:
            return
        t = calc.totals(b)
        key = g.name.casefold()
        v = t.globals.get(key)
        problem = t.global_problems.get(key, "")
        unit = f" {UNIT_NAMES[g.unit]}" if g.unit else ""
        if problem:
            self.sums.set("result", problem)
        else:
            self.sums.set("result", f"{qty(v)}{unit}" if v is not None else "—")
        n = calc.uses_of(b, g.name) if g.name else 0
        self.sums.set("used", f"{n} formula{'s' if n != 1 else ''}" if n else "Nothing yet")

    def _label(self, text: str) -> None:
        if self.g is None or self._loading:
            return
        self.g.label = text.strip()
        if not self.g.name:  # a new global gets its formula name from its label until it has one
            set_text(self.name, formula.clean_name(text))
        self.edited()

    def _rename(self) -> None:
        if self.g is None or self._loading:
            return
        new = formula.clean_name(self.name.text())
        if not new:
            set_text(self.name, self.g.name)
            return
        taken = any(x.name.casefold() == new.casefold() and x.id != self.g.id for x in self.budget.globals)
        if taken:
            self.toast_wanted.emit(f"There's already a global called {new}.", "problem")
            set_text(self.name, self.g.name)
            return
        set_text(self.name, new)
        if new != self.g.name:
            old = self.g.name
            self.g.name = new
            self.renamed.emit(self.g.id, old, new)
            self.numbers()
            self.edited()

    def _value(self, text: str) -> None:
        if self.g is not None and not self._loading:
            self.g.value = text.strip()
            self.numbers()
            self.edited()

    def _unit(self) -> None:
        if self.g is not None and not self._loading:
            self.g.unit = self.unit.currentData() or ""
            self.numbers()
            self.edited()
