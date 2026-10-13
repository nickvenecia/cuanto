"""Your profile: the production company whose name, logo and contact go on the budgets you print.

Filled in once (and more than once if you work under several companies). Each budget prints with the
profile in use, or the one it's set to.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import QDialog, QFileDialog, QLabel, QLineEdit, QPushButton, QWidget

from cuanto.core.log import get_logger
from cuanto.core.looks import COLORS, DEFAULT_COLOR
from cuanto.core.model import Profile
from cuanto.core.paths import logos_dir
from cuanto.ui.components.widgets import (
    Disclosure,
    Embeddable,
    FitScroll,
    Section,
    TextBox,
    combo,
    hbox,
    hint,
    vbox,
)
from cuanto.ui.style.tokens import (
    DIALOG_W_WIDE,
    LOGO_THUMB,
    LOGO_THUMB_MAX_W,
    PROFILE_DIALOG_H,
    SCROLL_GUTTER,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SPACE_5,
)

log = get_logger(__name__)

LOGO_MAX_PX = 1600  # bigger pictures are scaled down when added (keeps PDFs small)
LOGO_MAX_BYTES = 20_000_000  # a logo file bigger than this isn't a logo


def import_logo(src: Path) -> str:
    """Read a logo and save it again into Cuánto's own folder, as a PNG named by its content (so moving or
    deleting the original never breaks a budget, and nothing else the file carried comes along). An SVG is
    drawn into a PNG. Returns the stored file name. Raises ValueError if it isn't a picture Cuánto can read."""
    if src.stat().st_size > LOGO_MAX_BYTES:
        raise ValueError(f"{src.name} is too big for a logo. Use a smaller PNG, JPG or SVG.")
    if src.suffix.lower() == ".svg":
        from PySide6.QtSvg import QSvgRenderer

        r = QSvgRenderer(str(src))
        size = r.defaultSize()
        if not r.isValid() or size.width() <= 0 or size.height() <= 0:
            raise ValueError(f"Cuánto can't read {src.name}. Use a PNG, JPG or SVG file.")
        scale = LOGO_MAX_PX / max(size.width(), size.height())
        img = QImage(round(size.width() * scale), round(size.height() * scale), QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        r.render(p, QRectF(0, 0, img.width(), img.height()))
        p.end()
    else:
        img = QImage(str(src))
    if img.isNull():
        raise ValueError(f"Cuánto can't read {src.name}. Use a PNG, JPG or SVG file.")
    if max(img.width(), img.height()) > LOGO_MAX_PX:
        img = img.scaled(
            LOGO_MAX_PX,
            LOGO_MAX_PX,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    folder = logos_dir()
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / ".incoming.png"
    if not img.save(str(tmp), "PNG"):
        raise ValueError("Couldn't save the logo. Check that there's free space on this computer.")
    name = f"{hashlib.sha256(tmp.read_bytes()).hexdigest()[:16]}.png"
    tmp.replace(folder / name)
    return name


def logo_path(name: str) -> Path | None:
    """A profile's logo file, if it has one that's there (a name, never a path)."""
    if not name or Path(name).name != name:
        return None
    path = logos_dir() / name
    return path if path.is_file() else None


def logo_thumbnail(path: Path, height: int) -> QPixmap:
    """A sharp little picture of a logo file, `height` px tall (empty if it can't be read)."""
    dpr = 2
    pm = QPixmap(str(path))
    if pm.isNull():
        return pm
    pm = pm.scaledToHeight(height * dpr, Qt.TransformationMode.SmoothTransformation)
    pm.setDevicePixelRatio(dpr)
    return pm


class ProfileDialog(Embeddable, QDialog):
    """Add or edit a profile. After Save, `.profile` holds the result; `.deleted` if Delete was chosen."""

    def __init__(
        self, profile: Profile | None, can_delete: bool, parent: QWidget | None = None, new: bool = False
    ):
        """`new` with a profile: a new profile that starts from those values."""
        super().__init__(parent)
        self.editing = profile is not None and not new
        self.profile = replace(profile) if profile else Profile()
        self.deleted = False
        title_text = "Edit Profile" if self.editing else "Add Your Profile"
        self.setWindowTitle(title_text)
        self.setMinimumWidth(DIALOG_W_WIDE)
        self.resize(DIALOG_W_WIDE, PROFILE_DIALOG_H)
        outer = vbox(self, (0, SPACE_5, 0, SPACE_5), SPACE_3)
        head = self._head = vbox(spacing=SPACE_2)
        head.setContentsMargins(SPACE_5, 0, SPACE_5, 0)
        self.title_label = QLabel(title_text)
        self.title_label.setObjectName("DialogTitle")
        head.addWidget(self.title_label)
        outer.addLayout(head)

        body = QWidget()
        lay = self._body_lay = vbox(body, (SPACE_5, 0, SPACE_5 - SCROLL_GUTTER, 0), SPACE_3)
        p = self.profile
        self.name = self._line(lay, "Name", p.name, "Your production company")
        self.tagline = self._line(lay, "Tagline", p.tagline, "Features · Commercials · Music Videos")
        lay.addWidget(self._build_logo())

        self.contact = Disclosure("Contact", is_open=not self.editing)
        c = self.contact.lay
        self.email = self._line(c, "Email", p.email, "budgets@example.com")
        self.phone = self._line(c, "Phone", p.phone, "")
        self.website = self._line(c, "Website", p.website, "")
        self.address = self._box(c, "Address", p.address, "Street\nCity, State ZIP")
        lay.addWidget(self.contact)

        self.paper = Disclosure("Paper", is_open=True)
        sec = Section("Paper Color")
        self.color = combo([(k, v[0], "") for k, v in COLORS.items()], p.color or DEFAULT_COLOR)
        self.color.setToolTip("The accent on your top sheets and details")
        sec.add(self.color)
        self.paper.add(sec)
        self.note = self._box(self.paper.lay, "Closing Note", p.note, "Estimate valid for 30 days.")
        self.note.setToolTip("Printed under every top sheet.")
        lay.addWidget(self.paper)
        lay.addStretch(1)

        scroll = FitScroll()
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        buttons = self._buttons = hbox(spacing=SPACE_2)
        buttons.setContentsMargins(SPACE_5, SPACE_4, SPACE_5, 0)
        if self.editing and can_delete:
            delete = QPushButton("Delete Profile…")
            delete.setObjectName("Danger")
            delete.clicked.connect(self._delete)
            buttons.addWidget(delete)
        buttons.addStretch(1)
        self.cancel_btn = cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.save = QPushButton("Save")
        self.save.setObjectName("Primary")
        self.save.setDefault(True)
        self.save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(self.save)
        outer.addLayout(buttons)

        self.name.textChanged.connect(self._name_changed)
        for f in (self.email, self.phone):
            f.textChanged.connect(lambda _t: self._summaries())
        self.color.currentIndexChanged.connect(lambda _i: self._summaries())
        for group in (self.contact, self.paper):
            group.toggled.connect(lambda _on: self._summaries())
        self._name_changed(self.name.text())
        self._show_logo()

    def side_margin(self, px: int) -> None:
        """The room on the left and right (none inside Settings, which has its own)."""
        self._head.setContentsMargins(px, 0, px, 0)
        self._body_lay.setContentsMargins(px, 0, SPACE_3, 0)
        self._buttons.setContentsMargins(px, SPACE_4, SPACE_3 + SCROLL_GUTTER, 0)  # lines up with the fields

    def _line(self, lay, label: str, value: str, placeholder: str) -> QLineEdit:
        sec = Section(label)
        f = QLineEdit(value)
        f.setPlaceholderText(placeholder)
        sec.add(f)
        lay.addWidget(sec)
        return f

    def _box(self, lay, label: str, value: str, placeholder: str) -> TextBox:
        sec = Section(label)
        f = TextBox(placeholder)
        f.set_text(value)
        sec.add(f)
        lay.addWidget(sec)
        return f

    def _draft(self) -> Profile:
        p = replace(self.profile)
        p.name = self.name.text().strip()
        p.tagline = self.tagline.text().strip()
        p.email = self.email.text().strip()
        p.phone = self.phone.text().strip()
        p.website = self.website.text().strip()
        p.address = self.address.text().strip()
        p.color = self.color.currentData()
        p.note = self.note.text().strip()
        return p

    def _name_changed(self, text: str) -> None:
        self.save.setEnabled(bool(text.strip()))
        self._summaries()

    def _summaries(self) -> None:
        p = self._draft()
        self.contact.set_summary(p.email or p.phone or "")
        self.paper.set_summary(COLORS.get(p.color, COLORS[DEFAULT_COLOR])[0])

    # ------------------------------------------------------------------ logo
    def _build_logo(self) -> Section:
        sec = Section("Logo")
        row = hbox(spacing=SPACE_2)
        self.logo_thumb = QLabel()
        self.logo_thumb.setObjectName("LogoThumb")
        self.logo_thumb.setFixedHeight(LOGO_THUMB)
        self.logo_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_btn = QPushButton("Choose Logo…")
        self.logo_btn.setToolTip("PNG, JPG or SVG.")
        self.logo_btn.clicked.connect(self._choose_logo)
        self.logo_remove = QPushButton("Remove")
        self.logo_remove.setObjectName("Ghost")
        self.logo_remove.setToolTip("Leave the logo off. Cancel puts it back.")
        self.logo_remove.clicked.connect(lambda: self._set_logo(""))
        row.addWidget(self.logo_thumb)
        row.addWidget(self.logo_btn)
        row.addWidget(self.logo_remove)
        row.addStretch(1)
        sec.add(row)
        self.logo_error = hint("")
        self.logo_error.setObjectName("Bad")
        self.logo_error.hide()
        sec.add(self.logo_error)
        return sec

    def _show_logo(self) -> None:
        path = logo_path(self.profile.logo)
        pm = logo_thumbnail(path, LOGO_THUMB - SPACE_2) if path else QPixmap()
        has_logo = not pm.isNull()
        if has_logo:
            self.logo_thumb.setPixmap(pm)
            width = round(pm.width() / pm.devicePixelRatio()) + SPACE_2
            self.logo_thumb.setFixedWidth(min(width, LOGO_THUMB_MAX_W))
        self.logo_thumb.setVisible(has_logo)
        self.logo_remove.setVisible(has_logo)
        self.logo_btn.setText("Change…" if has_logo else "Choose Logo…")

    def _set_logo(self, name: str) -> None:
        self.profile.logo = name
        self._show_logo()

    def _choose_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a Logo", str(Path.home()), "Logos (*.png *.jpg *.jpeg *.svg)"
        )
        if not path:
            return
        try:
            name = import_logo(Path(path))
        except (OSError, ValueError) as e:
            log.warning("logo not added: %s", e)
            self.logo_error.setText(str(e) if isinstance(e, ValueError) else "Couldn't read that file.")
            self.logo_error.show()
            return
        log.info("logo added")
        self.logo_error.hide()
        self._set_logo(name)

    # ------------------------------------------------------------------ buttons
    def _save(self) -> None:
        self.profile = self._draft()
        self.accept()

    def _delete(self) -> None:
        from cuanto.ui.dialogs.common import confirm

        if confirm(
            self,
            "Delete This Profile?",
            f"{self.profile.name} comes off Cuánto. Budgets that used it print with the profile in use.",
            "Delete Profile",
        ):
            self.deleted = True
            self.accept()
