"""Small reusable widgets."""

from __future__ import annotations

import math

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor, QCursor, QFontMetrics, QFontMetricsF, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyledItemDelegate,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from cuanto.ui.components import glass
from cuanto.ui.style import theme, tokens

MAX_QTY = 9999  # a whole number of things: more is a typo


def section_label(text: str) -> QLabel:
    """The small Title Case label above a group of controls."""
    lbl = QLabel(text)
    lbl.setObjectName("SectionLabel")
    return lbl


def hint(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Hint")
    lbl.setWordWrap(True)
    return lbl


def vbox(
    widget: QWidget | None = None,
    margins: int | tuple[int, int, int, int] = 0,
    spacing: int = tokens.SPACE_2,
) -> QVBoxLayout:
    """A vertical layout using the spacing tokens (never type raw numbers in layouts)."""
    lay = QVBoxLayout(widget) if widget is not None else QVBoxLayout()
    m = (margins,) * 4 if isinstance(margins, int) else margins
    lay.setContentsMargins(*m)
    lay.setSpacing(spacing)
    return lay


def hbox(
    widget: QWidget | None = None,
    margins: int | tuple[int, int, int, int] = 0,
    spacing: int = tokens.SPACE_2,
) -> QHBoxLayout:
    """A horizontal layout using the spacing tokens."""
    lay = QHBoxLayout(widget) if widget is not None else QHBoxLayout()
    m = (margins,) * 4 if isinstance(margins, int) else margins
    lay.setContentsMargins(*m)
    lay.setSpacing(spacing)
    return lay


class Section(QWidget):
    """A labelled group: a small Title Case label, then its controls SPACE_1 below it.

    Put Sections in a layout with spacing SPACE_3 and every panel lines up the same way.
    Hiding a Section hides its label and controls together (and the gap collapses).
    """

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.lay = vbox(self, 0, tokens.SPACE_1)
        self.label = section_label(title)
        self.label.setVisible(bool(title))
        self.lay.addWidget(self.label)

    def add(self, item: QWidget | QHBoxLayout | QVBoxLayout) -> None:
        if isinstance(item, QWidget):
            self.lay.addWidget(item)
        else:
            self.lay.addLayout(item)

    def set_title(self, title: str) -> None:
        self.label.setText(title)
        self.label.setVisible(bool(title))


class ElidedLabel(QLabel):
    """A one-line label that cuts long text short with "…" instead of widening its panel."""

    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self._full = ""
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.set_full_text(text)

    def set_full_text(self, text: str) -> None:
        self._full = text
        self.setToolTip("")
        self._elide()
        self.updateGeometry()  # its size hint follows its words

    def full_text(self) -> str:
        return self._full

    def _elide(self) -> None:
        shown = self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideRight, max(1, self.width()))
        self.setText(shown)
        self.setToolTip(theme.plain_tip(self._full) if shown != self._full else "")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._elide()

    def sizeHint(self) -> QSize:  # as wide as the whole text, when there's room
        return QSize(self.fontMetrics().horizontalAdvance(self._full) + 2, super().sizeHint().height())

    def minimumSizeHint(self) -> QSize:  # …but it gives way to everything else first
        return QSize(0, super().minimumSizeHint().height())


class _FoldHeader(QPushButton):
    """The Disclosure's header: its text is cut short with "…" rather than widening the panel."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._full = ""
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

    def set_full_text(self, text: str) -> None:
        self._full = text
        self._elide()

    def _elide(self) -> None:
        room = self.width() - self.iconSize().width() - tokens.SPACE_3
        self.setText(self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideRight, max(1, room)))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._elide()


class Card(QFrame):
    """A titled group in an inspector panel: a soft tinted card (the look every panel's groups share).
    Every group in a panel (a line's amount, its fringes, an account's details) is a Card."""

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.outer = vbox(self, tokens.SPACE_3, tokens.SPACE_2)
        self.head = hbox(spacing=tokens.SPACE_2)
        self.title = QLabel(title)
        self.title.setObjectName("CardTitle")
        self.title.setVisible(bool(title))
        self.head.addWidget(self.title, 1)
        self.outer.addLayout(self.head)
        self.lay = vbox(spacing=tokens.SPACE_2)
        self.outer.addLayout(self.lay)

    def add(self, item: QWidget | QHBoxLayout | QVBoxLayout) -> None:
        if isinstance(item, QWidget):
            self.lay.addWidget(item)
        else:
            self.lay.addLayout(item)


class Disclosure(QFrame):
    """A fold-away group: a header row that opens and closes the controls under it.

    Folded, the header says what's inside ("Line Items · 3 items · $2,700.00"), so nothing that changes
    the page is ever hidden silently. (`first` is kept for callers; every group is now its own card.)"""

    toggled = Signal(bool)

    def __init__(self, title: str, is_open: bool = False, first: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self._title = title
        self._summary = ""
        self.setObjectName("Card")  # looks like every other group in a panel
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        outer = vbox(self, tokens.SPACE_3, tokens.SPACE_2)
        self.header = _FoldHeader()
        self.header.setObjectName("Disclosure")
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.clicked.connect(lambda: self.set_open(not self.body.isVisibleTo(self), emit=True))
        outer.addWidget(self.header)
        self.body = QWidget()
        self.lay = vbox(self.body, 0, tokens.SPACE_2)
        outer.addWidget(self.body)
        self.set_open(is_open)

    def add(self, item: QWidget | QHBoxLayout | QVBoxLayout) -> None:
        if isinstance(item, QWidget):
            self.lay.addWidget(item)
        else:
            self.lay.addLayout(item)

    def is_open(self) -> bool:
        return self.body.isVisibleTo(self)

    def set_open(self, on: bool, emit: bool = False) -> None:
        self.body.setVisible(on)
        self.header.setIcon(theme.icon("chevron" if on else "chevron-right", theme.MUTED))
        self.header.setToolTip("Hide" if on else "Show")
        self._show_title()
        if emit:
            self.toggled.emit(on)

    def set_summary(self, text: str) -> None:
        self._summary = text.replace("&", "&&")  # a lone & would underline the next letter instead
        self._show_title()

    def _show_title(self) -> None:
        folded = not self.body.isVisibleTo(self)
        self.header.set_full_text(
            f" {self._title}" + (f"  ·  {self._summary}" if folded and self._summary else "")
        )


def repolish(w: QWidget) -> None:
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


class AccentPicker(QWidget):
    """A row of color circles (tokens.ACCENTS), the chosen one ringed. Click, or the arrow keys."""

    picked = Signal(str)

    def __init__(self, current: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.keys = list(tokens.ACCENTS)
        self.current = current if current in tokens.ACCENTS else tokens.APP_ACCENT
        self._hover = ""
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(tokens.CONTROL_H)
        self.setMinimumWidth(self._pitch() * len(self.keys))

    @staticmethod
    def _pitch() -> int:
        return tokens.SWATCH + 2 * tokens.SWATCH_RING * 2 + tokens.SPACE_1

    def _rect(self, i: int) -> QRectF:
        outer = tokens.SWATCH + 4 * tokens.SWATCH_RING
        y = (self.height() - outer) / 2
        return QRectF(i * self._pitch(), y, outer, outer)

    def _key_at(self, pos) -> str:
        for i, k in enumerate(self.keys):
            if self._rect(i).contains(pos):
                return k
        return ""

    def set_value(self, key: str) -> None:
        self.current = key if key in tokens.ACCENTS else tokens.APP_ACCENT
        self.update()

    def _pick(self, key: str) -> None:
        if key and key != self.current:
            self.current = key
            self.update()
            self.picked.emit(key)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ring = tokens.SWATCH_RING
        for i, k in enumerate(self.keys):
            r = self._rect(i)
            dot = r.adjusted(2 * ring, 2 * ring, -2 * ring, -2 * ring)
            if k == self.current or k == self._hover:
                pen = QPen(theme.qcolor(tokens.TEXT if k == self.current else tokens.BORDER_HOVER))
                pen.setWidthF(ring)
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(r.adjusted(ring / 2, ring / 2, -ring / 2, -ring / 2))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(theme.qcolor(tokens.accent_of(k)))
            p.drawEllipse(dot)
        if self.hasFocus():
            pen = QPen(theme.qcolor(tokens.ACCENT_EDGE))
            pen.setWidthF(1)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(self._rect(self.keys.index(self.current)))

    def mouseMoveEvent(self, e) -> None:
        k = self._key_at(e.position())
        if k != self._hover:
            self._hover = k
            self.update()
        name = tokens.ACCENTS[k][0] if k else ""
        if k == tokens.APP_ACCENT:
            name += " (Cuánto's own)"
        self.setToolTip(name)

    def leaveEvent(self, _e) -> None:
        self._hover = ""
        self.update()

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._pick(self._key_at(e.position()))

    def keyPressEvent(self, e) -> None:
        step = {Qt.Key.Key_Left: -1, Qt.Key.Key_Right: 1}.get(e.key())
        if step is None:
            super().keyPressEvent(e)
            return
        i = (self.keys.index(self.current) + step) % len(self.keys)
        self._pick(self.keys[i])


class Segmented(QFrame):
    """A row of mutually exclusive buttons."""

    changed = Signal(str)

    def __init__(self, items: list[tuple[str, str]], compact: bool = False, parent: QWidget | None = None):
        """`compact`: each button as wide as its word, instead of sharing the full width."""
        super().__init__(parent)
        self.setObjectName("Seg")
        self.setFixedHeight(tokens.CONTROL_H)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(*(tokens.SEG_INSET,) * 4)
        lay.setSpacing(tokens.SEG_INSET)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[str, QPushButton] = {}
        for key, label in items:
            b = QPushButton(label)
            b.setObjectName("SegBtn")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setSizePolicy(
                QSizePolicy.Policy.Preferred if compact else QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            b.clicked.connect(lambda _=False, k=key: self.changed.emit(k))
            self.group.addButton(b)
            lay.addWidget(b)
            self.buttons[key] = b

    def set_value(self, key: str) -> None:
        if key in self.buttons:
            self.buttons[key].setChecked(True)

    def value(self) -> str:
        for k, b in self.buttons.items():
            if b.isChecked():
                return k
        return ""


class Toast(QWidget):
    """A short message floating over the bottom of the page: it rises and fades in, waits, and fades away.
    Its tone's icon says what kind it is: "done" (a green check), "problem" (an amber alert, on an amber-tinted
    toast) or news (an info sign). It never takes a click (what's under it still works); resting the pointer on
    it keeps it up while you read. Painted, so its words are always plain text.
    `anchor`: where it centres itself, in the parent's coordinates (the page, between the side panels)."""

    TONES = {
        "done": ("check", "TOAST_DONE"),
        "problem": ("alert", "TOAST_PROBLEM"),
        "": ("info", "TOAST_TEXT"),
    }

    def __init__(self, parent: QWidget, anchor=None):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.anchor = anchor or parent.rect
        self.text, self.tone = "", ""
        self._ms = tokens.TOAST_MS
        self._shown = 0.0  # 0 gone … 1 all the way in
        self._leaving = False
        self._pill = QRectF()
        self._anim = QVariantAnimation(self)
        self._anim.valueChanged.connect(self._step)
        self._anim.finished.connect(self._settled)
        self._t = QTimer(self)
        self._t.setSingleShot(True)
        self._t.timeout.connect(self._time_up)
        self.hide()

    def show_message(self, text: str, tone: str = "", ms: int = tokens.TOAST_MS) -> None:
        self.text, self.tone = text, tone if tone in self.TONES else ""
        self._ms = max(ms, len(text) * tokens.TOAST_MS_PER_CHAR)
        self.place()
        self.raise_()
        # already up (progress, say): just new words, no new entrance
        if not self.isVisible() or self._leaving:
            self._leaving = False
            self._go(1.0, tokens.TOAST_IN_MS, QEasingCurve.Type.OutCubic)
        self.show()
        self.update()
        self._t.start(self._ms)

    def dismiss(self) -> None:
        if self.isVisible() and not self._leaving:
            self._t.stop()
            self._leaving = True
            self._go(0.0, tokens.TOAST_OUT_MS, QEasingCurve.Type.InCubic)

    def place(self) -> None:
        """Size it to its words and centre it over the bottom of the page."""
        area = self.anchor()
        m = glass.shadow_margin()
        icon_w = tokens.ICON + tokens.SPACE_2
        pad_x, pad_y = tokens.SPACE_4, tokens.SPACE_3
        widest = max(
            tokens.ICON, min(tokens.TOAST_MAX_W, area.width() - 2 * tokens.SPACE_5) - 2 * pad_x - icon_w
        )
        flags = int(Qt.TextFlag.TextWordWrap)
        box = QFontMetrics(self._font()).boundingRect(QRect(0, 0, widest, 10_000), flags, self.text)
        w = icon_w + min(widest, box.width()) + 2 * pad_x
        h = max(tokens.ICON, box.height()) + 2 * pad_y
        self._pill = QRectF(m, m, w, h)
        self.setGeometry(
            round(area.center().x() - w / 2 - m),
            area.bottom() - tokens.TOAST_LIFT - h - m,
            w + 2 * m,
            h + 2 * m,
        )

    @staticmethod
    def _font():
        return theme.font(tokens.TEXT_MD, tokens.WEIGHT_MEDIUM)

    def _go(self, to: float, ms: int, curve) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._shown)
        self._anim.setEndValue(to)
        self._anim.setDuration(ms)
        self._anim.setEasingCurve(curve)
        self._anim.start()

    def _step(self, v) -> None:
        self._shown = float(v)
        self.update()

    def _settled(self) -> None:
        if self._leaving:
            self._leaving = False
            self.hide()

    def _time_up(self) -> None:
        if self._pill.contains(QPointF(self.mapFromGlobal(QCursor.pos()))):
            self._t.start(tokens.TOAST_MS)  # you're reading it
        else:
            self.dismiss()

    def paintEvent(self, _e):
        if self._shown <= 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._shown)
        r = self._pill.translated(0, (1 - self._shown) * tokens.TOAST_RISE)
        glass.paint_shadow(p, r, tokens.RADIUS_LG, tokens.TOAST_SHADOW)
        problem = self.tone == "problem"
        path = QPainterPath()
        path.addRoundedRect(r, tokens.RADIUS_LG, tokens.RADIUS_LG)
        p.fillPath(path, theme.qcolor(tokens.TOAST_PROBLEM_FILL if problem else tokens.TOAST))
        edge = QPainterPath()
        edge.addRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), tokens.RADIUS_LG - 0.5, tokens.RADIUS_LG - 0.5)
        p.setPen(QPen(theme.qcolor(tokens.TOAST_PROBLEM_EDGE if problem else tokens.TOAST_EDGE), 1))
        p.drawPath(edge)
        name, color = self.TONES[self.tone]
        pad_x = tokens.SPACE_4
        icon = theme.icon(name, getattr(tokens, color), tokens.ICON).pixmap(
            QSize(tokens.ICON, tokens.ICON), self.devicePixelRatioF()
        )
        p.drawPixmap(QPointF(r.left() + pad_x, r.center().y() - tokens.ICON / 2), icon)
        text = r.adjusted(pad_x + tokens.ICON + tokens.SPACE_2, 0, -pad_x, 0)
        p.setFont(self._font())
        p.setPen(theme.qcolor(tokens.TOAST_TEXT))
        p.drawText(text, int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignVCenter), self.text)
        p.end()


# ------------------------------------------------------------------ dropdowns
def combo(items: list[tuple[str, str, str]], current: str) -> QComboBox:
    """The standard dropdown. items: (key, label, tooltip); the key is the item's data."""
    c = QComboBox()
    for key, label, tip in items:
        c.addItem(label, key)
        if tip:
            c.setItemData(c.count() - 1, tip, Qt.ItemDataRole.ToolTipRole)
    c.setCurrentIndex(max(0, c.findData(current)))
    c.setCursor(Qt.CursorShape.PointingHandCursor)
    return c


class Embeddable:
    """A dialog that can also sit inside another window (a Settings pane): no title of its own, no Cancel,
    and finishing (Save, Delete, Sign In) tells its host instead of closing. Dialogs name the parts:
    `title_label` and `cancel_btn`."""

    embedded = False

    def embed(self) -> None:
        self.embedded = True
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setObjectName("Embedded")  # no background of its own: the window's shows through
        for name in ("title_label", "cancel_btn"):
            w = getattr(self, name, None)
            if w is not None:
                w.hide()

    def keyPressEvent(self, e) -> None:
        if self.embedded and e.key() == Qt.Key.Key_Escape:
            e.ignore()  # Esc closes the window it sits in, not the pane
            return
        super().keyPressEvent(e)

    def done(self, r: int) -> None:
        if not self.embedded:
            super().done(r)
            return
        self.setResult(r)
        self.finished.emit(r)
        (self.accepted if r else self.rejected).emit()


class SearchField(QLineEdit):
    """The toolbar's search: asks for SEARCH_W, gives way down to SEARCH_MIN on a narrow window."""

    def sizeHint(self) -> QSize:
        return QSize(tokens.SEARCH_W, super().sizeHint().height())


def set_combo(c: QComboBox, key: str) -> None:
    """Select the item with this key without firing change signals."""
    c.blockSignals(True)
    c.setCurrentIndex(max(0, c.findData(key)))
    c.blockSignals(False)


def disable_item(c: QComboBox, key: str, why: str) -> None:
    """Grey out one item and say why in its tooltip."""
    i = c.findData(key)
    item = c.model().item(i) if i >= 0 and hasattr(c.model(), "item") else None
    if item is not None:
        item.setEnabled(False)
        item.setToolTip(why)


def suggestions(c):
    """A type-ahead list (QCompleter) in the shared list look: rounded, rows inset like the sidebar's."""
    pop = c.popup()
    pop.setObjectName("Suggestions")
    pop.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    pop.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
    pop.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    pop.setItemDelegate(ComboItemDelegate(pop))
    return c


class ComboItemDelegate(QStyledItemDelegate):
    """Draws dropdown rows: rounded highlight from the stylesheet, standard row height,
    and a thin line for separators (Qt's default painter ignores the stylesheet on macOS)."""

    ROW_H = tokens.LIST_ROW_H + tokens.LIST_GAP
    SEP_H = tokens.SPACE_2 + 1

    @staticmethod
    def _is_separator(index) -> bool:
        return index.data(Qt.ItemDataRole.AccessibleDescriptionRole) == "separator"

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(self.SEP_H if self._is_separator(index) else max(size.height(), self.ROW_H))
        return size

    def paint(self, painter, option, index):
        if self._is_separator(index):
            y = option.rect.center().y()
            painter.save()
            painter.setPen(QColor(tokens.BORDER_STRONG))
            painter.drawLine(
                option.rect.left() + tokens.SPACE_2,
                y,
                option.rect.right() - tokens.SPACE_2,
                y,
            )
            painter.restore()
            return
        super().paint(painter, option, index)


class FitScroll(QScrollArea):
    """Scroll area whose content always matches the visible width (no clipped edges).

    The scroll bar's space is always reserved (it's invisible while there's nothing to scroll), so
    content never shifts or squeezes when a group opens. Put SCROLL_GUTTER less margin on the
    right of the content so both sides look the same."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        bar = self.verticalScrollBar()
        bar.setEnabled(False)
        bar.rangeChanged.connect(lambda lo, hi: bar.setEnabled(hi > lo))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.widget():
            self.widget().setFixedWidth(self.viewport().width())


class PanelHeader(QFrame):
    """The top of each panel, the same height everywhere so the three panels line up.

    It says what the panel holds ("Line", "Account"), or holds a control instead of a title.
    `.lead` takes widgets on the left, `.actions` on the right."""

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("PanelHeader")
        self.setFixedHeight(tokens.HEADER_H)
        lay = hbox(self, (tokens.SPACE_4, 0, tokens.SPACE_4, 0), tokens.SPACE_2)
        self.title = QLabel(title)
        self.title.setObjectName("PanelTitle")
        self.title.setVisible(bool(title))
        lay.addWidget(self.title)
        self.lead = hbox(spacing=tokens.SPACE_2)
        lay.addLayout(self.lead, 1)
        self.actions = hbox(spacing=tokens.SPACE_2)
        lay.addLayout(self.actions)

    def set_title(self, title: str) -> None:
        self.title.setText(title)
        self.title.setVisible(bool(title))

    def add_close(self, tip: str = "Close") -> QToolButton:
        """The round ✕, at the far right (after the ⋯ and any other buttons)."""
        b = circle_button("x", tip)
        self.layout().addWidget(b)
        return b


class ToggleRow(QAbstractButton):
    """An on/off setting: the label on the left, a switch on the right, the whole row clickable.
    Works like a QCheckBox (setChecked, isChecked, toggled, text)."""

    def __init__(self, text: str, checked: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(tokens.TOGGLE_ROW_H)
        self._hover = False

    def sizeHint(self) -> QSize:
        w = self.fontMetrics().horizontalAdvance(self.text()) + tokens.SPACE_3 + tokens.TOGGLE_W
        return QSize(w, tokens.TOGGLE_ROW_H)

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        on, enabled = self.isChecked(), self.isEnabled()
        r = self.rect()
        # label
        p.setPen(QColor(tokens.TEXT if enabled else tokens.FAINT))
        text_rect = r.adjusted(0, 0, -(tokens.TOGGLE_W + tokens.SPACE_3), 0)
        label = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, text_rect.width())
        p.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            label,
        )
        # switch
        tw, th = tokens.TOGGLE_W, tokens.TOGGLE_H
        track = QRectF(r.right() - tw + 1, r.center().y() - th / 2 + 1, tw - 1, th - 1)
        if on:
            fill = tokens.ACCENT_HOVER if self._hover and enabled else tokens.ACCENT
        else:
            fill = tokens.BORDER_HOVER if self._hover and enabled else tokens.BORDER_STRONG
        if not enabled:
            fill = tokens.ACCENT_OFF if on else tokens.BORDER
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(fill))
        p.drawRoundedRect(track, th / 2, th / 2)
        knob = th - 2 * tokens.TOGGLE_INSET
        x = track.right() - tokens.TOGGLE_INSET - knob if on else track.left() + tokens.TOGGLE_INSET
        p.setBrush(QColor(tokens.ON_ACCENT if on else tokens.TEXT) if enabled else QColor(tokens.FAINT))
        p.drawEllipse(QRectF(x, track.top() + tokens.TOGGLE_INSET, knob, knob))
        p.end()


class TextBox(QPlainTextEdit):
    """A multi-line text field (addresses, details, payment text) that looks like the one-line fields.
    `edited` fires on typing only, never when the window fills it in with set_text()."""

    edited = Signal()

    def __init__(
        self,
        placeholder: str = "",
        height: int = tokens.TEXT_BOX_H,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("Field")
        self.setPlaceholderText(placeholder)
        self.setFixedHeight(height)
        self.setTabChangesFocus(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._quiet = False
        self.textChanged.connect(self._changed)

    def _changed(self) -> None:
        if not self._quiet:
            self.edited.emit()

    def text(self) -> str:
        return self.toPlainText()

    def set_text(self, text: str) -> None:
        if text == self.toPlainText():
            return
        self._quiet = True
        self.setPlainText(text)
        self._quiet = False


class TitleEdit(QPlainTextEdit):
    """A big, editable title that wraps onto a second line instead of being cut off. One line of text (Return
    finishes, pasted line breaks become spaces); it grows to fit. Works like a QLineEdit: text(), setText(),
    textEdited (typing only)."""

    textEdited = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("BigName")
        self.setTabChangesFocus(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._quiet = False
        self.textChanged.connect(self._changed)

    def _changed(self) -> None:
        self._fit()
        if self._quiet:
            return
        t = self.toPlainText()
        if "\n" in t:  # a pasted line break
            pos = self.textCursor().position()
            self.setText(" ".join(t.split()))
            self.setCursorPosition(min(pos, len(self.toPlainText())))
            t = self.toPlainText()
        self.textEdited.emit(t)

    def _fit(self) -> None:
        # every line as tall as it's laid out: the font's rounded line spacing comes up a little short, and a
        # wrapped title then scrolled inside itself (the wheel moved its words instead of the panel)
        doc = self.document()
        one_line = math.ceil(QFontMetricsF(self.font()).lineSpacing())
        h = 0.0
        block = doc.begin()
        while block.isValid():
            layout = block.layout()
            n = layout.lineCount()
            h += sum(layout.lineAt(i).height() for i in range(n)) if n else one_line
            block = block.next()
        m = self.contentsMargins()
        self.setFixedHeight(math.ceil(h + 2 * doc.documentMargin()) + m.top() + m.bottom() + 2)

    def wheelEvent(self, e):
        e.ignore()  # it's always tall enough: the wheel scrolls the panel it's in

    def text(self) -> str:
        return self.toPlainText()

    def setText(self, text: str) -> None:
        self._quiet = True
        self.setPlainText(text)
        self._quiet = False
        self._fit()

    def setCursorPosition(self, n: int) -> None:
        c = self.textCursor()
        c.setPosition(n)
        self.setTextCursor(c)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.clearFocus()
            return
        super().keyPressEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() in (e.Type.FontChange, e.Type.StyleChange):
            self._fit()


# ------------------------------------------------------------------ fields shared by the panels
def date_field():
    """Every date: a calendar popup, shown as "Oct 10, 2026"."""
    from PySide6.QtCore import QLocale
    from PySide6.QtWidgets import QDateEdit

    d = QDateEdit()
    d.setCalendarPopup(True)
    d.setDisplayFormat("ddd, MMM d, yyyy")
    d.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
    d.setCursor(Qt.CursorShape.PointingHandCursor)
    return d


def to_qdate(iso: str):
    from PySide6.QtCore import QDate

    from cuanto.core import dates

    d = dates.parse(iso) or dates.today()
    return QDate(d.year, d.month, d.day)


def from_qdate(q) -> str:
    return f"{q.year():04d}-{q.month():02d}-{q.day():02d}"


def button_row() -> QHBoxLayout:
    """The row of buttons at the bottom of a dialog: right-aligned (add the main one last), SPACE_4 below
    the content in every dialog (dialogs lay out with SPACE_3 between rows)."""
    row = hbox(spacing=tokens.SPACE_2)
    row.setContentsMargins(0, tokens.SPACE_4 - tokens.SPACE_3, 0, 0)
    row.addStretch(1)
    return row


class IconLabel(QLabel):
    """A small icon that isn't a button. `tone` names a theme color ("MUTED", "ACCENT", "BAD"…); it redraws
    itself when the look changes between light and dark."""

    def __init__(self, name: str = "", tone: str = "MUTED", size: int = tokens.ICON_SM, parent=None):
        super().__init__(parent)
        self._name, self._tone, self._size = name, tone, size
        self.setFixedSize(size, size)
        self._draw()

    def set_icon(self, name: str) -> None:
        if name != self._name:
            self._name = name
            self._draw()

    def _draw(self) -> None:
        if self._name:
            self.setPixmap(theme.pixmap(self._name, self._size, getattr(theme, self._tone)))
        else:
            self.clear()

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() == e.Type.StyleChange:  # the app's stylesheet changed: light or dark
            self._draw()


def circle_button(name: str, tip: str, color: str = "") -> QToolButton:
    """The standard icon button: a round, raised button the height of every control (toolbars, panel
    headers, ‹ › arrows). Always has a tooltip."""
    b = QToolButton()
    b.setObjectName("Circle")
    b.setIcon(theme.icon(name, color or theme.MUTED))
    b.setToolTip(tip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def icon_button(name: str, tip: str, color: str = "", size: int = tokens.ICON_SM):
    """A small icon button inside a row or a card (a line's ⋯): round, no frame until you point at it.
    Always has a tooltip. Without a `color` it's the muted grey of the look in use
    (read now, not when this file loaded, so light mode gets light mode's grey)."""

    b = QToolButton()
    b.setObjectName("IconBtn")
    b.setIcon(theme.icon(name, color or theme.MUTED, size))
    b.setToolTip(tip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def picker(placeholder: str = "") -> QComboBox:
    """A dropdown of your own things (profiles, rates) that never widens the panel for a long name."""
    c = QComboBox()
    c.setCursor(Qt.CursorShape.PointingHandCursor)
    c.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    c.setMinimumContentsLength(1)
    c.setPlaceholderText(placeholder)
    return c


class QtyField(QLineEdit):
    """A whole number of pieces, typed. Works like a spin box (value, setValue, valueChanged), and the
    arrow keys count up and down."""

    valueChanged = Signal(int)

    def __init__(self, value: int = 1, top: int = MAX_QTY, parent: QWidget | None = None):
        super().__init__(parent)
        from PySide6.QtGui import QIntValidator

        self._top = top
        self._value = max(1, value)
        self.setValidator(QIntValidator(1, top, self))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedWidth(tokens.QTY_FIELD_W)
        self.setText(str(self._value))
        self.textEdited.connect(self._typed)
        self.editingFinished.connect(lambda: self.setText(str(self._value)))

    def value(self) -> int:
        return self._value

    def setValue(self, v: int) -> None:
        v = min(self._top, max(1, int(v)))
        self.setText(str(v))
        if v != self._value:
            self._value = v
            self.valueChanged.emit(v)

    def _typed(self, text: str) -> None:
        if text.isdigit() and int(text) >= 1 and int(text) != self._value:
            self._value = min(self._top, int(text))
            self.valueChanged.emit(self._value)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Up:
            self.setValue(self._value + 1)
        elif e.key() == Qt.Key.Key_Down:
            self.setValue(self._value - 1)
        else:
            super().keyPressEvent(e)


def qty_field(value: int = 1, top: int = MAX_QTY) -> QtyField:
    return QtyField(value, top)


def chip(text: str = "", tone: str = "") -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Chip")
    lbl.setProperty("tone", tone)
    return lbl


def set_tone(lbl: QLabel, tone: str, text: str) -> None:
    if lbl.property("tone") != tone:
        lbl.setProperty("tone", tone)
        repolish(lbl)
    lbl.setText(text)
    lbl.setVisible(bool(text))


class MoneyField(QLineEdit):
    """A money amount: reads "$5,998.00" until you click in, then it's the plain number to type over.
    `value()` is what you typed ("5998"); textEdited still fires with the typed text."""

    def __init__(self, currency: str = "$", parent: QWidget | None = None):
        super().__init__(parent)
        self.currency = currency
        self._raw = ""

    def value(self) -> str:
        return self.text() if self.hasFocus() else self._raw

    def set_value(self, raw: str) -> None:
        self._raw = (raw or "").strip()
        self._show()

    def _show(self) -> None:
        from cuanto.core import money

        if self.hasFocus() or not self._raw:
            self.setText(self._raw)
            return
        n = money.parse(self._raw)
        self.setText(money.fmt(n, self.currency) if n or self._raw.strip("0.") == "" else self._raw)

    def focusInEvent(self, e):
        self.setText(self._raw)
        super().focusInEvent(e)
        QTimer.singleShot(0, self.selectAll)

    def focusOutEvent(self, e):
        self._raw = self.text().strip().replace(self.currency, "").replace(",", "")
        super().focusOutEvent(e)
        self._show()


def add_chip(text: str, icon: str = "plus") -> QPushButton:
    """A tinted capsule with a small icon (+ Notes, + Line): the app's "add something" button."""
    b = QPushButton(text)
    b.setObjectName("AddChip")
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setIcon(theme.icon(icon, theme.ACCENT, tokens.ICON_SM))
    return b


class FlowLayout(QLayout):
    """Lays widgets out left to right and wraps to the next line when the row is full (chips)."""

    def __init__(self, parent: QWidget | None = None, spacing: int = tokens.SPACE_2):
        super().__init__(parent)
        self._items: list = []
        self._space = spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._lay(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect) -> None:
        super().setGeometry(rect)
        self._lay(rect, apply=True)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for it in self._items:
            size = size.expandedTo(it.minimumSize())
        return size

    def _lay(self, rect, apply: bool) -> int:
        x, y, line = rect.x(), rect.y(), 0
        for it in self._items:
            if it.widget() is not None and not it.widget().isVisibleTo(it.widget().parentWidget()):
                continue
            hint = it.sizeHint()
            if x + hint.width() > rect.right() + 1 and line > 0:
                x, y, line = rect.x(), y + line + self._space, 0
            if apply:
                it.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self._space
            line = max(line, hint.height())
        return y + line - rect.y()
