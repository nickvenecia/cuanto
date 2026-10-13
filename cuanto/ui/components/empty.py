"""What shows where a table would be when there's nothing in it yet: the ways to start, as tiles. A budget
starts from a template or an import, and a CSV or JSON file dropped anywhere on the page comes in too; the other
places start one way, with the place's own icon."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QLabel, QWidget

from cuanto.ui.components.widgets import IconLabel, hbox, repolish, vbox
from cuanto.ui.style import theme, tokens

SHEETS = (".csv", ".json")  # what Import reads: budget lines as CSV, the exchange format as JSON


def sheet_in(mime) -> Path | None:
    """The file being dragged in, if Cuánto can import it (the first file only)."""
    urls = mime.urls() if mime.hasUrls() else []
    if not urls or not urls[0].isLocalFile():
        return None
    path = Path(urls[0].toLocalFile())
    return path if path.suffix.lower() in SHEETS else None


class StartTile(QFrame):
    """One way to start: an icon, what it is, a few words. A click, Space or Return picks it."""

    clicked = Signal()

    def __init__(self, icon: str, title: str, detail: str, tip: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StartTile")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(tokens.START_TILE_W)
        if tip:
            self.setToolTip(theme.plain_tip(tip))
        lay = vbox(self, (tokens.SPACE_4, tokens.SPACE_5, tokens.SPACE_4, tokens.SPACE_5), tokens.SPACE_1)
        badge = QFrame()  # the icon, in a circle of the accent's tint
        badge.setObjectName("StartBadge")
        badge.setFixedSize(tokens.START_BADGE, tokens.START_BADGE)
        bl = vbox(badge)
        bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bl.addWidget(IconLabel(icon, "ACCENT", tokens.ICON_LG))
        lay.addWidget(badge, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addSpacing(tokens.SPACE_2)
        name = QLabel(title)
        name.setObjectName("StartTitle")
        sub = QLabel(detail)
        sub.setObjectName("StartDetail")
        for w in (name, sub):
            w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            w.setWordWrap(True)  # the tile is a fixed width: a line too long for it goes on to the next
            lay.addWidget(w)

    def set_hot(self, on: bool) -> None:
        """Lit while a file Cuánto can import is dragged over the page."""
        if self.property("hot") is not on:
            self.setProperty("hot", on)
            repolish(self)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            e.accept()  # the release comes back here
        else:
            super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(e)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.clicked.emit()
            return
        super().keyPressEvent(e)


class EmptyPage(QWidget):
    """The empty page. `show_for()` sets its tiles; `dropped` is a file let go on it (only while the
    page takes them)."""

    dropped = Signal(Path)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._key: tuple = ()
        self._slots: list[Callable] = []
        self._sheet_tile: int | None = None  # the tile that lights up while a file is dragged in
        self.tiles: list[StartTile] = []
        lay = vbox(self, tokens.SPACE_5, 0)
        lay.addStretch(2)
        self.tile_row = hbox(spacing=tokens.SPACE_3)
        lay.addLayout(self.tile_row)
        lay.addStretch(3)

    def show_for(
        self, tiles: tuple[tuple[str, str, str, str, Callable], ...], sheet_tile: int | None = None
    ) -> None:
        """The tiles: (icon, title, detail, tooltip, what it does). `sheet_tile`: a file dropped here is
        imported, and that tile lights up while it's dragged in."""
        self._sheet_tile = sheet_tile
        self._slots = [t[4] for t in tiles]
        key = tuple(t[:4] for t in tiles)
        if key == self._key:
            return
        self._key = key
        while self.tile_row.count():
            w = self.tile_row.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        self.tiles = []
        self.tile_row.addStretch(1)
        for n, (name, label, detail, tip, _slot) in enumerate(tiles):
            tile = StartTile(name, label, detail, tip)
            tile.clicked.connect(lambda n=n: self._slots[n]())
            self.tile_row.addWidget(tile)
            self.tiles.append(tile)
        self.tile_row.addStretch(1)

    # ---- a file dragged in from the Finder or Explorer lights its tile and is imported
    def _light(self, on: bool) -> None:
        if self._sheet_tile is not None and self._sheet_tile < len(self.tiles):
            self.tiles[self._sheet_tile].set_hot(on)

    def dragEnterEvent(self, e):
        if self._sheet_tile is not None and sheet_in(e.mimeData()) is not None:
            e.acceptProposedAction()
            self._light(True)
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        self._light(False)

    def dropEvent(self, e):
        self._light(False)
        path = sheet_in(e.mimeData()) if self._sheet_tile is not None else None
        if path is None:
            e.ignore()
            return
        e.acceptProposedAction()
        QTimer.singleShot(0, lambda: self.dropped.emit(path))  # after the drag ends: the Import window waits
