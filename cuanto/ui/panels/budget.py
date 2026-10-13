"""A budget on the right (from All Budgets): its name, what it's for (the words at the top of its pages),
whose profile prints it, its currency, its notes, and what it comes to."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLineEdit, QWidget

from cuanto.core import calc
from cuanto.core.model import CURRENCIES, KIND_NAMES, STAGE_NAMES, Budget
from cuanto.core.store import Library
from cuanto.ui.components.widgets import (
    Card,
    Section,
    TextBox,
    TitleEdit,
    chip,
    combo,
    hbox,
    set_combo,
    set_tone,
)
from cuanto.ui.panels.base import DetailsBase, Numbers, field, set_text
from cuanto.ui.style import tokens
from cuanto.ui.window.tables import short_money

INFO = [  # BudgetInfo field, label, placeholder
    ("client", "Client", "Who it's for"),
    ("company", "Production Company", ""),
    ("director", "Director", ""),
    ("producer", "Producer", ""),
    ("format", "Format", "4K, 2.39:1"),
    ("dates", "Shoot Dates", "Nov 2–27, 2026"),
    ("location", "Location", ""),
]


class BudgetPanel(DetailsBase):
    KEY = "budget"
    TITLE = "Budget"
    MORE_TIP = "Duplicate, export, delete"

    open_wanted = Signal(str)
    duplicate_wanted = Signal(str)
    export_wanted = Signal(str)
    delete_wanted = Signal(str)

    def __init__(self, lib: Library, parent: QWidget | None = None):
        super().__init__(parent)
        self.lib = lib
        self.budget: Budget | None = None
        f = self.form_lay
        self.name = TitleEdit()
        self.name.setPlaceholderText("Budget name")
        self.name.textEdited.connect(self._name)
        f.addWidget(self.name)
        row = hbox(spacing=tokens.SPACE_2)
        self.stage = chip()
        self.kind = chip()
        row.addWidget(self.stage)
        row.addWidget(self.kind)
        row.addStretch(1)
        f.addLayout(row)
        self.sums = Numbers("Totals", [("atl", "Above the Line"), ("btl", "Below the Line"), ("fees", "Fees"),
                                       ("grand", "Grand Total")])  # fmt: skip
        f.addWidget(self.sums)
        card = Card("Production")
        self.fields: dict[str, QLineEdit] = {}
        pairs = [INFO[0:2], INFO[2:4], INFO[4:6], INFO[6:7]]
        for pair in pairs:
            r = hbox(spacing=tokens.SPACE_2)
            for key, label, ph in pair:
                sec, w = field(label, ph)
                w.textEdited.connect(lambda t, k=key: self._info(k, t))
                self.fields[key] = w
                r.addWidget(sec, 1)
            card.add(r)
        f.addWidget(card)
        card = Card("Paper")
        r = hbox(spacing=tokens.SPACE_2)
        sec = Section("Profile")
        self.profile = combo([], "")
        self.profile.setToolTip("Whose name, logo and contact print on it")
        self.profile.activated.connect(lambda _i: self._profile())
        sec.add(self.profile)
        r.addWidget(sec, 2)
        sec = Section("Currency")
        self.currency = combo([(c, c, "") for c in CURRENCIES], "USD")
        self.currency.activated.connect(lambda _i: self._currency())
        sec.add(self.currency)
        r.addWidget(sec, 1)
        card.add(r)
        f.addWidget(card)
        card = Card("Notes")
        self.notes = TextBox("Printed under the top sheet", tokens.TEXT_BOX_TALL)
        self.notes.edited.connect(self._notes)
        card.add(self.notes)
        f.addWidget(card)
        btn = self.footer_button("Open Top Sheet", "receipt")
        btn.clicked.connect(lambda: self.budget and self.open_wanted.emit(self.budget.id))
        self.menu_action(
            "copy", "Duplicate", lambda: self.budget and self.duplicate_wanted.emit(self.budget.id)
        )
        self.menu_action(
            "share", "Export JSON…", lambda: self.budget and self.export_wanted.emit(self.budget.id)
        )
        self.menu_action("", "-", None)
        self.menu_action("trash", "Delete…", lambda: self.budget and self.delete_wanted.emit(self.budget.id))
        self.show_empty("Nothing selected")

    def load(self, budget: Budget) -> None:
        self._loading = True
        self.budget = budget
        if self.name.text() != budget.name:
            self.name.setText(budget.name)
        set_tone(self.stage, budget.stage, STAGE_NAMES.get(budget.stage, ""))
        set_tone(self.kind, "", KIND_NAMES.get(budget.kind, ""))
        for key, w in self.fields.items():
            set_text(w, getattr(budget.info, key))
        self.profile.clear()
        self.profile.addItem("The Profile in Use", "")
        for p in self.lib.profiles.values():
            self.profile.addItem(p.name or "Unnamed Profile", p.id)
        set_combo(self.profile, budget.profile_id if budget.profile_id in self.lib.profiles else "")
        if self.currency.findData(budget.currency) < 0:
            self.currency.addItem(budget.currency, budget.currency)
        set_combo(self.currency, budget.currency)
        self.notes.set_text(budget.info.notes)
        self._loading = False
        self.numbers()
        self.show_form()

    def numbers(self) -> None:
        b = self.budget
        if b is None:
            return
        t = calc.totals(b)
        self.sums.set("atl", short_money(t.atl.total, b))
        self.sums.set("btl", short_money(t.btl.total, b))
        self.sums.set("fees", short_money(t.fees, b))
        self.sums.set("grand", short_money(t.grand, b))

    def _name(self, text: str) -> None:
        if self.budget is not None and not self._loading:
            self.budget.name = text.strip()
            self.edited()

    def _info(self, key: str, text: str) -> None:
        if self.budget is not None and not self._loading:
            setattr(self.budget.info, key, text.strip())
            self.edited()

    def _notes(self) -> None:
        if self.budget is not None and not self._loading:
            self.budget.info.notes = self.notes.text()
            self.edited()

    def _profile(self) -> None:
        if self.budget is not None and not self._loading:
            self.budget.profile_id = self.profile.currentData() or ""
            self.edited()

    def _currency(self) -> None:
        if self.budget is not None and not self._loading:
            self.budget.currency = self.currency.currentData()
            self.numbers()
            self.edited()
