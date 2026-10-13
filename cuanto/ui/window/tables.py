"""The big tables in the middle: your budgets, a budget's top sheet and its detail, its globals and fringes,
and the rate library. Click a row to edit it on the right.

Never a widget per row: one delegate (RowPainter) paints every row, its rounded highlight, the accent bands
that divide a table (a section, a category, a department) and their fold arrows. A band folds what's under it
(remembered). In the detail, a line's Description, Amount, Units, Unit and Rate can be typed over right in
the table (double-click, or Return); what's typed is the same text the line's panel shows (a number or a
formula), and it saves itself.
"""

from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPen, QPixmap, QRegion
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QLineEdit,
    QMenu,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from cuanto.core import calc, dates, formula, money, rates
from cuanto.core.model import (
    KIND_NAMES,
    SECTION_NAMES,
    STAGE_NAMES,
    SYMBOLS,
    UNIT_NAMES,
    UNITS,
    Budget,
    Rate,
)
from cuanto.ui.style import theme, tokens

ID = Qt.ItemDataRole.UserRole
SORT = Qt.ItemDataRole.UserRole + 1
HAY = Qt.ItemDataRole.UserRole + 2
HEAD = Qt.ItemDataRole.UserRole + 3  # a band (divider) row: its place in the table
KIND = Qt.ItemDataRole.UserRole + 4  # what a row is: budget, category, account, line, adjustment…
FOLD = Qt.ItemDataRole.UserRole + 5  # the key its fold is remembered by (bands and accounts)
OPEN = Qt.ItemDataRole.UserRole + 6
DEPTH = Qt.ItemDataRole.UserRole + 7  # how far its name is indented
RAW = Qt.ItemDataRole.UserRole + 8  # a line's cells as typed (formulas), for editing in place
FORMULA = Qt.ItemDataRole.UserRole + 9  # columns whose number comes from a formula (shown in the accent)

RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
CENTER = Qt.AlignmentFlag.AlignCenter
W = tokens.COL_W


def short_money(d: Decimal, budget: Budget | None = None) -> str:
    sym = SYMBOLS.get(budget.currency, "$") if budget is not None else "$"
    return money.fmt(d, sym)


def compact_money(d: Decimal, budget: Budget | None = None) -> str:
    """$412K, $1.6M: a total that fits in the sidebar."""
    sym = SYMBOLS.get(budget.currency, "$") if budget is not None else "$"
    a = abs(d)
    sign = money.MINUS if d < 0 else ""
    if a >= 1_000_000:
        return f"{sign}{sym}{a / 1_000_000:.1f}M".replace(".0M", "M")
    if a >= 1_000:
        return f"{sign}{sym}{round(a / 1_000):,}K"
    return f"{sign}{sym}{int(money.whole(a)):,}" if a else ""


def qty(d: Decimal) -> str:
    return money.fmt_qty(money.cents(d))


class Row(QTreeWidgetItem):
    """Sorts by the hidden sort key of the clicked column (numbers as numbers, words as words)."""

    def __lt__(self, other):
        tree = self.treeWidget()
        col = tree.sortColumn() if tree else 0
        ha, hb = self.data(0, HEAD), other.data(0, HEAD)
        if ha is not None and hb is not None:  # bands keep their order whichever way you sort
            descending = (
                tree is not None and tree.header().sortIndicatorOrder() == Qt.SortOrder.DescendingOrder
            )
            return ha > hb if descending else ha < hb
        a, b = self.data(col, SORT), other.data(col, SORT)
        if a is None or b is None:
            return (self.text(col) or "").casefold() < (other.text(col) or "").casefold()
        if isinstance(a, str) or isinstance(b, str):
            return str(a).casefold() < str(b).casefold()
        return a < b


class RowPainter(QStyledItemDelegate):
    """Every row's highlight drawn once across the whole row as one rounded shape (hover, selected, and the
    bands' accent, a step brighter under the mouse), the fold arrows, and a name indented by its depth. The
    stylesheet leaves cells clear so nothing paints over it. Also the editors for typing over a line."""

    edited = Signal(str, str, str)  # line id, field (description / amount / units / unit / rate), text

    def row_shape(self, painter, option, fill: QColor) -> None:
        view = self.parent()
        left, right = option.rect.left(), option.rect.right()
        if view is not None:
            head = view.header()
            for v in range(head.count()):  # the first column showing starts the row
                c = head.logicalIndex(v)
                if not head.isSectionHidden(c):
                    left = head.sectionViewportPosition(c)
                    break
            right = view.viewport().width()
        i = tokens.ROW_INSET
        r = QRectF(left + 1, option.rect.top() + i, right - left - 2, option.rect.height() - 2 * i)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipRect(option.rect)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        painter.drawRoundedRect(r, tokens.ROW_R, tokens.ROW_R)
        painter.restore()

    def backdrop(self, painter, option, index) -> bool:
        """Paint the row's shape; True for a band."""
        row0 = index.siblingAtColumn(0)
        band = row0.data(HEAD) is not None
        hover = bool(option.state & QStyle.StateFlag.State_MouseOver)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        if band:
            self.row_shape(painter, option, theme.qcolor(tokens.DIVIDER_HOVER if hover else tokens.DIVIDER))
            if selected:
                self.row_shape(painter, option, theme.qcolor(tokens.ACCENT_TINT))
        elif selected:
            self.row_shape(painter, option, theme.qcolor(tokens.CARD_SELECTED))
        elif hover:
            self.row_shape(painter, option, theme.qcolor(tokens.ROW_HOVER))
        return band

    @staticmethod
    def plain(option) -> QStyleOptionViewItem:
        """The cell without hover or selection (its row shape is already drawn)."""
        opt = QStyleOptionViewItem(option)
        opt.state &= ~(
            QStyle.StateFlag.State_MouseOver
            | QStyle.StateFlag.State_Selected
            | QStyle.StateFlag.State_HasFocus
        )
        return opt

    def paint(self, painter, option, index):
        band = self.backdrop(painter, option, index)
        row0 = index.siblingAtColumn(0)
        view = self.parent()
        option = self.plain(option)
        fold_col = getattr(view, "fold_col", -1)
        if index.column() == fold_col:
            if row0.data(FOLD) is not None and view is not None:
                item = view.itemFromIndex(row0)
                if item is not None and item.childCount():
                    color = tokens.DIVIDER_TEXT if band else tokens.FAINT
                    self._chevron(painter, option.rect, bool(row0.data(OPEN)), color)
            return
        depth = row0.data(DEPTH) or 0
        if depth and index.column() == getattr(view, "name_col", -1):
            option = QStyleOptionViewItem(option)
            option.rect = option.rect.adjusted(depth * tokens.ROW_INDENT, 0, 0, 0)
        super().paint(painter, option, index)

    @staticmethod
    def _chevron(painter, rect, open_: bool, color: str) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(theme.qcolor(color), tokens.LINE_STROKE)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        c = QPointF(rect.center())
        r = tokens.CHEVRON / 2
        if open_:
            pts = [
                QPointF(c.x() - r, c.y() - r / 2),
                QPointF(c.x(), c.y() + r / 2),
                QPointF(c.x() + r, c.y() - r / 2),
            ]
        else:
            pts = [
                QPointF(c.x() - r / 2, c.y() - r),
                QPointF(c.x() + r / 2, c.y()),
                QPointF(c.x() - r / 2, c.y() + r),
            ]
        painter.drawPolyline(pts)
        painter.restore()

    # ---- typing over a line, right in the table
    def createEditor(self, parent, option, index):
        view = self.parent()
        key = view.column_key(index.column()) if view is not None else ""
        if key == "unit":
            c = QComboBox(parent)
            for u in UNITS:
                c.addItem(UNIT_NAMES[u], u)
            c.activated.connect(lambda _i, c=c: self.commitData.emit(c))
            return c
        e = QLineEdit(parent)
        e.setFrame(False)
        if key in ("amount", "units", "rate"):
            e.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            names = getattr(view, "global_names", [])
            if names:
                from PySide6.QtWidgets import QCompleter

                from cuanto.ui.components.widgets import suggestions

                comp = QCompleter(names, e)
                comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                e.setCompleter(suggestions(comp))
        return e

    def updateEditorGeometry(self, editor, option, index):
        r = option.rect
        depth = index.siblingAtColumn(0).data(DEPTH) or 0
        view = self.parent()
        if depth and view is not None and index.column() == getattr(view, "name_col", -1):
            r = r.adjusted(depth * tokens.ROW_INDENT, 0, 0, 0)
        editor.setGeometry(r)

    def setEditorData(self, editor, index):
        raw = index.siblingAtColumn(0).data(RAW) or {}
        key = self.parent().column_key(index.column())
        if isinstance(editor, QComboBox):
            editor.setCurrentIndex(max(0, editor.findData(raw.get("unit", "allow"))))
            editor.showPopup()
        else:
            editor.setText(raw.get(key, ""))
            editor.selectAll()

    def setModelData(self, editor, model, index):
        row0 = index.siblingAtColumn(0)
        key = self.parent().column_key(index.column())
        text = editor.currentData() if isinstance(editor, QComboBox) else editor.text()
        raw = row0.data(RAW) or {}
        if text != raw.get(key):
            self.edited.emit(row0.data(ID), key, text)


class Table(QTreeWidget):
    picked = Signal(str, str)  # kind, id
    opened = Signal(str, str)  # double-clicked (a category on the top sheet: go to it)
    menu_wanted = Signal(str, str, QPoint)
    delete_wanted = Signal(list)  # [(kind, id)] on Delete / Backspace
    cleared = Signal()  # a click on empty space: nothing picked
    folds_changed = Signal()

    COLUMNS: list[tuple[str, str, int, object]] = []  # (key, title, width or 0 = stretch, alignment)
    GIVE_WAY: list[str] = []  # on a narrow window these columns step aside first, in this order
    SORTABLE = True
    name_col = 1
    fold_col = -1  # the column fold arrows are drawn in (none: -1)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Table")
        self.setColumnCount(len(self.COLUMNS))
        self.setHeaderLabels([c[1] for c in self.COLUMNS])
        self.setRootIsDecorated(False)
        self.setIndentation(0)
        self.setUniformRowHeights(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSortingEnabled(self.SORTABLE)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setFrameShape(QTreeWidget.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.setExpandsOnDoubleClick(False)
        h = self.header()
        h.setStretchLastSection(False)
        h.setSectionsMovable(False)
        h.setHighlightSections(False)
        h.setSectionsClickable(self.SORTABLE)
        for i, (_k, _t, w, align) in enumerate(self.COLUMNS):
            if w:
                h.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                self.setColumnWidth(i, w)
            else:
                h.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            if align is not None:
                self.headerItem().setTextAlignment(i, align)
        if self.fold_col >= 0:
            h.setSectionResizeMode(self.fold_col, QHeaderView.ResizeMode.Fixed)
        if self.SORTABLE:
            self.sortByColumn(self.name_col, Qt.SortOrder.AscendingOrder)
        self.painter = RowPainter(self)
        self.setItemDelegate(self.painter)
        self.setMouseTracking(True)
        self.currentItemChanged.connect(self._current)
        self.itemDoubleClicked.connect(self._double)
        self.folded: set[str] = set()
        self._quiet = False
        self._squeezed: set[str] = set()

    def column_key(self, col: int) -> str:
        return self.COLUMNS[col][0] if 0 <= col < len(self.COLUMNS) else ""

    def col(self, key: str) -> int:
        return next(i for i, c in enumerate(self.COLUMNS) if c[0] == key)

    # ------------------------------------------------------------------ narrow windows
    def _apply_columns(self) -> None:
        """Make room for the name: the least needed columns step aside on a narrow window."""
        room = self.viewport().width() - tokens.NAME_MIN
        widths = {k: w for k, _t, w, _a in self.COLUMNS}
        needed = sum(w for w in widths.values())
        self._squeezed = set()
        for k in self.GIVE_WAY:
            if needed <= room:
                break
            self._squeezed.add(k)
            needed -= widths[k]
        for i, (k, *_r) in enumerate(self.COLUMNS):
            self.setColumnHidden(i, k in self._squeezed)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if not self.sliding:
            self._apply_columns()

    # ------------------------------------------------------------------ sliding with the inspector
    # Redrawing every row on every step of the inspector's slide is too slow, so while it slides the table
    # is two still pictures (before and after) split after the wide column: the columns to the right
    # move with the edge, the names are covered or uncovered. The real table comes back when it stops.
    sliding = False
    _slide = None

    def _shot(self) -> QPixmap:
        vp = self.viewport()
        dpr = vp.devicePixelRatioF()
        pix = QPixmap(max(1, round(vp.width() * dpr)), max(1, round(vp.height() * dpr)))
        pix.setDevicePixelRatio(dpr)
        pix.fill(Qt.GlobalColor.transparent)
        vp.render(pix, QPoint(), QRegion(), QWidget.RenderFlag.DrawChildren)
        return pix

    def _seam(self) -> int:
        """Where the wide column ends (everything right of it keeps its width)."""
        h = self.header()
        for c in range(h.count()):
            if not h.isSectionHidden(c) and h.sectionResizeMode(c) == QHeaderView.ResizeMode.Stretch:
                return h.sectionViewportPosition(c) + h.sectionSize(c)
        return self.viewport().width()

    def freeze(self, to_end, to_start) -> None:
        """Take the before and after pictures (`to_end` / `to_start` resize the table), then show them."""
        before, seam_before, w_before = self._shot(), self._seam(), self.viewport().width()
        to_end()
        self._apply_columns()
        after, seam_after, w_after = self._shot(), self._seam(), self.viewport().width()
        self.sliding = True  # columns stay as they'll end up
        to_start()
        wide = (before, seam_before) if w_before >= w_after else (after, seam_after)
        self._slide = (wide[0], wide[1], after, seam_after, w_after - seam_after)
        self.viewport().update()

    def thaw(self) -> None:
        self._slide = None
        self.sliding = False
        self._apply_columns()
        self.viewport().update()

    def paintEvent(self, e):
        if self._slide is None:
            return super().paintEvent(e)
        left, left_seam, right, right_seam, right_w = self._slide
        vp = self.viewport()
        h = vp.height()
        cut = vp.width() - right_w
        p = QPainter(vp)
        lw = max(0, min(cut, left_seam))
        if lw:
            d = left.devicePixelRatio()
            p.drawPixmap(QRectF(0, 0, lw, h), left, QRectF(0, 0, lw * d, h * d))
        if right_w > 0:
            d = right.devicePixelRatio()
            p.drawPixmap(QRectF(cut, 0, right_w, h), right, QRectF(right_seam * d, 0, right_w * d, h * d))
        p.end()

    # ------------------------------------------------------------------ picking
    def _current(self, cur, _prev) -> None:
        if cur is not None and not self._quiet and cur.data(0, ID):
            self.picked.emit(cur.data(0, KIND) or "", cur.data(0, ID))

    def _double(self, item, col) -> None:
        if item is None or not item.data(0, ID):
            return
        if item.data(0, KIND) == "line" and self.column_key(col) in getattr(self, "EDITABLE", ()):
            self.editItem(item, col)
            return
        self.opened.emit(item.data(0, KIND) or "", item.data(0, ID))

    def _menu(self, pos) -> None:
        it = self.itemAt(pos)
        if it is not None and it.data(0, ID):
            self.menu_wanted.emit(it.data(0, KIND) or "", it.data(0, ID), self.viewport().mapToGlobal(pos))

    def mousePressEvent(self, e):
        it = self.itemAt(e.position().toPoint())
        if it is None:
            self.cleared.emit()
            return
        if it.data(0, FOLD) is not None and it.childCount() and e.button() == Qt.MouseButton.LeftButton:
            on_arrow = self.fold_col >= 0 and self.columnAt(int(e.position().x())) == self.fold_col
            plain_band = it.data(0, HEAD) is not None and not it.data(0, ID)
            if on_arrow or plain_band:  # its arrow folds it; a band that's only a heading folds anywhere
                self.set_fold(it, not it.isExpanded())
                return
        super().mousePressEvent(e)

    def set_fold(self, it, open_: bool) -> None:
        it.setExpanded(open_)
        it.setData(0, OPEN, open_)
        key = it.data(0, FOLD)
        (self.folded.discard if open_ else self.folded.add)(key)
        self.folds_changed.emit()

    def keyPressEvent(self, e):
        if (
            e.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace)
            and self.state() != QAbstractItemView.State.EditingState
        ):
            got = self.chosen()
            if got:
                self.delete_wanted.emit(got)
            return
        if (
            e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and self.state() != QAbstractItemView.State.EditingState
        ):
            it = self.currentItem()
            if it is not None and it.data(0, KIND) == "line" and getattr(self, "EDITABLE", ()):
                self.editItem(it, self.name_col)
                return
        if e.matches(QKeySequence.StandardKey.SelectAll):
            self.select_showing()
            return
        super().keyPressEvent(e)

    def showing_rows(self):
        """Rows you can see (not hidden, not inside a folded band) that stand for something."""

        def walk(row):
            for i in range(row.childCount()):
                r = row.child(i)
                if r.isHidden():
                    continue
                if r.data(0, ID):
                    yield r
                if r.isExpanded():
                    yield from walk(r)

        yield from walk(self.invisibleRootItem())

    def select_showing(self) -> None:
        """⌘A: every row you can see of the kind that's picked (lines with lines, budgets with budgets)."""
        cur = self.currentItem()
        kind = cur.data(0, KIND) if cur is not None else None
        self.clearSelection()
        for r in self.showing_rows():
            if kind is None or r.data(0, KIND) == kind:
                r.setSelected(True)

    def chosen(self) -> list[tuple[str, str]]:
        """The selected rows you can see, top to bottom (or the current row): (kind, id)."""
        got = [(r.data(0, KIND), r.data(0, ID)) for r in self.showing_rows() if r.isSelected()]
        if not got:
            it = self.currentItem()
            if it is not None and it.data(0, ID):
                got = [(it.data(0, KIND), it.data(0, ID))]
        return got

    def current(self) -> tuple[str, str] | None:
        it = self.currentItem()
        return (it.data(0, KIND), it.data(0, ID)) if it is not None and it.data(0, ID) else None

    def find(self, kind: str, obj_id: str):
        stack = [self.topLevelItem(i) for i in range(self.topLevelItemCount())]
        while stack:
            r = stack.pop()
            if r.data(0, ID) == obj_id and (not kind or r.data(0, KIND) == kind):
                return r
            stack.extend(r.child(i) for i in range(r.childCount()))
        return None

    def select_id(self, kind: str, obj_id: str) -> bool:
        self._quiet = True
        found = self.find(kind, obj_id)
        if found is not None:
            p = found.parent()
            while p is not None:
                if not p.isExpanded():
                    self.set_fold(p, True)
                p = p.parent()
            self.clearSelection()
            self.setCurrentItem(found)
            found.setSelected(True)
            self.scrollToItem(found, QAbstractItemView.ScrollHint.EnsureVisible)
        else:
            self.clearSelection()
        self._quiet = False
        return found is not None

    def filter(self, text: str, keep=None) -> int:
        """Hide rows that don't match every word, and (when given) `keep(kind, id)`; a band or account stays
        when something under it matches. Returns how many rows that stand for something show."""
        words = text.casefold().split()

        def walk(row) -> int:
            kids = 0
            for i in range(row.childCount()):
                kids += walk(row.child(i))
            if row is self.invisibleRootItem():
                return kids
            me = bool(row.data(0, ID)) and all(w in (row.data(0, HAY) or "") for w in words)
            if me and keep is not None:
                me = keep(row.data(0, KIND), row.data(0, ID))
            row.setHidden(not (me or kids))
            if (words or keep is not None) and kids and not row.isExpanded():
                row.setExpanded(True)
                row.setData(0, OPEN, True)
            return kids + (1 if me else 0)

        return walk(self.invisibleRootItem())

    # ------------------------------------------------------------------ filling
    def make(self, kind: str, obj_id: str, cells: list[tuple[str, object]], parent=None) -> Row:
        row = Row(parent or self)
        row.setData(0, ID, obj_id)
        row.setData(0, KIND, kind)
        for i, (text, key) in enumerate(cells):
            row.setText(i, text)
            row.setData(i, SORT, key)
            align = self.COLUMNS[i][3]
            if align is not None:
                row.setTextAlignment(i, align)
        row.setSizeHint(0, QSize(0, tokens.TABLE_ROW_H))
        return row

    def band(self, n: int, fold_key: str, cells: dict[str, str], kind: str = "", obj_id: str = "") -> Row:
        """An accent band dividing the table (a section, a category, a department). Folds what's under it."""
        d = Row(self)
        d.setData(0, HEAD, n)
        d.setData(0, FOLD, fold_key)
        if obj_id:
            d.setData(0, ID, obj_id)
            d.setData(0, KIND, kind)
        f = theme.font(tokens.TEXT_MD, tokens.WEIGHT_SEMIBOLD)
        big = theme.font(tokens.TEXT_LG, tokens.WEIGHT_SEMIBOLD)
        for c, (key, _t, _w, align) in enumerate(self.COLUMNS):
            d.setText(c, cells.get(key, ""))
            d.setFont(c, big if c == self.name_col else f)
            d.setForeground(c, theme.qcolor(tokens.DIVIDER_TEXT))
            if align is not None:
                d.setTextAlignment(c, align)
        d.setSizeHint(0, QSize(0, tokens.TABLE_ROW_H))
        return d

    def settle_folds(self) -> None:
        """Bands and accounts open or folded as you left them."""
        stack = [self.topLevelItem(i) for i in range(self.topLevelItemCount())]
        while stack:
            r = stack.pop()
            key = r.data(0, FOLD)
            if key is not None:
                r.setExpanded(key not in self.folded)
                r.setData(0, OPEN, r.isExpanded())
            stack.extend(r.child(i) for i in range(r.childCount()))

    def _fill_start(self) -> tuple:
        keep = self.current()
        col = self.sortColumn()
        order = self.header().sortIndicatorOrder()
        top = self.verticalScrollBar().value()
        self._quiet = True
        self.setSortingEnabled(False)
        self.clear()
        return keep, col, order, top

    def _fill_end(self, state: tuple) -> None:
        keep, col, order, top = state
        if self.SORTABLE:
            self.setSortingEnabled(True)
            self.sortItems(max(0, col), order)
        self.settle_folds()
        self._apply_columns()
        self._quiet = False
        if keep is not None:
            self.select_id(*keep)
        self.verticalScrollBar().setValue(top)


# ---------------------------------------------------------------------------- your budgets
class BudgetsTable(Table):
    COLUMNS = [
        ("fold", "", 0, None),
        ("name", "Name", 0, None),
        ("kind", "Type", W["kind"], None),
        ("stage", "Stage", W["stage"], None),
        ("updated", "Updated", W["updated"], None),
        ("total", "Total", W["total"], RIGHT),
    ]
    GIVE_WAY = ["updated", "stage", "kind"]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setColumnHidden(0, True)
        self.setColumnWidth(0, 0)

    def _apply_columns(self) -> None:
        super()._apply_columns()
        self.setColumnHidden(0, True)

    def fill(self, budgets: list[Budget], totals: dict[str, calc.Totals]) -> None:
        state = self._fill_start()
        for b in budgets:
            t = totals[b.id]
            when = dates.parse(b.updated[:10]) if b.updated else None
            row = self.make(
                "budget",
                b.id,
                [
                    ("", ""),
                    (b.name or "Untitled Budget", (b.name or "~").casefold()),
                    (KIND_NAMES.get(b.kind, ""), KIND_NAMES.get(b.kind, "")),
                    (STAGE_NAMES.get(b.stage, ""), b.stage),
                    (dates.fmt(when) if when else "", b.updated),
                    (short_money(t.grand, b), float(t.grand)),
                ],
            )
            for c in (2, 4):
                row.setForeground(c, theme.qcolor(tokens.MUTED))
            row.setData(
                0,
                HAY,
                " ".join((b.name, b.info.client, b.info.company, KIND_NAMES.get(b.kind, ""))).casefold(),
            )
        self._fill_end(state)


# ---------------------------------------------------------------------------- the top sheet
class TopSheetTable(Table):
    SORTABLE = False
    COLUMNS = [
        ("fold", "", tokens.FOLD_W, None),
        ("code", "Acct #", W["code"], None),
        ("name", "Category", 0, None),
        ("lines", "Lines", W["lines"], RIGHT),
        ("fringes", "Fringes", W["money"], RIGHT),
        ("total", "Total", W["total"], RIGHT),
    ]
    GIVE_WAY = ["lines", "fringes", "code"]
    name_col = 2
    fold_col = 0

    def fill(self, b: Budget, t: calc.Totals) -> None:
        state = self._fill_start()
        n = 0
        for s, label in SECTION_NAMES.items():
            cats = [c for c in b.categories if c.section == s]
            if not cats:  # an empty section doesn't show
                continue
            sec = t.sections[s]
            d = self.band(n, f"top/{s}", {"name": label, "fringes": short_money(sec.fringes, b) if sec.fringes else "",
                                          "total": short_money(sec.total, b)})  # fmt: skip
            d.setData(0, HAY, label.casefold())
            n += 1
            for c in cats:
                cs = t.categories[c.id]
                row = self.make(
                    "category",
                    c.id,
                    [("", ""), (c.code, c.code), (c.name or "Untitled Category", c.name),
                     (f"{cs.lines:,}" if cs.lines else "", cs.lines),
                     (short_money(cs.fringes, b) if cs.fringes else "", float(cs.fringes)),
                     (short_money(cs.total, b), float(cs.total))],
                    d,
                )  # fmt: skip
                row.setForeground(1, theme.qcolor(tokens.FAINT))
                row.setForeground(3, theme.qcolor(tokens.MUTED))
                row.setForeground(4, theme.qcolor(tokens.MUTED))
                row.setData(0, HAY, f"{c.code} {c.name} {label}".casefold())
        if not b.adjustments:
            self._fill_end(state)
            return
        d = self.band(n, "top/fees", {"name": "Fees", "total": short_money(t.fees, b)})
        d.setData(0, HAY, "fees contingency markup")
        for adj, a in zip(b.adjustments, t.adjustments, strict=False):
            what = a.name or "Untitled Fee"
            if adj.kind == "percent":
                what += f"  ·  {money.fmt_qty(money.parse(adj.rate))}%"
            row = self.make(
                "adjustment",
                adj.id,
                [("", ""), ("", ""), (what, what), ("", 0), ("", 0),
                 (short_money(a.amount, b) if not a.problem else "—", float(a.amount))],
                d,
            )  # fmt: skip
            if a.problem:
                row.setForeground(5, theme.qcolor(tokens.BAD))
                row.setToolTip(5, theme.plain_tip(a.problem))
            row.setData(0, HAY, f"{a.name} fee".casefold())
        self._fill_end(state)


# ---------------------------------------------------------------------------- a section's detail
class DetailTable(Table):
    """A section's categories (bands), their accounts (bold, folding) and the lines in each."""

    SORTABLE = False
    COLUMNS = [
        ("fold", "", tokens.FOLD_W, None),
        ("code", "Acct #", W["code"], None),
        ("description", "Description", 0, None),
        ("amount", "Amount", W["amount"], RIGHT),
        ("units", "Units", W["units"], RIGHT),
        ("unit", "Unit", W["unit"], None),
        ("rate", "Rate", W["rate"], RIGHT),
        ("subtotal", "Subtotal", W["money"], RIGHT),
        ("fringes", "Fringes", W["fringes"], RIGHT),
        ("total", "Total", W["total"], RIGHT),
    ]
    GIVE_WAY = ["subtotal", "fringes", "code", "unit", "amount"]
    EDITABLE = ("description", "amount", "units", "unit", "rate")
    name_col = 2
    fold_col = 0
    edited = Signal(str, str, str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.global_names: list[str] = []
        self.painter.edited.connect(self.edited.emit)
        self.setEditTriggers(QAbstractItemView.EditTrigger.EditKeyPressed)

    def fill(self, b: Budget, t: calc.Totals, section: str, keep=None) -> None:
        state = self._fill_start()
        self.global_names = [g.name for g in b.globals if g.name]
        semibold = theme.font(tokens.TEXT_MD, tokens.WEIGHT_SEMIBOLD)
        n = 0
        for c in b.categories:
            if c.section != section:
                continue
            cs = t.categories[c.id]
            d = self.band(
                n,
                f"cat/{c.id}",
                {"code": c.code, "description": c.name or "Untitled Category",
                 "fringes": short_money(cs.fringes, b) if cs.fringes else "", "total": short_money(cs.total, b)},
                "category",
                c.id,
            )  # fmt: skip
            d.setData(0, HAY, f"{c.code} {c.name}".casefold())
            n += 1
            for a in c.accounts:
                s = t.accounts[a.id]
                acc = self.make(
                    "account",
                    a.id,
                    [("", ""), (a.code, a.code), (a.name or "Untitled Account", a.name), ("", 0), ("", 0), ("", ""),
                     ("", 0), (short_money(s.subtotal, b) if s.subtotal else "", 0),
                     (short_money(s.fringes, b) if s.fringes else "", 0), (short_money(s.total, b), 0)],
                    d,
                )  # fmt: skip
                acc.setData(0, FOLD, f"acc/{a.id}")
                for col in range(len(self.COLUMNS)):
                    acc.setFont(col, semibold)
                acc.setForeground(1, theme.qcolor(tokens.FAINT))
                acc.setData(0, HAY, f"{a.code} {a.name} {c.name}".casefold())
                for ln in a.lines:
                    self._line(b, t, ln, acc)
        self._fill_end(state)

    def _line(self, b: Budget, t: calc.Totals, ln, parent) -> Row:
        lt = t.lines[ln.id]
        unit = UNIT_NAMES[ln.unit]
        row = self.make(
            "line",
            ln.id,
            [("", ""), ("", ""), (ln.description or "Untitled Line", ln.description), (qty(lt.amount), 0),
             (qty(lt.units), 0), (unit, ""), (short_money(lt.rate, b) if ln.rate.strip() else "", 0),
             (short_money(lt.subtotal, b) if not lt.problem else "", 0),
             (short_money(lt.fringes, b) if lt.fringes else "", 0),
             (short_money(lt.total, b) if not lt.problem else "—", 0)],
            parent,
        )  # fmt: skip
        row.setData(0, DEPTH, 1)
        row.setData(0, RAW, {"description": ln.description, "amount": ln.amount, "units": ln.units,
                             "unit": ln.unit, "rate": ln.rate})  # fmt: skip
        row.setFlags(row.flags() | Qt.ItemFlag.ItemIsEditable)
        if not ln.description:
            row.setForeground(2, theme.qcolor(tokens.FAINT))
        for key in ("unit", "fringes", "subtotal"):
            row.setForeground(self.col(key), theme.qcolor(tokens.MUTED))
        for key in ("amount", "units", "rate"):  # a number that follows a global is in the accent
            text = getattr(ln, key)
            if text.strip() and not formula.is_plain(text):
                c = self.col(key)
                row.setForeground(c, theme.qcolor(tokens.ACCENT))
                row.setToolTip(c, theme.plain_tip(text))
        if lt.problem:
            row.setForeground(self.col("total"), theme.qcolor(tokens.BAD))
            row.setToolTip(self.col("total"), theme.plain_tip(lt.problem))
        names = " ".join(f.name for fid in ln.fringes if (f := b.fringe(fid)) is not None)
        row.setData(0, HAY, f"{ln.description} {ln.notes} {names} {ln.rate}".casefold())
        return row


# ---------------------------------------------------------------------------- globals and fringes
class GlobalsTable(Table):
    COLUMNS = [
        ("fold", "", 0, None),
        ("name", "Name", W["value"], None),
        ("label", "What It Is", 0, None),
        ("value", "Value", W["value"], None),
        ("result", "Comes To", W["result"], RIGHT),
        ("used", "Used In", W["used"], RIGHT),
    ]
    GIVE_WAY = ["used", "value"]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setColumnHidden(0, True)

    def _apply_columns(self) -> None:
        super()._apply_columns()
        self.setColumnHidden(0, True)

    def fill(self, b: Budget, t: calc.Totals) -> None:
        state = self._fill_start()
        for g in b.globals:
            key = g.name.casefold()
            v = t.globals.get(key)
            problem = t.global_problems.get(key, "")
            uses = calc.uses_of(b, g.name) if g.name else 0
            unit = f" {UNIT_NAMES[g.unit]}" if g.unit and v is not None else ""
            row = self.make(
                "global",
                g.id,
                [("", ""), (g.name or "unnamed", g.name), (g.label, g.label), (g.value, g.value),
                 (f"{qty(v)}{unit}" if v is not None else "—", float(v) if v is not None else 0),
                 (f"{uses:,}" if uses else "", uses)],
            )  # fmt: skip
            row.setForeground(1, theme.qcolor(tokens.ACCENT))
            row.setForeground(3, theme.qcolor(tokens.MUTED))
            if problem:
                row.setForeground(4, theme.qcolor(tokens.BAD))
                row.setToolTip(4, theme.plain_tip(problem))
            row.setData(0, HAY, f"{g.name} {g.label} {g.value}".casefold())
        self._fill_end(state)


class FringesTable(Table):
    COLUMNS = [
        ("fold", "", 0, None),
        ("name", "Fringe", 0, None),
        ("kind", "Kind", W["kind"], None),
        ("rate", "Rate", W["rate"], RIGHT),
        ("cap", "Cap", W["cap"], RIGHT),
        ("lines", "Lines", W["lines"], RIGHT),
        ("total", "Total", W["total"], RIGHT),
    ]
    GIVE_WAY = ["cap", "kind", "lines"]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setColumnHidden(0, True)

    def _apply_columns(self) -> None:
        super()._apply_columns()
        self.setColumnHidden(0, True)

    def fill(self, b: Budget, t: calc.Totals) -> None:
        state = self._fill_start()
        for f in b.fringes:
            problem = t.fringe_problems.get(f.id, "")
            pct = f.kind == "percent"
            rate = f"{f.rate}%" if pct and f.rate.strip() and formula.is_plain(f.rate) else f.rate
            total = t.fringes.get(f.id, Decimal(0))
            row = self.make(
                "fringe",
                f.id,
                [("", ""), (f.name or "Untitled Fringe", f.name), ("Percent" if pct else "Flat per Unit", f.kind),
                 (rate, float(money.parse(f.rate))), (short_money(money.parse(f.cap), b) if pct and f.cap.strip() else "", 0),
                 (f"{t.fringe_lines.get(f.id, 0):,}", t.fringe_lines.get(f.id, 0)),
                 (short_money(total, b) if not problem else "—", float(total))],
            )  # fmt: skip
            for c in (2, 4):
                row.setForeground(c, theme.qcolor(tokens.MUTED))
            if problem:
                row.setForeground(6, theme.qcolor(tokens.BAD))
                row.setToolTip(6, theme.plain_tip(problem))
            row.setData(0, HAY, f"{f.name} {f.notes}".casefold())
        self._fill_end(state)


# ---------------------------------------------------------------------------- the rate library
class RatesTable(Table):
    COLUMNS = [
        ("fold", "", tokens.FOLD_W, None),
        ("name", "Name", 0, None),
        ("department", "Department", W["department"], None),
        ("union", "Union", W["union"], None),
        ("who", "Vendor or Who", W["department"], None),
        ("rate", "Rate", W["rate"], RIGHT),
        ("unit", "Per", W["unit"], None),
    ]
    GIVE_WAY = ["who", "department", "union"]
    fold_col = 0

    def fill(self, items: list[Rate], divide: bool, keep=None) -> None:
        state = self._fill_start()
        bands: dict[str, Row] = {}
        if divide:
            depts = sorted({r.department for r in items}, key=lambda d: (not d, d.casefold()))
            for n, dept in enumerate(depts):
                d = self.band(n, f"rates/{dept}", {"name": dept or "No Department"})
                d.setData(0, HAY, (dept or "").casefold())
                bands[dept] = d
        for r in items:
            union = (r.local or "Union") if r.union else ("Vendor" if r.kind == "vendor" else "Non-Union")
            row = self.make(
                "rate",
                r.id,
                [("", ""), (r.name or "Untitled Rate", r.name.casefold()), (r.department, r.department.casefold()),
                 (union, union.casefold()), (r.vendor, r.vendor.casefold()),
                 (money.fmt(money.parse(r.rate)) if r.rate.strip() else "", float(money.parse(r.rate))),
                 (UNIT_NAMES[r.unit].removesuffix("s") if r.unit not in ("allow", "flat", "each", "units") else UNIT_NAMES[r.unit], r.unit)],
                bands.get(r.department),
            )  # fmt: skip
            for c in (2, 3, 4, 6):
                row.setForeground(c, theme.qcolor(tokens.MUTED))
            if r.union:
                row.setForeground(3, theme.qcolor(tokens.ACCENT))
            row.setData(0, HAY, rates.haystack(r))
        self._fill_end(state)


def menu(parent: QWidget, items: list[tuple[str, str, object]]) -> QMenu:
    m = QMenu(parent)
    for icon, text, slot in items:
        if text == "-":
            m.addSeparator()
        else:
            m.addAction(theme.menu_icon(icon), text, slot)
    return m
