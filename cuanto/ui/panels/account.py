"""An account on the right: its code and name, which category it's in, what it adds up to, and the fringes
on its lines (a switch puts a fringe on every line of the account at once)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from cuanto.core import calc
from cuanto.core.model import Account, Budget, Category
from cuanto.ui.components.widgets import Card, Section, TextBox, TitleEdit, ToggleRow, combo, hbox, set_combo
from cuanto.ui.panels.base import DetailsBase, Numbers, field, set_text
from cuanto.ui.style import tokens
from cuanto.ui.window.tables import short_money


class AccountPanel(DetailsBase):
    KEY = "account"
    TITLE = "Account"
    MORE_TIP = "Duplicate, move, delete"

    new_line = Signal(str)  # in this account
    moved = Signal(str, str)  # account id, the category it goes to
    duplicate_wanted = Signal(str)
    delete_wanted = Signal(str)
    step_wanted = Signal(str, int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.budget: Budget | None = None
        self.category: Category | None = None
        self.account: Account | None = None
        f = self.form_lay
        self.name = TitleEdit()
        self.name.setPlaceholderText("Account name")
        self.name.textEdited.connect(self._name)
        f.addWidget(self.name)
        row = hbox(spacing=tokens.SPACE_2)
        sec, self.code = field("Acct #", "2301")
        self.code.textEdited.connect(self._code)
        row.addWidget(sec, 1)
        self.cat_sec = Section("Category")
        self.cat = combo([], "")
        self.cat.activated.connect(lambda _i: self._move())
        self.cat_sec.add(self.cat)
        row.addWidget(self.cat_sec, 2)
        f.addLayout(row)
        self.sums = Numbers("Totals", [("lines", "Lines"), ("subtotal", "Before Fringes"), ("fringes", "Fringes"),
                                       ("total", "Total")])  # fmt: skip
        f.addWidget(self.sums)
        self.fringe_card = Card("Fringes on Every Line")
        self.fringe_rows: dict[str, ToggleRow] = {}
        f.addWidget(self.fringe_card)
        notes = Card("Notes")
        self.notes = TextBox("", tokens.TEXT_BOX_TALL)
        self.notes.edited.connect(self._notes)
        notes.add(self.notes)
        f.addWidget(notes)
        btn = self.footer_button("New Line", "plus")
        btn.clicked.connect(lambda: self.account and self.new_line.emit(self.account.id))
        self.menu_action(
            "copy", "Duplicate", lambda: self.account and self.duplicate_wanted.emit(self.account.id)
        )
        self.menu_action(
            "arrow-up", "Move Up", lambda: self.account and self.step_wanted.emit(self.account.id, -1)
        )
        self.menu_action(
            "arrow-down", "Move Down", lambda: self.account and self.step_wanted.emit(self.account.id, 1)
        )
        self.menu_action("", "-", None)
        self.menu_action(
            "trash", "Delete…", lambda: self.account and self.delete_wanted.emit(self.account.id)
        )
        self.show_empty("Nothing selected")

    def load(self, budget: Budget, category: Category, account: Account) -> None:
        self._loading = True
        self.budget, self.category, self.account = budget, category, account
        if self.name.text() != account.name:
            self.name.setText(account.name)
        set_text(self.code, account.code)
        self.cat.clear()
        for c in budget.categories:
            self.cat.addItem(f"{c.code}  {c.name}".strip() or "Untitled Category", c.id)
        set_combo(self.cat, category.id)
        self.notes.set_text(account.notes)
        for row in self.fringe_rows.values():
            row.setParent(None)
            row.deleteLater()
        self.fringe_rows = {}
        for fr in budget.fringes:
            t = ToggleRow(fr.name or "Untitled Fringe")
            t.toggled.connect(lambda on, fid=fr.id: self._fringe(fid, on))
            self.fringe_card.add(t)
            self.fringe_rows[fr.id] = t
        self.fringe_card.setVisible(bool(budget.fringes) and bool(account.lines))
        self._loading = False
        self.numbers()
        self.show_form()

    def numbers(self) -> None:
        b, a = self.budget, self.account
        if b is None or a is None:
            return
        t = calc.totals(b)
        s = t.accounts.get(a.id, calc.Sum())
        self.sums.set("lines", f"{len(a.lines):,}")
        self.sums.set("subtotal", short_money(s.subtotal, b))
        self.sums.set("fringes", short_money(s.fringes, b))
        self.sums.set("total", short_money(s.total, b))
        self._loading = True
        for fid, row in self.fringe_rows.items():
            on = sum(1 for ln in a.lines if fid in ln.fringes)
            row.setChecked(bool(a.lines) and on == len(a.lines))
            fr = b.fringe(fid)
            name = fr.name if fr is not None and fr.name else "Untitled Fringe"
            row.setText(f"{name}  ·  {on} of {len(a.lines)}" if 0 < on < len(a.lines) else name)
        self._loading = False

    # ------------------------------------------------------------------ edits
    def _name(self, text: str) -> None:
        if self.account is not None and not self._loading:
            self.account.name = text.strip()
            self.edited()

    def _code(self, text: str) -> None:
        if self.account is not None and not self._loading:
            self.account.code = text.strip()
            self.edited()

    def _notes(self) -> None:
        if self.account is not None and not self._loading:
            self.account.notes = self.notes.text()
            self.edited()

    def _move(self) -> None:
        if self.account is None or self._loading:
            return
        to = self.cat.currentData()
        if self.category is not None and to != self.category.id:
            self.moved.emit(self.account.id, to)

    def _fringe(self, fid: str, on: bool) -> None:
        if self.account is None or self._loading:
            return
        for ln in self.account.lines:
            have = [f for f in ln.fringes if f != fid]
            if on:
                want = set(have) | {fid}
                have = [f.id for f in self.budget.fringes if f.id in want]
            ln.fringes = have
        self.numbers()
        self.edited()
