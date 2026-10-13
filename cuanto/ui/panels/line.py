"""A line on the right: what it is, how many of how many units at what rate (numbers or formulas over the
globals), which fringes go on it, where its rate came from, and its notes. Its total is worked out as you type.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QWidget

from cuanto.core import calc, formula
from cuanto.core.model import UNIT_NAMES, UNITS, Account, Budget, Category, Line
from cuanto.ui.components.widgets import (
    Card,
    ElidedLabel,
    TextBox,
    TitleEdit,
    ToggleRow,
    add_chip,
    combo,
    hbox,
    icon_button,
    set_combo,
    vbox,
)
from cuanto.ui.panels.base import DetailsBase, formula_field, offer_globals, set_text
from cuanto.ui.style import theme, tokens
from cuanto.ui.window.tables import qty, short_money


class LinePanel(DetailsBase):
    KEY = "line"
    TITLE = "Line"
    MORE_TIP = "Duplicate, move, delete"

    open_account = Signal(str)
    new_line = Signal(str)  # after this line
    duplicate_wanted = Signal(str)
    delete_wanted = Signal(str)
    step_wanted = Signal(str, int)  # up (-1) or down (+1)
    move_wanted = Signal(str)  # to another account
    use_rate_wanted = Signal(str)
    save_rate_wanted = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.budget: Budget | None = None
        self.category: Category | None = None
        self.account: Account | None = None
        self.ln: Line | None = None
        f = self.form_lay

        self.where = QPushButton()
        self.where.setObjectName("LinkBtn")
        self.where.setCursor(Qt.CursorShape.PointingHandCursor)
        self.where.setToolTip("Open its account")
        self.where.clicked.connect(lambda: self.account and self.open_account.emit(self.account.id))
        f.addWidget(self.where)
        self.name = TitleEdit()
        self.name.setPlaceholderText("What it is")
        self.name.textEdited.connect(self._name)
        f.addWidget(self.name)
        totals = vbox(spacing=0)
        self.total = QLabel()
        self.total.setObjectName("BigTotal")
        self.breakdown = ElidedLabel()
        self.breakdown.setObjectName("Meta")
        self.problem = QLabel()
        self.problem.setObjectName("Bad")
        self.problem.setWordWrap(True)
        totals.addWidget(self.total)
        totals.addWidget(self.breakdown)
        totals.addWidget(self.problem)
        f.addLayout(totals)

        card = Card("Cost")
        row = hbox(spacing=tokens.SPACE_2)
        self.amount_sec, self.amount = formula_field("Amount", "1", "How many: people, items or units")
        self.units_sec, self.units = formula_field(
            "Units", "1", "How long: days, weeks… (a number or a global)"
        )
        self.unit_sec = QWidget()
        us = vbox(self.unit_sec, 0, tokens.SPACE_1)
        from cuanto.ui.components.widgets import section_label

        us.addWidget(section_label("Unit"))
        self.unit = combo([(u, UNIT_NAMES[u], "") for u in UNITS], "allow")
        us.addWidget(self.unit)
        row.addWidget(self.amount_sec, 2)
        row.addWidget(self.units_sec, 3)  # room for a formula: prep_days + shoot_days
        row.addWidget(self.unit_sec, 2)
        card.add(row)
        self.rate_sec, self.rate = formula_field(
            "Rate", "0.00", "Per unit. A number, or a formula with your globals"
        )
        card.add(self.rate_sec)
        f.addWidget(card)
        for w, attr in ((self.amount, "amount"), (self.units, "units"), (self.rate, "rate")):
            w.textEdited.connect(lambda t, a=attr: self._number(a, t))
        self.unit.activated.connect(lambda _i: self._unit())

        self.fringe_card = Card("Fringes")
        self.fringe_rows: dict[str, ToggleRow] = {}
        f.addWidget(self.fringe_card)

        lib = Card("Rate Library")
        self.from_rate = ElidedLabel()
        self.from_rate.setObjectName("Muted")
        lib.add(self.from_rate)
        row = hbox(spacing=tokens.SPACE_2)
        use = QPushButton("Use a Rate…")
        use.clicked.connect(lambda: self.ln and self.use_rate_wanted.emit(self.ln.id))
        keep = QPushButton("Save to Library")
        keep.setObjectName("Ghost")
        keep.clicked.connect(lambda: self.ln and self.save_rate_wanted.emit(self.ln.id))
        row.addWidget(use)
        row.addWidget(keep)
        row.addStretch(1)
        lib.add(row)
        f.addWidget(lib)

        self.notes_card = Card("Notes")
        self.notes_x = icon_button("x", "Take off the notes")
        self.notes_x.clicked.connect(self._drop_notes)
        self.notes_card.head.addWidget(self.notes_x)
        self.notes = TextBox("", tokens.TEXT_BOX_TALL)
        self.notes.edited.connect(self._notes)
        self.notes_card.add(self.notes)
        f.addWidget(self.notes_card)
        self.add_notes = add_chip("Notes")
        self.add_notes.clicked.connect(self._show_notes)
        chips = hbox(spacing=tokens.SPACE_2)
        chips.addWidget(self.add_notes)
        chips.addStretch(1)
        f.addLayout(chips)

        btn = self.footer_button("New Line", "plus")
        btn.clicked.connect(lambda: self.ln and self.new_line.emit(self.ln.id))
        self.menu_action("copy", "Duplicate", lambda: self.ln and self.duplicate_wanted.emit(self.ln.id))
        self.menu_action("arrow-up", "Move Up", lambda: self.ln and self.step_wanted.emit(self.ln.id, -1))
        self.menu_action("arrow-down", "Move Down", lambda: self.ln and self.step_wanted.emit(self.ln.id, 1))
        self.menu_action("folder", "Move to Account…", lambda: self.ln and self.move_wanted.emit(self.ln.id))
        self.menu_action(
            "tag", "Save to Rate Library", lambda: self.ln and self.save_rate_wanted.emit(self.ln.id)
        )
        self.menu_action("", "-", None)
        self.menu_action("trash", "Delete…", lambda: self.ln and self.delete_wanted.emit(self.ln.id))
        self.show_empty("Nothing selected")

    # ------------------------------------------------------------------ filling in
    def load(
        self, budget: Budget, category: Category, account: Account, ln: Line, rate_name: str = ""
    ) -> None:
        self._loading = True
        self.budget, self.category, self.account, self.ln = budget, category, account, ln
        self.where.setText(" › ".join(x for x in (
            f"{category.code} {category.name}".strip(), f"{account.code} {account.name}".strip()) if x))  # fmt: skip
        if self.name.text() != ln.description:
            self.name.setText(ln.description)
        names = [g.name for g in budget.globals if g.name]
        for w, value in ((self.amount, ln.amount), (self.units, ln.units), (self.rate, ln.rate)):
            set_text(w, value)
            offer_globals(w, names)
        set_combo(self.unit, ln.unit)
        self._fringe_rows()
        self.from_rate.set_full_text(f"From the library: {rate_name}" if rate_name else "")
        self.from_rate.setVisible(bool(rate_name))
        self.notes.set_text(ln.notes)
        self._notes_shown(bool(ln.notes.strip()))
        self._loading = False
        self.numbers()
        self.show_form()

    def _fringe_rows(self) -> None:
        b, ln = self.budget, self.ln
        for row in self.fringe_rows.values():
            row.setParent(None)
            row.deleteLater()
        self.fringe_rows = {}
        for fr in b.fringes:
            t = ToggleRow(fr.name or "Untitled Fringe", fr.id in ln.fringes)
            t.toggled.connect(lambda on, fid=fr.id: self._fringe(fid, on))
            self.fringe_card.add(t)
            self.fringe_rows[fr.id] = t
        self.fringe_card.setVisible(bool(b.fringes))

    def numbers(self) -> None:
        """The total, its parts, and what each formula and fringe comes to (after any edit)."""
        b, ln = self.budget, self.ln
        if b is None or ln is None:
            return
        t = calc.totals(b)
        lt = t.lines.get(ln.id)
        if lt is None:
            return
        self.total.setText(short_money(lt.total, b) if not lt.problem else "—")
        parts = [f"{qty(lt.amount)} × {qty(lt.units)} {UNIT_NAMES[ln.unit]} × {short_money(lt.rate, b)}"]
        if lt.fringes:
            parts.append(f"{short_money(lt.fringes, b)} fringes")
        self.breakdown.set_full_text("  ·  ".join(parts) if not lt.problem else "")
        self.problem.setText(lt.problem)
        self.problem.setVisible(bool(lt.problem))
        for sec, label, text, value in (
            (self.amount_sec, "Amount", ln.amount, lt.amount),
            (self.units_sec, "Units", ln.units, lt.units),
            (self.rate_sec, "Rate", ln.rate, lt.rate),
        ):
            shows = text.strip() and not formula.is_plain(text) and not lt.problem
            sec.set_title(f"{label}  ·  {qty(value)}" if shows else label)
        for fid, row in self.fringe_rows.items():
            fr = b.fringe(fid)
            amount = lt.by_fringe.get(fid)
            name = fr.name if fr is not None else ""
            row.setText(
                f"{name or 'Untitled Fringe'}  ·  {short_money(amount, b)}"
                if amount
                else (name or "Untitled Fringe")
            )
            row.update()

    # ------------------------------------------------------------------ edits
    def _name(self, text: str) -> None:
        if self.ln is not None and not self._loading:
            self.ln.description = text.strip()
            self.edited()

    def _number(self, attr: str, text: str) -> None:
        if self.ln is None or self._loading:
            return
        setattr(self.ln, attr, text.strip())
        self.numbers()
        self.edited()

    def _unit(self) -> None:
        if self.ln is None or self._loading:
            return
        self.ln.unit = self.unit.currentData()
        self.numbers()
        self.edited()

    def _fringe(self, fid: str, on: bool) -> None:
        if self.ln is None or self._loading:
            return
        have = [f for f in self.ln.fringes if f != fid]
        if on:  # in the budget's order
            want = set(have) | {fid}
            have = [f.id for f in self.budget.fringes if f.id in want]
        self.ln.fringes = have
        self.numbers()
        self.edited()

    def _notes(self) -> None:
        if self.ln is not None and not self._loading:
            self.ln.notes = self.notes.text()
            self.notes_x.setVisible(not self.ln.notes.strip())
            self.edited()

    def _notes_shown(self, on: bool) -> None:
        self.notes_card.setVisible(on)
        self.add_notes.setVisible(not on)
        self.notes_x.setVisible(on and not self.notes.text().strip())

    def _show_notes(self) -> None:
        self._notes_shown(True)
        self.notes.setFocus()

    def _drop_notes(self) -> None:
        if self.ln is not None and not self.ln.notes.strip():
            self._notes_shown(False)

    def recolor(self) -> None:
        self.notes_x.setIcon(theme.icon("x", theme.MUTED, tokens.ICON_SM))
        self.add_notes.setIcon(theme.icon("plus", theme.ACCENT, tokens.ICON_SM))
