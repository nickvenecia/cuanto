"""The toolbar's filter button: how the list is divided, and what it shows. Its choices depend on the page:

    a section's detail   Show: Everything / Lines with Money / Lines Without a Rate / Lines with a Problem
    the rate library     Divide By: Department / No Dividers;  Show: Everything / Crew / Vendors / Union / Non-Union
    Clear Filters        back to how it starts

Just an icon; the accent while a filter hides something. Pages with nothing to filter don't show it.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QLabel, QMenu, QToolButton, QWidgetAction

from cuanto.core import calc, money
from cuanto.core.model import Budget, Rate
from cuanto.ui.style import theme

LINE_SHOWS = [
    ("all", "Everything", ""),
    ("money", "Lines with Money", "Lines that come to something"),
    ("no_rate", "Lines Without a Rate", "Lines still to price"),
    ("problem", "Lines with a Problem", "A formula that can't be worked out"),
]
RATE_SHOWS = [
    ("all", "Everything", ""),
    ("crew", "Crew", ""),
    ("vendor", "Vendors", ""),
    ("union", "Union", ""),
    ("non_union", "Non-Union", "Crew rates that aren't union"),
]
RATE_DIVIDES = [("department", "Department"), ("none", "No Dividers")]


@dataclass
class Filter:
    show: str = "all"
    divide: str = "department"

    def active(self) -> bool:
        return self.show != "all"


def keep_line(budget: Budget, t: calc.Totals, show: str):
    """A test on a line id, or None when nothing's filtered."""
    if show == "all":
        return None

    def keep(line_id: str) -> bool:
        lt = t.lines.get(line_id)
        if lt is None:
            return False
        if show == "money":
            return lt.total != 0
        if show == "problem":
            return bool(lt.problem)
        got = budget.find_line(line_id)
        return got is not None and money.parse(got[2].rate) == 0 and not lt.problem

    return keep


def keep_rate(r: Rate, show: str) -> bool:
    return {
        "all": True,
        "crew": r.kind == "crew",
        "vendor": r.kind == "vendor",
        "union": r.union,
        "non_union": r.kind == "crew" and not r.union,
    }.get(show, True)


class FilterButton(QToolButton):
    """The icon that opens the filter menu (built fresh each time, for the page it's on)."""

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Circle")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.page = "lines"  # lines / rates
        self.filters = {"lines": Filter(), "rates": Filter()}
        self.m = QMenu(self)
        self.m.setToolTipsVisible(True)
        self.m.aboutToShow.connect(self._build)
        self.setMenu(self.m)
        self.show_state()

    @property
    def filter(self) -> Filter:
        return self.filters[self.page]

    def set_page(self, page: str) -> None:
        self.page = page
        self.show_state()

    def is_default(self) -> bool:
        return self.filter == Filter()

    def clear(self) -> None:
        self.filters[self.page] = Filter()
        self.show_state()

    def show_state(self) -> None:
        on = self.filter.active()
        self.setIcon(theme.icon("filter", theme.ACCENT if on else theme.MUTED))
        if bool(self.property("active")) != on:
            self.setProperty("active", on)
            self.style().unpolish(self)
            self.style().polish(self)
        shows = dict((k, label) for k, label, _t in (LINE_SHOWS if self.page == "lines" else RATE_SHOWS))
        self.setToolTip(f"Showing: {shows.get(self.filter.show, '')}" if on else "Filter and divide the list")

    def _pick(self, what: str, key: str) -> None:
        setattr(self.filter, what, key)
        self.show_state()
        self.changed.emit()

    def _heading(self, text: str) -> None:
        label = QLabel(text)
        label.setObjectName("MenuHeading")
        a = QWidgetAction(self.m)
        a.setDefaultWidget(label)
        a.setEnabled(False)
        self.m.addAction(a)

    def _choices(self, what: str, items, current: str) -> None:
        group = QActionGroup(self.m)
        for key, label, *tip in items:
            a = QAction(label, group)
            a.setCheckable(True)
            a.setChecked(key == current)
            if tip and tip[0]:
                a.setToolTip(tip[0])
            a.triggered.connect(lambda _c=False, k=key: self._pick(what, k))
            self.m.addAction(a)

    def _build(self) -> None:
        m = self.m
        m.clear()
        if self.page == "rates":
            self._heading("Divide By")
            self._choices("divide", RATE_DIVIDES, self.filter.divide)
            m.addSeparator()
        self._heading("Show")
        self._choices("show", LINE_SHOWS if self.page == "lines" else RATE_SHOWS, self.filter.show)
        m.addSeparator()
        clear = m.addAction("Clear Filters")
        clear.setEnabled(not self.is_default())
        clear.triggered.connect(self._clear)

    def _clear(self) -> None:
        self.clear()
        self.changed.emit()
