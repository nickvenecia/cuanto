"""The sidebar: where you are. Budgets (All Budgets, with each budget under it; the Rate Library), then the
open budget's own places: its Top Sheet, each section's detail, its Globals and Fringes. Clicking a heading
folds its section; each heading has a + that makes something new in it, faded in while the pointer is over
that section. Each place shows a count or its total. Your profile card sits at the bottom.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QPoint, QPropertyAnimation, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from cuanto.core import calc
from cuanto.core.model import SECTIONS, Budget
from cuanto.core.store import Library
from cuanto.ui.components.panels import LeftPanel, NavRow
from cuanto.ui.components.widgets import ElidedLabel, IconLabel, hbox, vbox
from cuanto.ui.style import theme, tokens
from cuanto.ui.window.common import PLACE_ICONS, TITLES
from cuanto.ui.window.tables import compact_money


class SectionHead(QFrame):
    """A heading over a list in the sidebar. Click it to fold the list away (or bring it back)."""

    toggled = Signal(bool)  # folded

    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("NavHead")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.folded = False
        self.lay = hbox(
            self, (tokens.SPACE_2, tokens.SPACE_1, tokens.SPACE_1, tokens.SPACE_1), tokens.SPACE_1
        )
        self.label = ElidedLabel(text)
        self.label.setObjectName("SectionLabel")
        # as wide as its words when there's room (then the arrow sits right after them), cut with "…" when not
        self.label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.chevron = IconLabel("chevron", "FAINT")
        self.lay.addWidget(self.label, 0)
        self.lay.addWidget(self.chevron)
        self.lay.addStretch(1)
        self.setFixedHeight(tokens.NAV_H)
        self._draw()

    def set_text(self, text: str) -> None:
        self.label.set_full_text(text)

    def _draw(self) -> None:
        self.chevron.set_icon("chevron-right" if self.folded else "chevron")

    def set_folded(self, on: bool) -> None:
        self.folded = on
        self._draw()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.set_folded(not self.folded)
            self.toggled.emit(self.folded)
        super().mousePressEvent(e)


class ProfileCard(QFrame):
    """The bottom of the sidebar: your profile (its initials, its name), and your account's email once you're
    signed in. Click for your profiles, feedback, updates and Settings."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ProfileCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(tokens.PROFILE_CARD_H)
        lay = hbox(self, (tokens.SPACE_2, 0, tokens.SPACE_2, 0), tokens.SPACE_2)
        self.avatar = QLabel()
        self.avatar.setObjectName("Avatar")
        self.avatar.setFixedSize(tokens.AVATAR, tokens.AVATAR)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.avatar)
        texts = vbox(spacing=0)  # the name (and who's signed in, when someone is), tight and centred
        self.name = ElidedLabel()
        self.name.setObjectName("ProfileName")
        self.sub = ElidedLabel()
        self.sub.setObjectName("ProfileSub")
        texts.addStretch(1)
        texts.addWidget(self.name)
        texts.addWidget(self.sub)
        texts.addStretch(1)
        lay.addLayout(texts, 1)
        lay.addWidget(IconLabel("updown", "FAINT"))

    def show_who(self, name: str, sub: str) -> None:
        words = [w for w in name.replace("&", " ").split() if w[:1].isalnum()]
        self.avatar.setText("".join(w[0] for w in words[:2]).upper() or "C")
        self.name.set_full_text(name)
        self.sub.set_full_text(sub)
        self.sub.setVisible(bool(sub))  # nothing to say until someone's signed in
        self.setToolTip("Profiles and Settings")

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)


class Sidebar(LeftPanel):
    picked = Signal(str)  # "budgets", "budget:<id>", "rates", "top", "sec:production", "globals", "fringes"
    menu_wanted = Signal(str, QPoint)  # right-click on a place (a budget has Duplicate, Delete…)

    def __init__(self, lib: Library, parent: QWidget | None = None):
        super().__init__(tokens.SIDEBAR_W, tokens.TOOLBAR_H, parent)
        self.lib = lib
        self.current = "budgets"
        self.budget: Budget | None = None
        self.word = word = QLabel(theme.wordmark())
        word.setObjectName("Wordmark")
        word.setTextFormat(Qt.TextFormat.RichText)
        self.top_lay.addWidget(word)

        self.heads: dict[str, SectionHead] = {}
        self.boxes: dict[str, QWidget] = {}
        self._section_plus: dict[str, QToolButton] = {}
        self.btn_new_budget = self._plus("New Budget…")
        lay = self._section("library", "Budgets", self.btn_new_budget)
        self._row("budgets", TITLES["budgets"], PLACE_ICONS["budgets"], lay)
        self.budget_lay = self._under("budgets", lay)
        self._row("rates", TITLES["rates"], PLACE_ICONS["rates"], lay)
        self.btn_new_here = self._plus("New line, account or category")
        lay = self._section("open", "", self.btn_new_here)
        for key in ("top", *[f"sec:{s}" for s in SECTIONS], "globals", "fringes"):
            self._row(key, TITLES[key], PLACE_ICONS[key], lay)
        self.lay.addStretch(1)
        folded = lib.settings.get("sidebar_folded", [])
        for key in folded if isinstance(folded, list) else []:
            if key in self.boxes:
                self._show_fold(key, True)

        self.btn_update = QPushButton()
        self.add_to_foot(self.btn_update)
        self.btn_update.hide()
        self.profile_card = ProfileCard()  # your profiles, and Settings (⌘,)
        self.add_to_foot(self.profile_card)

    # ------------------------------------------------------------------ the sections' +
    def _plus(self, tip: str) -> QToolButton:
        """A section's add button, as on the Mac: a small plain gray +, faded in while the pointer is over its
        own section (heading or rows) and faded out when it leaves. Always there for the layout, so nothing shifts."""
        b = QToolButton()
        b.setObjectName("SectionAdd")
        b.setIcon(theme.icon("plus", theme.MUTED, tokens.ICON_SM))
        b.setToolTip(tip)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # the same commands are in the menus, with keys
        fx = QGraphicsOpacityEffect(b)
        fx.setOpacity(0.0)
        b.setGraphicsEffect(fx)
        anim = QPropertyAnimation(fx, b"opacity", b)
        anim.setDuration(tokens.FADE_MS)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        b._fade = anim
        return b

    @staticmethod
    def _fade(b: QToolButton, on: bool) -> None:
        fx, anim = b.graphicsEffect(), b._fade
        target = 1.0 if on else 0.0
        if anim.endValue() == target and anim.state() == QPropertyAnimation.State.Running:
            return
        if abs(fx.opacity() - target) < 0.01:
            return
        anim.stop()
        anim.setStartValue(fx.opacity())
        anim.setEndValue(target)
        anim.start()

    def _hover_check(self) -> None:
        """Show the + of the section under the pointer, and only that one."""
        at = QCursor.pos()
        for key, plus in self._section_plus.items():
            head, box = self.heads[key], self.boxes[key]
            if not head.isVisible():
                continue
            area = QRect(head.mapToGlobal(QPoint(0, 0)), head.size())
            if box.isVisible():
                area = area.united(QRect(box.mapToGlobal(QPoint(0, 0)), box.size()))
            self._fade(plus, self.underMouse() and area.contains(at))

    def eventFilter(self, obj, e):
        if e.type() in (QEvent.Type.Enter, QEvent.Type.Leave, QEvent.Type.HoverMove):
            QTimer.singleShot(0, self._hover_check)
        return super().eventFilter(obj, e)

    def leaveEvent(self, e):
        for plus in self._section_plus.values():
            self._fade(plus, False)
        super().leaveEvent(e)

    # ------------------------------------------------------------------ building
    def _section(self, key: str, text: str, plus: QToolButton):
        """A heading and the list under it; returns the list's layout."""
        head = SectionHead(text)
        head.lay.addWidget(plus)
        box = QWidget()
        self._section_plus[key] = plus
        for w in (head, box):
            w.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
            w.installEventFilter(self)
        lay = vbox(box, (0, 0, 0, tokens.SPACE_3), tokens.NAV_GAP)
        head.toggled.connect(lambda folded, k=key: self._fold(k, folded))
        self.lay.addWidget(head)
        self.lay.addWidget(box)
        self.heads[key], self.boxes[key] = head, box
        return lay

    def _under(self, key: str, into):
        """The rows under row `key` (its arrow folds them); returns their layout."""
        box = QWidget()
        lay = vbox(box, 0, tokens.NAV_GAP)
        into.addWidget(box)
        self.boxes[key] = box
        self.rows[key].fold_wanted.connect(lambda k: self._fold(k, not self.rows[k].folded))
        return lay

    def _row(self, key: str, label: str, icon: str = "", into=None) -> NavRow:
        r = self.add_row(key, label, icon, into)
        r.clicked.connect(self.pick)
        r.menu_wanted.connect(self.menu_wanted.emit)
        return r

    def show_who(self) -> None:
        """The profile card: your profile, and whether you're signed in."""
        from cuanto.services import account

        p = self.lib.profile()
        who = account.current()
        self.profile_card.show_who((p.name if p and p.name else "Your Profile"), who.email if who else "")

    def recolor(self) -> None:
        """The look changed: redraw the icons."""
        for h in self.heads.values():
            h._draw()
        for r in self.rows.values():
            r.recolor()
        for b in self._section_plus.values():
            b.setIcon(theme.icon("plus", theme.MUTED, tokens.ICON_SM))

    def _show_fold(self, key: str, folded: bool) -> None:
        self.boxes[key].setVisible(not folded)
        if key in self.heads:
            self.heads[key].set_folded(folded)
        else:
            self.rows[key].set_folded(folded)

    def _fold(self, key: str, folded: bool) -> None:
        self._show_fold(key, folded)
        self.lib.settings["sidebar_folded"] = sorted(
            [k for k, h in self.heads.items() if h.folded]
            + (["budgets"] if self.rows["budgets"].folded else [])
        )
        self.lib.save_settings()

    def pick(self, key: str) -> None:
        self.select(key)
        self.picked.emit(key)

    def select(self, key: str) -> None:
        self.current = key
        super().select(key)

    # ------------------------------------------------------------------ filling
    def refresh(self, budget: Budget | None, totals: dict[str, calc.Totals]) -> None:
        """One row per budget, the open budget's places, and every count."""
        lib = self.lib
        self.budget = budget
        budgets = lib.ordered_budgets()
        have = [k for k in self.rows if k.startswith("budget:")]
        if have != [f"budget:{b.id}" for b in budgets]:
            for k in have:
                self.rows.pop(k).deleteLater()
            for b in budgets:
                self._row(f"budget:{b.id}", "", "", self.budget_lay).as_child()
        for b in budgets:
            row = self.rows[f"budget:{b.id}"]
            row.label.set_full_text(b.name or "Untitled Budget")
            row.set_count(compact_money(totals[b.id].grand, b) if b.id in totals else "")
        self.rows["budgets"].arrow.setVisible(bool(budgets))
        self.rows["budgets"].set_count(len(budgets))
        self.rows["rates"].set_count(len(lib.rates))
        open_ = budget is not None
        self.heads["open"].setVisible(open_)
        self.boxes["open"].setVisible(open_ and not self.heads["open"].folded)
        if open_:
            self.heads["open"].set_text(budget.name or "Untitled Budget")
            t = totals.get(budget.id) or calc.totals(budget)
            self.rows["top"].set_count(compact_money(t.grand, budget))
            for s in SECTIONS:
                row = self.rows[f"sec:{s}"]
                row.set_count(compact_money(t.sections[s].total, budget))
            self.rows["globals"].set_count(len(budget.globals))
            self.rows["fringes"].set_count(len(budget.fringes))
        self.show_who()
        self.select(self.current if self.current in self.rows else "budgets")
