"""Small windows for picking: a new budget (its name and the template it starts from), a rate from the
library, an account to put a line in."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QWidget

from cuanto.core import money, rates, templates
from cuanto.core.model import UNIT_NAMES, Budget, Rate
from cuanto.ui.components.widgets import SearchField, Section, button_row, combo, vbox
from cuanto.ui.style import theme, tokens


def _title(d: QDialog, text: str, lay) -> None:
    d.setWindowTitle(text)
    t = QLabel(text)
    t.setObjectName("DialogTitle")
    lay.addWidget(t)


def _buttons(d: QDialog, lay, action: str) -> QPushButton:
    row = button_row()
    cancel = QPushButton("Cancel")
    cancel.clicked.connect(d.reject)
    go = QPushButton(action)
    go.setObjectName("Primary")
    go.setDefault(True)
    go.clicked.connect(d.accept)
    row.addWidget(cancel)
    row.addWidget(go)
    lay.addLayout(row)
    return go


class NewBudgetDialog(QDialog):
    """A name and a template. After Create: `.name`, `.kind`."""

    def __init__(self, parent: QWidget | None = None, kind: str = "feature"):
        super().__init__(parent)
        self.setMinimumWidth(tokens.DIALOG_W)
        lay = vbox(self, tokens.SPACE_5, tokens.SPACE_3)
        _title(self, "New Budget", lay)
        sec = Section("Name")
        self.field = QLineEdit()
        self.field.setPlaceholderText("The Long Night")
        sec.add(self.field)
        lay.addWidget(sec)
        sec = Section("Start From")
        self.template = combo([(k, name, "") for k, name in templates.choices()], kind)
        sec.add(self.template)
        lay.addWidget(sec)
        _buttons(self, lay, "Create")

    @property
    def name(self) -> str:
        return self.field.text().strip()

    @property
    def kind(self) -> str:
        return self.template.currentData()


def rate_words(r: Rate) -> str:
    """One line about a rate: "Gaffer · Electric · IATSE Local 728 · $725.00 / Day"."""
    per = UNIT_NAMES[r.unit]
    per = per[:-1] if per.endswith("s") and r.unit in ("days", "weeks", "hours", "months") else per
    price = f"{money.fmt(money.parse(r.rate))} / {per}" if r.rate.strip() else ""
    union = (r.local or "Union") if r.union else ""
    return "  ·  ".join(x for x in (r.name or "Untitled Rate", r.department, union, r.vendor, price) if x)


class RatePicker(QDialog):
    """Search the rate library and pick one. After Use: `.rate_id`."""

    def __init__(self, items: list[Rate], parent: QWidget | None = None, hint: str = ""):
        super().__init__(parent)
        self.resize(*tokens.PICKER_SIZE)
        lay = vbox(self, tokens.SPACE_5, tokens.SPACE_3)
        _title(self, "Use a Rate", lay)
        self.search = SearchField()
        self.search.setProperty("capsule", True)
        self.search.setPlaceholderText("Search")
        self.search.setClearButtonEnabled(True)
        self.search.addAction(theme.icon("search", theme.FAINT), QLineEdit.ActionPosition.LeadingPosition)
        self.search.textChanged.connect(self._filter)
        lay.addWidget(self.search)
        self.list = QListWidget()
        self.list.setObjectName("Picker")
        for r in items:
            it = QListWidgetItem(rate_words(r))
            it.setData(Qt.ItemDataRole.UserRole, r.id)
            it.setData(Qt.ItemDataRole.UserRole + 1, rates.haystack(r))
            it.setToolTip(theme.plain_tip(rate_words(r)))
            self.list.addItem(it)
        self.list.itemDoubleClicked.connect(lambda _i: self.accept())
        lay.addWidget(self.list, 1)
        self.go = _buttons(self, lay, "Use")
        self.list.currentItemChanged.connect(
            lambda cur, _p: self.go.setEnabled(cur is not None and not cur.isHidden())
        )
        self.search.setText(hint)
        self._filter(hint)
        self.search.setFocus()

    def _filter(self, text: str) -> None:
        words = text.casefold().split()
        first = None
        for i in range(self.list.count()):
            it = self.list.item(i)
            ok = all(w in it.data(Qt.ItemDataRole.UserRole + 1) for w in words)
            it.setHidden(not ok)
            if ok and first is None:
                first = it
        if first is None and words:  # nothing matches every word: show everything rather than nothing
            for i in range(self.list.count()):
                self.list.item(i).setHidden(False)
            first = self.list.item(0)
        self.list.setCurrentItem(first)
        self.go.setEnabled(first is not None)

    @property
    def rate_id(self) -> str:
        it = self.list.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it is not None else ""


class AccountPicker(QDialog):
    """Pick one of a budget's accounts. After the action: `.account_id`."""

    def __init__(
        self, budget: Budget, title: str, action: str, current: str = "", parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.setMinimumWidth(tokens.DIALOG_W)
        lay = vbox(self, tokens.SPACE_5, tokens.SPACE_3)
        _title(self, title, lay)
        sec = Section("Account")
        items = []
        for c, a in budget.accounts():
            words = f"{a.code}  {a.name or 'Untitled Account'}".strip()
            items.append((a.id, f"{words}  ·  {c.name}" if c.name else words, ""))
        self.pick = combo(items, current)
        sec.add(self.pick)
        lay.addWidget(sec)
        go = _buttons(self, lay, action)
        go.setEnabled(bool(items))

    @property
    def account_id(self) -> str:
        return self.pick.currentData() or ""
