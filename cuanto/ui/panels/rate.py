"""A rate in the library, on the right: a crew position (union or not) or a vendor's price, kept once and
used in any budget. A rate's fringes are names; a budget's fringes with those names go on lines made from it."""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QPushButton, QWidget

from cuanto.core import web
from cuanto.core.model import RATE_KINDS, UNIT_NAMES, UNITS, Rate, now_iso
from cuanto.core.store import Library
from cuanto.ui.components.widgets import (
    Card,
    Section,
    TextBox,
    TitleEdit,
    ToggleRow,
    combo,
    hbox,
    set_combo,
)
from cuanto.ui.panels.base import DetailsBase, field, offer_words, set_text
from cuanto.ui.style import tokens

KIND_LABELS = {"crew": "Crew", "vendor": "Vendor"}


class RatePanel(DetailsBase):
    KEY = "rate"
    TITLE = "Rate"

    add_wanted = Signal(str)  # to the open budget
    duplicate_wanted = Signal(str)
    delete_wanted = Signal(str)

    def __init__(self, lib: Library, parent: QWidget | None = None):
        super().__init__(parent)
        self.lib = lib
        self.r: Rate | None = None
        f = self.form_lay
        self.name = TitleEdit()
        self.name.setPlaceholderText("Gaffer, Grip Truck…")
        self.name.textEdited.connect(self._name)
        f.addWidget(self.name)
        row = hbox(spacing=tokens.SPACE_2)
        sec = Section("Kind")
        self.kind = combo([(k, KIND_LABELS[k], "") for k in RATE_KINDS], "crew")
        self.kind.activated.connect(lambda _i: self._kind())
        sec.add(self.kind)
        row.addWidget(sec, 1)
        sec, self.dept = field("Department", "Camera")
        self.dept.textEdited.connect(lambda t: self._set("department", t))
        row.addWidget(sec, 2)
        f.addLayout(row)
        row = hbox(spacing=tokens.SPACE_2)
        sec, self.rate = field("Rate", "0.00")
        self.rate.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.rate.textEdited.connect(lambda t: self._set("rate", t))
        row.addWidget(sec, 1)
        sec = Section("Per")
        self.unit = combo([(u, UNIT_NAMES[u], "") for u in UNITS], "days")
        self.unit.activated.connect(lambda _i: self._unit())
        sec.add(self.unit)
        row.addWidget(sec, 1)
        f.addLayout(row)
        self.union_card = Card("Union")
        self.union = ToggleRow("Union Rate")
        self.union.toggled.connect(self._union)
        self.union_card.add(self.union)
        self.local_sec, self.local = field("Local", "IATSE Local 600")
        self.local.textEdited.connect(lambda t: self._set("local", t))
        self.union_card.add(self.local_sec)
        f.addWidget(self.union_card)
        sec, self.fringes = field(
            "Fringes", "FICA, Union P&H", "The budget's fringes with these names go on its lines"
        )
        self.fringes.textEdited.connect(self._fringes)
        f.addWidget(sec)
        self.who_sec, self.who = field("Who", "")
        self.who.textEdited.connect(lambda t: self._set("vendor", t))
        f.addWidget(self.who_sec)
        row = hbox(spacing=tokens.SPACE_2)
        sec, self.link = field("Link", "example.com")
        self.link.textEdited.connect(lambda t: self._set("link", t))
        row.addWidget(sec, 1)
        self.open_link = QPushButton("Open ↗")
        self.open_link.setObjectName("LinkBtn")
        self.open_link.clicked.connect(self._open_link)
        row.addWidget(self.open_link, 0, Qt.AlignmentFlag.AlignBottom)
        f.addLayout(row)
        card = Card("Notes")
        self.notes = TextBox("", tokens.TEXT_BOX_H)
        self.notes.edited.connect(self._notes)
        card.add(self.notes)
        f.addWidget(card)
        self.btn_add = self.footer_button("Add to Budget…", "plus")
        self.btn_add.clicked.connect(lambda: self.r and self.add_wanted.emit(self.r.id))
        self.menu_action("copy", "Duplicate", lambda: self.r and self.duplicate_wanted.emit(self.r.id))
        self.menu_action("", "-", None)
        self.menu_action("trash", "Delete…", lambda: self.r and self.delete_wanted.emit(self.r.id))
        self.show_empty("Nothing selected")

    def load(self, r: Rate, budget_open: bool) -> None:
        self._loading = True
        self.r = r
        if self.name.text() != r.name:
            self.name.setText(r.name)
        set_combo(self.kind, r.kind)
        set_text(self.dept, r.department)
        offer_words(self.dept, self.lib.departments())
        set_text(self.rate, r.rate)
        set_combo(self.unit, r.unit)
        self.union.setChecked(r.union)
        set_text(self.local, r.local)
        set_text(self.fringes, ", ".join(r.fringes))
        set_text(self.who, r.vendor)
        set_text(self.link, r.link)
        self.notes.set_text(r.notes)
        self.btn_add.setVisible(budget_open)
        self._loading = False
        self._shape()
        self.show_form()
        self.footer.setVisible(budget_open)

    def _shape(self) -> None:
        crew = self.r is not None and self.r.kind == "crew"
        self.union_card.setVisible(crew)
        self.local_sec.setVisible(crew and self.r.union)
        self.who_sec.set_title("Who" if crew else "Vendor")
        self.who.setPlaceholderText("A name, if it's someone's rate" if crew else "Who it's from")
        self.open_link.setEnabled(bool(web.web_link(self.link.text())))

    def _touch(self) -> None:
        if self.r is not None:
            self.r.updated = now_iso()
        self.edited()

    def _name(self, text: str) -> None:
        if self.r is not None and not self._loading:
            self.r.name = text.strip()
            self._touch()

    def _set(self, attr: str, text: str) -> None:
        if self.r is not None and not self._loading:
            setattr(self.r, attr, text.strip())
            self._shape()
            self._touch()

    def _kind(self) -> None:
        if self.r is not None and not self._loading:
            self.r.kind = self.kind.currentData()
            self._shape()
            self._touch()

    def _unit(self) -> None:
        if self.r is not None and not self._loading:
            self.r.unit = self.unit.currentData()
            self._touch()

    def _union(self, on: bool) -> None:
        if self.r is not None and not self._loading:
            self.r.union = on
            self._shape()
            self._touch()

    def _fringes(self, text: str) -> None:
        if self.r is not None and not self._loading:
            self.r.fringes = [x.strip() for x in text.split(",") if x.strip()]
            self._touch()

    def _notes(self) -> None:
        if self.r is not None and not self._loading:
            self.r.notes = self.notes.text()
            self._touch()

    def _open_link(self) -> None:
        link = web.web_link(self.link.text())  # only a plain web link ever opens
        if link:
            QDesktopServices.openUrl(QUrl("https://" + link.split("://", 1)[1]))
