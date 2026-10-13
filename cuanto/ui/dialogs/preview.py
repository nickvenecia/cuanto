"""The page window: a budget's top sheet and detail, exactly as they print, and the ways to send them out.

The pages are drawn by doc/render.py, the same steps the PDF uses. The moon turns on the Dark Page (the
same page in light-on-dark colors; PDFs and prints stay white). The bottom bar holds Save PDF…, Print… and ⋯.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QToolButton,
    QWidget,
)

from cuanto.doc import export
from cuanto.doc.render import Page
from cuanto.ui.components.widgets import PanelHeader, Segmented, hbox, vbox
from cuanto.ui.style import theme, tokens


class PageView(QWidget):
    """Draws the pages one under another, as wide as the panel allows."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.pages: list[Page] = []
        self._images: list[QImage] = []
        self._scale = 1.0
        self.message = ""

    def set_pages(self, pages: list[Page]) -> None:
        self.pages = pages
        self._render()

    def _fit(self) -> float:
        """Pixels per point so the page fills the panel's width (with a gap each side)."""
        if not self.pages:
            return 1.0
        avail = self.width() - 2 * tokens.PAGE_GAP
        return max(0.35, min(1.8, avail / self.pages[0].size[0]))

    def _render(self) -> None:
        self._scale = self._fit()
        dpr = self.devicePixelRatioF() or 1.0
        self._images = []
        for p in self.pages:
            img = export.image(p, self._scale * dpr)
            img.setDevicePixelRatio(dpr)
            self._images.append(img)
        h = tokens.PAGE_GAP + sum(p.size[1] * self._scale + tokens.PAGE_GAP for p in self.pages)
        self.setMinimumHeight(int(h))
        self.update()

    def refit(self) -> None:
        if self.pages and abs(self._fit() - self._scale) > 0.01:
            self._render()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.pages:
            if self.message:
                p.setPen(QColor(tokens.FAINT))
                p.drawText(self.rect(), int(Qt.AlignmentFlag.AlignCenter), self.message)
            return
        y = float(tokens.PAGE_GAP)
        for page, img in zip(self.pages, self._images, strict=False):
            w, h = page.size[0] * self._scale, page.size[1] * self._scale
            x = (self.width() - w) / 2
            # a soft shadow under the paper
            for i in range(tokens.PAGE_SHADOW // 3, 0, -1):
                c = theme.qcolor(tokens.SHADOW)
                c.setAlpha(max(4, 26 - i * 3))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(c)
                p.drawRoundedRect(QRectF(x - i, y - i + tokens.GLASS_SHADOW_DROP, w + 2 * i, h + 2 * i), i, i)
            p.drawImage(QRectF(x, y, w, h), img)
            y += h + tokens.PAGE_GAP


class PreviewPanel(QFrame):
    save_pdf = Signal()
    print_wanted = Signal()
    save_png = Signal()
    copy_text = Signal()
    open_folder = Signal()
    show_file = Signal()
    dark_changed = Signal(bool)
    doc_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.dark = False
        outer = vbox(self, 0, 0)
        self.header = PanelHeader("Preview")
        self.seg: Segmented | None = None
        self._docs: list[tuple[str, str]] = []
        self.btn_dark = QToolButton()
        self.btn_dark.setObjectName("Circle")
        self.btn_dark.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dark.clicked.connect(lambda: self._toggle_dark())
        self.header.actions.addWidget(self.btn_dark)
        outer.addWidget(self.header)
        self.area = QScrollArea()
        self.area.setObjectName("PreviewArea")
        self.area.setWidgetResizable(True)
        self.area.setFrameShape(QFrame.Shape.NoFrame)
        self.area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view = PageView()
        self.area.setWidget(self.view)
        self.area.viewport().setAutoFillBackground(True)
        self.area.viewport().setObjectName("PreviewArea")
        outer.addWidget(self.area, 1)

        bottom = QFrame()
        bottom.setObjectName("PanelBottom")
        row = hbox(bottom, tokens.SPACE_4, tokens.SPACE_2)
        self.status = QLabel()
        self.status.setObjectName("Muted")
        row.addWidget(self.status, 1)
        self.btn_show = QPushButton("Show File")
        self.btn_show.clicked.connect(self.show_file.emit)
        row.addWidget(self.btn_show)
        self.btn_more = QToolButton()
        self.btn_more.setObjectName("Circle")
        self.btn_more.setIcon(theme.icon("more", theme.MUTED))
        self.btn_more.setToolTip("More ways to send it")
        self.btn_more.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        m = QMenu(self.btn_more)
        m.addAction(theme.menu_icon("image"), "Save as PNG…", self.save_png.emit)
        m.addAction(theme.menu_icon("copy"), "Copy Top Sheet as Text", self.copy_text.emit)
        m.addSeparator()
        m.addAction(theme.menu_icon("folder"), "Open Exports Folder", self.open_folder.emit)
        self.btn_more.setMenu(m)
        row.addWidget(self.btn_more)
        self.btn_print = QPushButton("Print…")
        self.btn_print.setIcon(theme.icon("printer", theme.TEXT, tokens.ICON_SM))
        self.btn_print.clicked.connect(self.print_wanted.emit)
        row.addWidget(self.btn_print)
        self.btn_pdf = QPushButton("Save PDF…")
        self.btn_pdf.setObjectName("Primary")
        self.btn_pdf.clicked.connect(self.save_pdf.emit)
        row.addWidget(self.btn_pdf)
        outer.addWidget(bottom)
        self.saved_hint(None)
        self.set_dark(False)

        self._refit = QTimer(self)
        self._refit.setSingleShot(True)
        self._refit.setInterval(tokens.PREVIEW_REFIT_MS)
        self._refit.timeout.connect(self.view.refit)

    def set_dark(self, on: bool) -> None:
        self.dark = on
        self.btn_dark.setIcon(theme.icon("sun" if on else "moon", theme.MUTED))
        self.btn_dark.setToolTip(
            "Show the page in white, exactly as it prints"
            if on
            else "Dark Page: easier on the eyes while you work. PDFs and prints stay white."
        )

    def _toggle_dark(self) -> None:
        self.set_dark(not self.dark)
        self.dark_changed.emit(self.dark)

    def set_pages(self, pages: list[Page]) -> None:
        self.view.message = ""
        self.view.set_pages(pages)
        for b in (self.btn_pdf, self.btn_print, self.btn_more):
            b.setEnabled(bool(pages))

    def clear(self, message: str) -> None:
        self.view.message = message
        self.view.set_pages([])
        for b in (self.btn_pdf, self.btn_print, self.btn_more):
            b.setEnabled(False)
        self.saved_hint(None)

    def saved_hint(self, name: str | None) -> None:
        self.status.setText(f"Saved {name}" if name else "")
        self.btn_show.setVisible(bool(name))

    def set_docs(self, items: list[tuple[str, str]], current: str) -> None:
        """The views it offers (Top Sheet, Detail, Both): a switch in the header."""
        self._docs = items
        self.seg = Segmented(items, compact=True)
        self.seg.set_value(current)
        self.seg.changed.connect(self.doc_changed.emit)
        self.header.lead.addWidget(self.seg, 0, Qt.AlignmentFlag.AlignLeft)
        self.header.set_title("")

    def current_doc(self) -> str:
        if self.seg is not None:
            return self.seg.value() or (self._docs[0][0] if self._docs else "")
        return self._docs[0][0] if self._docs else ""

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._refit.start()

    def showEvent(self, e):
        super().showEvent(e)
        self._refit.start()


class PageDialog(QDialog):
    """The PreviewPanel in its own big window, opened from a budget (never in the way of editing)."""

    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(*tokens.PAGE_DIALOG_SIZE)
        if parent is not None:
            g = parent.geometry()
            inset = tokens.PAGE_DIALOG_INSET
            self.resize(
                min(tokens.PAGE_DIALOG_SIZE[0], g.width() - inset),
                max(tokens.PAGE_DIALOG_MIN_H, g.height() - inset),
            )
        lay = vbox(self, 0, 0)
        self.panel = PreviewPanel()
        lay.addWidget(self.panel)
