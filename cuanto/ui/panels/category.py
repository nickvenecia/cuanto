"""A category (a top-sheet row) on the right: its code and name, which section it's in, and what it adds up to."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from cuanto.core import calc
from cuanto.core.model import SECTION_NAMES, SECTIONS, Budget, Category
from cuanto.ui.components.widgets import Card, Section, TextBox, TitleEdit, combo, hbox, set_combo
from cuanto.ui.panels.base import DetailsBase, Numbers, field, set_text
from cuanto.ui.style import tokens
from cuanto.ui.window.tables import short_money


class CategoryPanel(DetailsBase):
    KEY = "category"
    TITLE = "Category"
    MORE_TIP = "Move, delete"

    new_account = Signal(str)  # in this category
    show_accounts = Signal(str)
    delete_wanted = Signal(str)
    step_wanted = Signal(str, int)
    section_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.budget: Budget | None = None
        self.category: Category | None = None
        f = self.form_lay
        self.name = TitleEdit()
        self.name.setPlaceholderText("Category name")
        self.name.textEdited.connect(self._name)
        f.addWidget(self.name)
        row = hbox(spacing=tokens.SPACE_2)
        sec, self.code = field("Acct #", "2300")
        self.code.textEdited.connect(self._code)
        row.addWidget(sec, 1)
        sec = Section("Section")
        self.section = combo([(s, SECTION_NAMES[s], "") for s in SECTIONS], "production")
        self.section.activated.connect(lambda _i: self._section())
        sec.add(self.section)
        row.addWidget(sec, 2)
        f.addLayout(row)
        self.sums = Numbers("Totals", [("accounts", "Accounts"), ("lines", "Lines"), ("subtotal", "Before Fringes"),
                                       ("fringes", "Fringes"), ("total", "Total")])  # fmt: skip
        f.addWidget(self.sums)
        notes = Card("Notes")
        self.notes = TextBox("", tokens.TEXT_BOX_TALL)
        self.notes.edited.connect(self._notes)
        notes.add(self.notes)
        f.addWidget(notes)
        btn = self.footer_button("New Account", "plus")
        btn.clicked.connect(lambda: self.category and self.new_account.emit(self.category.id))
        self.menu_action(
            "table", "Show Its Accounts", lambda: self.category and self.show_accounts.emit(self.category.id)
        )
        self.menu_action(
            "arrow-up", "Move Up", lambda: self.category and self.step_wanted.emit(self.category.id, -1)
        )
        self.menu_action(
            "arrow-down", "Move Down", lambda: self.category and self.step_wanted.emit(self.category.id, 1)
        )
        self.menu_action("", "-", None)
        self.menu_action(
            "trash", "Delete…", lambda: self.category and self.delete_wanted.emit(self.category.id)
        )
        self.show_empty("Nothing selected")

    def load(self, budget: Budget, category: Category) -> None:
        self._loading = True
        self.budget, self.category = budget, category
        if self.name.text() != category.name:
            self.name.setText(category.name)
        set_text(self.code, category.code)
        set_combo(self.section, category.section)
        self.notes.set_text(category.notes)
        self._loading = False
        self.numbers()
        self.show_form()

    def numbers(self) -> None:
        b, c = self.budget, self.category
        if b is None or c is None:
            return
        s = calc.totals(b).categories.get(c.id, calc.Sum())
        self.sums.set("accounts", f"{len(c.accounts):,}")
        self.sums.set("lines", f"{s.lines:,}")
        self.sums.set("subtotal", short_money(s.subtotal, b))
        self.sums.set("fringes", short_money(s.fringes, b))
        self.sums.set("total", short_money(s.total, b))

    def _name(self, text: str) -> None:
        if self.category is not None and not self._loading:
            self.category.name = text.strip()
            self.edited()

    def _code(self, text: str) -> None:
        if self.category is not None and not self._loading:
            self.category.code = text.strip()
            self.edited()

    def _notes(self) -> None:
        if self.category is not None and not self._loading:
            self.category.notes = self.notes.text()
            self.edited()

    def _section(self) -> None:
        if self.category is None or self._loading:
            return
        s = self.section.currentData()
        if s != self.category.section:
            self.category.section = s
            self.edited()
            self.section_changed.emit(self.category.id)
