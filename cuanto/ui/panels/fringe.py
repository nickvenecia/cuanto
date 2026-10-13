"""A fringe on the right: payroll tax, pension & health, workers' comp… a percent of each line it's on (up to
an optional cap), or a flat amount for each unit. Which lines carry it is set on the line, or on a whole
account at once."""

from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from cuanto.core import calc
from cuanto.core.model import Budget, Fringe
from cuanto.ui.components.widgets import Card, Section, TextBox, TitleEdit, combo, hbox, set_combo
from cuanto.ui.panels.base import DetailsBase, Numbers, formula_field, offer_globals, set_text
from cuanto.ui.style import tokens
from cuanto.ui.window.tables import short_money

KINDS = [
    ("percent", "Percent", "A percent of each line it's on"),
    ("flat", "Flat per Unit", "So much for each day, hour…"),
]


class FringePanel(DetailsBase):
    KEY = "fringe"
    TITLE = "Fringe"
    MORE_TIP = "Delete"

    delete_wanted = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.budget: Budget | None = None
        self.fr: Fringe | None = None
        f = self.form_lay
        self.name = TitleEdit()
        self.name.setPlaceholderText("FICA, Union P&H…")
        self.name.textEdited.connect(self._name)
        f.addWidget(self.name)
        row = hbox(spacing=tokens.SPACE_2)
        sec = Section("Kind")
        self.kind = combo(KINDS, "percent")
        self.kind.activated.connect(lambda _i: self._kind())
        sec.add(self.kind)
        row.addWidget(sec, 1)
        self.rate_sec, self.rate = formula_field("Rate %", "7.65")
        self.rate.textEdited.connect(lambda t: self._set("rate", t))
        row.addWidget(self.rate_sec, 1)
        f.addLayout(row)
        self.cap_sec, self.cap = formula_field(
            "Cap", "No cap", "Only this much of each line counts (a wage base)"
        )
        self.cap.textEdited.connect(lambda t: self._set("cap", t))
        f.addWidget(self.cap_sec)
        self.sums = Numbers("", [("lines", "On"), ("total", "Total")])
        f.addWidget(self.sums)
        card = Card("Notes")
        self.notes = TextBox("", tokens.TEXT_BOX_H)
        self.notes.edited.connect(self._notes)
        card.add(self.notes)
        f.addWidget(card)
        self.menu_action("trash", "Delete…", lambda: self.fr and self.delete_wanted.emit(self.fr.id))
        self.show_empty("Nothing selected")

    def load(self, budget: Budget, fr: Fringe) -> None:
        self._loading = True
        self.budget, self.fr = budget, fr
        if self.name.text() != fr.name:
            self.name.setText(fr.name)
        set_combo(self.kind, fr.kind)
        set_text(self.rate, fr.rate)
        set_text(self.cap, fr.cap)
        names = [g.name for g in budget.globals if g.name]
        offer_globals(self.rate, names)
        offer_globals(self.cap, names)
        self.notes.set_text(fr.notes)
        self._loading = False
        self._shape()
        self.numbers()
        self.show_form()

    def _shape(self) -> None:
        pct = self.fr is not None and self.fr.kind == "percent"
        self.rate_sec.set_title("Rate %" if pct else "Per Unit")
        self.cap_sec.setVisible(pct)

    def numbers(self) -> None:
        b, fr = self.budget, self.fr
        if b is None or fr is None:
            return
        t = calc.totals(b)
        n = t.fringe_lines.get(fr.id, 0)
        problem = t.fringe_problems.get(fr.id, "")
        self.sums.set("lines", f"{n} line{'s' if n != 1 else ''}")
        self.sums.set("total", problem or short_money(t.fringes.get(fr.id, Decimal(0)), b))

    def _name(self, text: str) -> None:
        if self.fr is not None and not self._loading:
            self.fr.name = text.strip()
            self.edited()

    def _kind(self) -> None:
        if self.fr is not None and not self._loading:
            self.fr.kind = self.kind.currentData()
            self._shape()
            self.numbers()
            self.edited()

    def _set(self, attr: str, text: str) -> None:
        if self.fr is not None and not self._loading:
            setattr(self.fr, attr, text.strip())
            self.numbers()
            self.edited()

    def _notes(self) -> None:
        if self.fr is not None and not self._loading:
            self.fr.notes = self.notes.text()
            self.edited()
