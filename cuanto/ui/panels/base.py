"""What every panel on the right shares, on top of components.panels.SidePanel: an empty state, a form of
Cards, the ⋯ menu, a footer for the one main action, and the small form pieces they're built from (a
labelled field, a formula field that knows the budget's globals, a card of totals)."""

from __future__ import annotations

from PySide6.QtCore import QStringListModel, Qt, QTimer, Signal
from PySide6.QtWidgets import QCompleter, QLabel, QLineEdit, QPushButton, QWidget

from cuanto.ui.components.panels import SidePanel
from cuanto.ui.components.widgets import Card, ElidedLabel, Section, hbox, suggestions, vbox
from cuanto.ui.style import theme, tokens


class DetailsBase(SidePanel):
    """A thing on the right, editable: the SidePanel frame (with ⋯), an empty state and a form."""

    changed = Signal()  # something in the open thing was changed (it saves itself)
    toast_wanted = Signal(str, str)

    KEY = ""
    TITLE = ""
    MORE_TIP = "Duplicate, delete"

    def __init__(self, parent: QWidget | None = None):
        super().__init__(self.TITLE, more=True, parent=parent)
        self._loading = False
        self.more.setToolTip(self.MORE_TIP)
        self.header_buttons: list[QWidget] = [self.more]
        self.more.hide()

        self.empty = QWidget()
        el = vbox(self.empty, (0, tokens.SPACE_5, 0, 0), tokens.SPACE_3)
        self.empty_title = QLabel()
        self.empty_title.setObjectName("EmptyTitle")
        self.empty_title.setWordWrap(True)
        el.addWidget(self.empty_title)
        self.lay.addWidget(self.empty)

        self.form = QWidget()
        self.form_lay = vbox(self.form, 0, tokens.SPACE_3)
        self.lay.addWidget(self.form)
        self.lay.addStretch(1)

    def show_empty(self, title: str) -> None:
        self.form.hide()
        self.empty.show()
        self.empty_title.setText(title)
        for b in self.header_buttons:
            b.hide()
        self.footer.hide()

    def show_form(self) -> None:
        self.empty.hide()
        self.form.show()
        for b in self.header_buttons:
            b.show()
        self.footer.setVisible(self.footer_lay.count() > 0)

    def menu_action(self, icon: str, text: str, slot) -> None:
        """A command under the header's ⋯ (Duplicate, Delete…). Destructive ones go last, after a "-"."""
        if text == "-":
            self.more_menu.addSeparator()
        else:
            self.more_menu.addAction(theme.menu_icon(icon), text, lambda: self.later(slot))

    def later(self, fn) -> None:
        QTimer.singleShot(0, self, fn)

    def edited(self) -> None:
        """Tell the window something changed (unless the form is being filled in)."""
        if not self._loading:
            self.changed.emit()


# ---------------------------------------------------------------------------- form pieces
def field(label: str, placeholder: str = "", tip: str = "") -> tuple[Section, QLineEdit]:
    sec = Section(label)
    f = QLineEdit()
    f.setPlaceholderText(placeholder)
    if tip:
        f.setToolTip(tip)
    sec.add(f)
    return sec, f


def formula_field(label: str, placeholder: str = "", tip: str = "") -> tuple[Section, QLineEdit]:
    """A number or a formula over the budget's globals; typing a global's name offers it."""
    sec, f = field(label, placeholder, tip or "A number, or a formula with your globals: shoot_days + 2")
    f.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return sec, f


def offer_words(f: QLineEdit, words: list[str]) -> None:
    """Type-ahead of `words` in a field (in the shared list look). The field keeps one completer and only
    its list changes, so loading a panel again and again doesn't pile up popups."""
    c = f.completer()
    if c is None:
        c = QCompleter(f)
        c.setModel(QStringListModel(c))
        c.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        f.setCompleter(suggestions(c))
    c.model().setStringList(words)


def offer_globals(f: QLineEdit, names: list[str]) -> None:
    """Type-ahead of the budget's global names in a formula field."""
    offer_words(f, names)


def set_text(f: QLineEdit, text: str) -> None:
    """Fill a field without it counting as an edit (and without moving the cursor if it's the same)."""
    if f.text() != text:
        f.blockSignals(True)
        f.setText(text)
        f.setCursorPosition(0)  # a long formula shows from its start
        f.blockSignals(False)


class Numbers(Card):
    """A card of figures: a label on the left, its value on the right, one per row."""

    def __init__(
        self, title: str = "", rows: list[tuple[str, str]] | None = None, parent: QWidget | None = None
    ):
        super().__init__(title, parent)
        self.values: dict[str, QLabel] = {}
        self.labels: dict[str, QLabel] = {}
        for key, text in rows or []:
            row = hbox(spacing=tokens.SPACE_2)
            k = ElidedLabel(text)
            k.setObjectName("SumLabel")
            v = QLabel()
            v.setObjectName("SumValue")
            v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(k, 1)
            row.addWidget(v)
            self.add(row)
            self.values[key], self.labels[key] = v, k

    def set(self, key: str, value: str, label: str | None = None) -> None:
        self.values[key].setText(value)
        if label is not None:
            self.labels[key].set_full_text(label)


def footer_plain(panel: SidePanel, text: str, icon: str = "") -> QPushButton:
    """A panel's main action as a normal button (when it isn't the view's one primary action)."""
    return panel.footer_button(text, icon, primary=False)
