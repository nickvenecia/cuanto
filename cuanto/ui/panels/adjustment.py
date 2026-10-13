"""A fee on the top sheet, on the right: contingency, a production fee, a markup. A percent of what it's on
(above and below the line, below the line, production only, or everything above it), or a flat amount."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from cuanto.core import calc
from cuanto.core.model import ADJUSTMENT_BASES, BASE_NAMES, Adjustment, Budget
from cuanto.ui.components.widgets import Section, TitleEdit, combo, hbox, set_combo
from cuanto.ui.panels.base import DetailsBase, Numbers, formula_field, offer_globals, set_text
from cuanto.ui.style import tokens
from cuanto.ui.window.tables import short_money


class AdjustmentPanel(DetailsBase):
    KEY = "adjustment"
    TITLE = "Fee"
    MORE_TIP = "Move, delete"

    delete_wanted = Signal(str)
    step_wanted = Signal(str, int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.budget: Budget | None = None
        self.adj: Adjustment | None = None
        f = self.form_lay
        self.name = TitleEdit()
        self.name.setPlaceholderText("Contingency, Production Fee…")
        self.name.textEdited.connect(self._name)
        f.addWidget(self.name)
        row = hbox(spacing=tokens.SPACE_2)
        sec = Section("Kind")
        self.kind = combo([("percent", "Percent", ""), ("flat", "Flat Amount", "")], "percent")
        self.kind.activated.connect(lambda _i: self._kind())
        sec.add(self.kind)
        row.addWidget(sec, 1)
        self.rate_sec, self.rate = formula_field("Rate %", "10")
        self.rate.textEdited.connect(self._rate)
        row.addWidget(self.rate_sec, 1)
        f.addLayout(row)
        self.base_sec = Section("Of")
        self.base = combo([(k, BASE_NAMES[k], "") for k in ADJUSTMENT_BASES], "atl_btl")
        self.base.activated.connect(lambda _i: self._base())
        self.base_sec.add(self.base)
        f.addWidget(self.base_sec)
        self.sums = Numbers("", [("base", "On"), ("amount", "Comes To")])
        f.addWidget(self.sums)
        self.menu_action("arrow-up", "Move Up", lambda: self.adj and self.step_wanted.emit(self.adj.id, -1))
        self.menu_action(
            "arrow-down", "Move Down", lambda: self.adj and self.step_wanted.emit(self.adj.id, 1)
        )
        self.menu_action("", "-", None)
        self.menu_action("trash", "Delete…", lambda: self.adj and self.delete_wanted.emit(self.adj.id))
        self.show_empty("Nothing selected")

    def load(self, budget: Budget, adj: Adjustment) -> None:
        self._loading = True
        self.budget, self.adj = budget, adj
        if self.name.text() != adj.name:
            self.name.setText(adj.name)
        set_combo(self.kind, adj.kind)
        set_text(self.rate, adj.rate)
        offer_globals(self.rate, [g.name for g in budget.globals if g.name])
        set_combo(self.base, adj.base)
        self._loading = False
        self._shape()
        self.numbers()
        self.show_form()

    def _shape(self) -> None:
        pct = self.adj is not None and self.adj.kind == "percent"
        self.rate_sec.set_title("Rate %" if pct else "Amount")
        self.base_sec.setVisible(pct)
        self.sums.values["base"].setVisible(pct)
        self.sums.labels["base"].setVisible(pct)

    def numbers(self) -> None:
        b, adj = self.budget, self.adj
        if b is None or adj is None:
            return
        t = calc.totals(b)
        got = next((a for a in t.adjustments if a.id == adj.id), None)
        if got is None:
            return
        self.sums.set("base", short_money(got.base, b))
        self.sums.set("amount", got.problem or short_money(got.amount, b))

    def _name(self, text: str) -> None:
        if self.adj is not None and not self._loading:
            self.adj.name = text.strip()
            self.edited()

    def _kind(self) -> None:
        if self.adj is not None and not self._loading:
            self.adj.kind = self.kind.currentData()
            self._shape()
            self.numbers()
            self.edited()

    def _rate(self, text: str) -> None:
        if self.adj is not None and not self._loading:
            self.adj.rate = text.strip()
            self.numbers()
            self.edited()

    def _base(self) -> None:
        if self.adj is not None and not self._loading:
            self.adj.base = self.base.currentData()
            self.numbers()
            self.edited()
