"""The window, full screen: the sidebar | a big table of where you are | the thing you picked, editable.

Pick a place in the sidebar (all your budgets, the rate library, or the open budget's top sheet, a section,
its globals or fringes), click a row, change it on the right. The top sheet and detail open in their own
window when you ask for them. Edits save themselves a moment after you stop typing.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QWidget,
)

from cuanto.core import calc, update
from cuanto.core.history import History
from cuanto.core.log import get_logger
from cuanto.core.model import Budget
from cuanto.core.store import Library
from cuanto.ui.components import titlebar
from cuanto.ui.components.empty import EmptyPage
from cuanto.ui.components.glass import Dock, GlassRoot, glass
from cuanto.ui.components.widgets import ElidedLabel, SearchField, Toast, hbox, vbox
from cuanto.ui.panels.account import AccountPanel
from cuanto.ui.panels.adjustment import AdjustmentPanel
from cuanto.ui.panels.budget import BudgetPanel
from cuanto.ui.panels.category import CategoryPanel
from cuanto.ui.panels.fringe import FringePanel
from cuanto.ui.panels.globals import GlobalPanel
from cuanto.ui.panels.line import LinePanel
from cuanto.ui.panels.rate import RatePanel
from cuanto.ui.style import theme, tokens
from cuanto.ui.window.common import TITLES, kind_of, needs_budget, section_of
from cuanto.ui.window.editing import EditingMixin
from cuanto.ui.window.filters import FilterButton, keep_line, keep_rate
from cuanto.ui.window.menus import MenusMixin
from cuanto.ui.window.pages import PagesMixin
from cuanto.ui.window.services import ServicesMixin
from cuanto.ui.window.sidebar import Sidebar
from cuanto.ui.window.tables import (
    BudgetsTable,
    DetailTable,
    FringesTable,
    GlobalsTable,
    RatesTable,
    TopSheetTable,
    compact_money,
    short_money,
)
from cuanto.ui.window.transfer import TransferMixin

log = get_logger(__name__)

TOTALS = [
    ("atl", "Above the Line"),
    ("btl", "Below the Line"),
    ("fringes", "Fringes"),
    ("fees", "Fees"),
    ("grand", "Grand Total"),
]


class MainWindow(MenusMixin, EditingMixin, TransferMixin, PagesMixin, ServicesMixin, QMainWindow):
    def __init__(self, lib: Library | None = None):
        super().__init__()
        self.lib = lib or Library().load()
        self.setWindowTitle("Cuánto")
        self.resize(*tokens.WINDOW_SIZE)
        self.setMinimumSize(*tokens.WINDOW_MIN)
        self._dirty: set[str] = set()  # budgets changed since the last save
        self._dirty_rates = False
        self.history: History | None = None
        self._fresh: tuple[str, str, dict] | None = None  # a new thing not filled in yet
        self.last_export: Path | None = None
        self._release: update.Release | None = None
        self.view_key = "budgets"
        self.page = None
        self.all_totals: dict[str, calc.Totals] = {}
        saved = self.lib.settings.get("budget", "")
        self.budget: Budget | None = self.lib.budgets.get(saved) if isinstance(saved, str) else None

        root = GlassRoot()
        self.root = root
        outer = vbox(root, 0, 0)
        self.titlebar = titlebar.install(self)
        if self.titlebar is not None:
            outer.addWidget(self.titlebar)
        gap = tokens.GLASS_GAP
        body = hbox(spacing=gap)
        body.setContentsMargins(gap, 0 if self.titlebar is not None else gap, gap, gap)
        self.sidebar = glass(Sidebar(self.lib))
        root.float(self.sidebar)
        body.addWidget(self.sidebar)
        body.addWidget(self._build_center(), 1)
        self.budget_panel = BudgetPanel(self.lib)
        self.category_panel = CategoryPanel()
        self.account_panel = AccountPanel()
        self.line_panel = LinePanel()
        self.global_panel = GlobalPanel()
        self.fringe_panel = FringePanel()
        self.adjustment_panel = AdjustmentPanel()
        self.rate_panel = RatePanel(self.lib)
        self.panels = {
            "budget": self.budget_panel,
            "category": self.category_panel,
            "account": self.account_panel,
            "line": self.line_panel,
            "global": self.global_panel,
            "fringe": self.fringe_panel,
            "adjustment": self.adjustment_panel,
            "rate": self.rate_panel,
        }
        self.inspector = glass(QStackedWidget())  # the glass panel on the right…
        for w in self.panels.values():
            self.inspector.addWidget(w)
        self.dock = Dock(self.inspector, root, self.sidebar, body)  # …which slides in when something's picked
        self.dock.follower = lambda: self.pages.currentWidget()
        outer.addLayout(body, 1)
        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc.activated.connect(self.deselect)
        self.setCentralWidget(root)
        self.toaster = Toast(self, self._toast_area)
        self.open_kind = ""  # what the panel on the right shows: line, account…
        self.open_id = ""

        self._save_timer = QTimer(self, singleShot=True, interval=tokens.SAVE_DELAY_MS, timeout=self.flush)
        self._table_timer = QTimer(
            self, singleShot=True, interval=tokens.TABLE_DELAY_MS, timeout=self.refresh
        )

        folded = self.lib.settings.get("folded", [])
        folded = {x for x in folded if isinstance(x, str)} if isinstance(folded, list) else set()
        for t in self.tables.values():
            t.folded = set(folded)
        self._wire()
        self._menus()
        self.look_changed()
        self._restored = False  # True: open at the size already set (screenshots), not the saved one
        view = self.lib.settings.get("view", "budgets")
        self.go(view if isinstance(view, str) else "budgets")
        self.history = History(self.lib)  # undo/redo starts from how things are when the window opens
        QTimer.singleShot(tokens.UPDATE_CHECK_DELAY_MS, self._auto_check_updates)

    # ------------------------------------------------------------------ building
    def _build_center(self) -> QWidget:
        center = QFrame()
        center.setObjectName("Center")
        lay = vbox(center, 0, 0)
        bar = QFrame()
        bar.setObjectName("Toolbar")
        bar.setFixedHeight(tokens.TOOLBAR_H)
        # three parts: the title on the left, the search and filter centred, the buttons on the right
        grid = QGridLayout(bar)
        grid.setContentsMargins(tokens.SPACE_4, 0, tokens.SPACE_2, 0)
        grid.setHorizontalSpacing(tokens.SPACE_4)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(2, 1)
        left = hbox(spacing=tokens.SPACE_2)
        self.title = QLabel(TITLES["budgets"])
        self.title.setObjectName("PageTitle")
        self.count = ElidedLabel()  # "3", "$1,583,281.32", or "5 selected": gives way before the search does
        self.count.setObjectName("PageCount")
        self.count.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        left.addWidget(self.title)
        left.addWidget(self.count, 1)
        grid.addLayout(left, 0, 0)
        mid = hbox(spacing=tokens.SPACE_2)
        self.search = SearchField()
        self.search.setPlaceholderText("Search")
        self.search.setProperty("capsule", True)
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(tokens.SEARCH_MIN)  # shrinks before anything squeezes together
        self.search.setMaximumWidth(tokens.SEARCH_W)
        self.search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.search.addAction(theme.icon("search", theme.FAINT), QLineEdit.ActionPosition.LeadingPosition)
        self.search.textChanged.connect(lambda _t: self._apply_search())
        mid.addWidget(self.search)
        self.filter_btn = FilterButton()
        self.filter_btn.changed.connect(self._filter_picked)
        mid.addWidget(self.filter_btn)
        grid.addLayout(mid, 0, 1, Qt.AlignmentFlag.AlignCenter)
        right = hbox(spacing=tokens.SPACE_2)
        right.addStretch(1)
        self.btn_share = QToolButton()
        self.btn_share.setObjectName("Circle")
        self.btn_share.setIcon(theme.icon("share", theme.MUTED))
        self.btn_share.setToolTip("Print, export and import")
        self.btn_share.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_share.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        right.addWidget(self.btn_share)
        self.btn_new = QToolButton()
        self.btn_new.setObjectName("CirclePrimary")
        self.btn_new.setIcon(theme.icon("plus", theme.ON_ACCENT))
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.clicked.connect(self.new_here)
        right.addWidget(self.btn_new)
        grid.addLayout(right, 0, 2)
        lay.addWidget(bar)
        bar.installEventFilter(self)
        self.toolbar = bar

        self.pages = QStackedWidget()
        self.tables = {
            "budgets": BudgetsTable(),
            "top": TopSheetTable(),
            "section": DetailTable(),
            "globals": GlobalsTable(),
            "fringes": FringesTable(),
            "rates": RatesTable(),
        }
        for t in self.tables.values():
            self.pages.addWidget(t)
        self.empty = EmptyPage()  # where the table would be, with nothing in it yet
        self.empty.dropped.connect(self.import_file)
        self.pages.addWidget(self.empty)
        lay.addWidget(self.pages, 1)
        self.totals = QFrame()
        self.totals.setObjectName("Totals")
        tl = hbox(
            self.totals, (tokens.SPACE_5, tokens.SPACE_3, tokens.SPACE_5, tokens.SPACE_3), tokens.SPACE_5
        )
        self.total_values: dict[str, QLabel] = {}
        tl.addStretch(1)
        for key, label in TOTALS:
            box = vbox(spacing=0)
            k = QLabel(label)
            k.setObjectName("TotalLabel")
            v = QLabel()
            v.setObjectName("GrandValue" if key == "grand" else "TotalValue")
            k.setAlignment(Qt.AlignmentFlag.AlignRight)
            v.setAlignment(Qt.AlignmentFlag.AlignRight)
            box.addWidget(k)
            box.addWidget(v)
            tl.addLayout(box)
            self.total_values[key] = v
        lay.addWidget(self.totals)
        return center

    def _wire(self) -> None:
        sb = self.sidebar
        sb.picked.connect(self._place_picked)
        sb.menu_wanted.connect(self._sidebar_menu)
        sb.profile_card.clicked.connect(self._app_menu)
        sb.btn_update.clicked.connect(self.show_update)
        sb.btn_new_budget.clicked.connect(lambda: self.new_budget())
        for t in self.tables.values():
            t.picked.connect(self.open)
            t.opened.connect(self._opened)
            t.menu_wanted.connect(self._row_menu)
            t.delete_wanted.connect(self.delete_many)
            t.cleared.connect(self.deselect)
            t.folds_changed.connect(self._remember_folds)
            t.itemSelectionChanged.connect(self._selection_count)
        self.tables["section"].edited.connect(self.cell_edited)
        for p in self.panels.values():
            p.changed.connect(self._edited)
            p.close_wanted.connect(self.deselect)
            p.toast_wanted.connect(self.toast)
        b = self.budget_panel
        b.open_wanted.connect(lambda i: self.go(f"budget:{i}"))
        b.duplicate_wanted.connect(lambda i: self.duplicate("budget", i))
        b.export_wanted.connect(self.export_json)
        b.delete_wanted.connect(lambda i: self.delete_many([("budget", i)]))
        c = self.category_panel
        c.new_account.connect(lambda i: self.new_account(i))
        c.show_accounts.connect(lambda i: self._opened("category", i))
        c.delete_wanted.connect(lambda i: self.delete_many([("category", i)]))
        c.step_wanted.connect(lambda i, n: self.step("category", i, n))
        c.section_changed.connect(lambda _i: self.refresh())
        a = self.account_panel
        a.new_line.connect(lambda i: self.new_line(account_id=i))
        a.moved.connect(self.move_account)
        a.duplicate_wanted.connect(lambda i: self.duplicate("account", i))
        a.delete_wanted.connect(lambda i: self.delete_many([("account", i)]))
        a.step_wanted.connect(lambda i, n: self.step("account", i, n))
        ln = self.line_panel
        ln.open_account.connect(lambda i: self.open("account", i))
        ln.new_line.connect(lambda i: self.new_line(after=i))
        ln.duplicate_wanted.connect(lambda i: self.duplicate("line", i))
        ln.delete_wanted.connect(lambda i: self.delete_many([("line", i)]))
        ln.step_wanted.connect(lambda i, n: self.step("line", i, n))
        ln.move_wanted.connect(self.move_line)
        ln.use_rate_wanted.connect(self.use_rate)
        ln.save_rate_wanted.connect(self.save_rate)
        g = self.global_panel
        g.delete_wanted.connect(lambda i: self.delete_many([("global", i)]))
        g.renamed.connect(self.global_renamed)
        self.fringe_panel.delete_wanted.connect(lambda i: self.delete_many([("fringe", i)]))
        adj = self.adjustment_panel
        adj.delete_wanted.connect(lambda i: self.delete_many([("adjustment", i)]))
        adj.step_wanted.connect(lambda i, n: self.step("adjustment", i, n))
        r = self.rate_panel
        r.add_wanted.connect(self.add_rate_to_budget)
        r.duplicate_wanted.connect(lambda i: self.duplicate("rate", i))
        r.delete_wanted.connect(lambda i: self.delete_many([("rate", i)]))

    # ------------------------------------------------------------------ where you are
    def current_table(self):
        page = self.pages.currentWidget()
        return page if page is not self.empty else None

    def _table_for(self, view: str):
        return self.tables.get(kind_of(view))

    def _place_picked(self, key: str) -> None:
        self.go(key)

    def go(self, view: str) -> None:
        """Show a place from the sidebar ("budget:<id>" opens that budget's top sheet)."""
        self.flush()
        self._drop_fresh()
        if view.startswith("budget:"):
            b = self.lib.budgets.get(view[7:])
            if b is not None:
                self.set_budget(b)
                view = "top"
            else:
                view = "budgets"
        if needs_budget(view) and self.budget is None:
            view = "budgets"
        if view not in TITLES:
            view = "budgets"
        changed = view != self.view_key
        self.view_key = view
        self.lib.settings["view"] = view
        self.title.setText(TITLES[view])
        kind = kind_of(view)
        self.filter_btn.set_page("rates" if kind == "rates" else "lines")
        if changed:
            self.search.blockSignals(True)
            self.search.clear()
            self.search.blockSignals(False)
        self._toolbar_menus()
        self.refresh()
        # keep what's open if it's still here; otherwise nothing is picked and the panel slides away
        t = self.current_table()
        if (
            self.open_kind
            and t is not None
            and self.dock.opened
            and t.find(self.open_kind, self.open_id) is not None
        ):
            t.select_id(self.open_kind, self.open_id)
        else:
            self._close_panel()

    def set_budget(self, b: Budget | None) -> None:
        """Open a budget: its places show in the sidebar."""
        if b is self.budget:
            return
        self.flush()
        self.budget = b
        self.lib.settings["budget"] = b.id if b is not None else ""
        self.setWindowTitle(f"{b.name or 'Untitled Budget'} — Cuánto" if b is not None else "Cuánto")

    def refresh(self) -> None:
        """Fill the table for where you are (and the sidebar's counts and totals)."""
        lib = self.lib
        if self.budget is not None and self.budget.id not in lib.budgets:  # deleted, or undone away
            self.budget = None
            self.lib.settings["budget"] = ""
        if needs_budget(self.view_key) and self.budget is None:
            self.view_key = "budgets"
            self.title.setText(TITLES["budgets"])
            self._toolbar_menus()
        self.all_totals = {b.id: calc.totals(b) for b in lib.budgets.values()}
        b = self.budget
        t = self.all_totals.get(b.id) if b is not None else None
        self.sidebar.refresh(b, self.all_totals)
        self.sidebar.select(self.view_key)
        kind = kind_of(self.view_key)
        table = self.tables[kind]
        page: QWidget = table
        if kind == "budgets":
            table.fill(lib.ordered_budgets(), self.all_totals)
            if not lib.budgets:
                page = self._empty_page("budgets")
        elif kind == "rates":
            show = self.filter_btn.filters["rates"]
            table.fill(
                [r for r in lib.ordered_rates() if keep_rate(r, show.show)], show.divide == "department"
            )
            if not lib.rates:
                page = self._empty_page("rates")
        elif kind == "top":
            table.fill(b, t)
            if not b.categories and not b.adjustments:
                page = self._empty_page("top")
        elif kind == "section":
            s = section_of(self.view_key)
            table.fill(b, t, s)
            if not any(c.section == s for c in b.categories):
                page = self._empty_page("section")
        elif kind == "globals":
            table.fill(b, t)
            if not b.globals:
                page = self._empty_page("globals")
        else:
            table.fill(b, t)
            if not b.fringes:
                page = self._empty_page("fringes")
        self.pages.setCurrentWidget(page)
        empty = page is self.empty
        self.search.setVisible(not empty)
        self.filter_btn.setVisible(not empty and kind in ("section", "rates"))
        if empty and self.dock.opened and self.open_kind != "budget":
            self.dock.set_open(False)
        self._apply_search()
        self._totals(t if needs_budget(self.view_key) else None)
        if self.dock.opened:
            self._reload_panel()
        if self.history is not None:
            self.history.mark()

    def _apply_search(self) -> None:
        t = self.current_table()
        if t is None:
            self._count_full = self._page_total() if needs_budget(self.view_key) else ""
            self.count.set_full_text(self._count_full)
            self._fit_toolbar()
            return
        keep = None
        if t is self.tables["section"] and self.budget is not None:
            k = keep_line(self.budget, self.all_totals[self.budget.id], self.filter_btn.filters["lines"].show)
            if k is not None:
                keep = lambda kind, i, k=k: kind == "line" and k(i)  # noqa: E731
        n = t.filter(self.search.text(), keep)
        if kind_of(self.view_key) in ("top", "section"):
            self._count_full = self._page_total()
        else:
            self._count_full, self._count_short = (f"{n:,}" if n else ""), ""
        self.count.set_full_text(self._count_full)
        self._fit_toolbar()

    def _page_total(self) -> str:
        """The page's total beside its title ("$763,843.33"); the short form ("$764K") is kept for a narrow
        window, where the search has already given way."""
        b = self.budget
        self._count_short = ""
        if b is None:
            return ""
        t = self.all_totals.get(b.id) or calc.totals(b)
        s = section_of(self.view_key)
        value = t.grand if self.view_key == "top" else (t.sections[s].total if s else None)
        if value is None:
            return ""
        self._count_short = compact_money(value, b)
        return short_money(value, b)

    def _totals(self, t: calc.Totals | None) -> None:
        """The bar under a budget's tables: above and below the line, fringes, fees, the grand total."""
        show = (
            t is not None
            and kind_of(self.view_key) in ("top", "section")
            and self.pages.currentWidget() is not self.empty
        )
        self.totals.setVisible(show)
        if not show:
            return
        b = self.budget
        self.total_values["atl"].setText(short_money(t.atl.total, b))
        self.total_values["btl"].setText(short_money(t.btl.total, b))
        self.total_values["fringes"].setText(short_money(t.direct.fringes, b))
        self.total_values["fees"].setText(short_money(t.fees, b))
        self.total_values["grand"].setText(short_money(t.grand, b))

    def _filter_picked(self) -> None:
        self.refresh()

    def _empty_page(self, which: str) -> QWidget:
        from cuanto.core import templates

        if which == "budgets":
            tiles = [
                (icon, name, words, "", lambda k=k: self.new_budget(k))
                for (k, name), (icon, words) in zip(
                    templates.choices()[:4],
                    (("film", "A full chart of accounts"), ("camera", "Lean and quick"),
                     ("receipt", "AICP-style bid form"), ("audio", "Artist, crew and post")),
                    strict=True,
                )
            ]  # fmt: skip
            tiles.append(
                ("table", "Import…", "A CSV or JSON budget", "Or drop a file on this page.", self.import_any)
            )
            self.empty.show_for(tuple(tiles), sheet_tile=4)
        elif which == "rates":
            self.empty.show_for(
                (
                    ("tag", "New Crew Rate", "A position, union or not", "", lambda: self.new_rate("crew")),
                    ("box", "New Vendor Rate", "Gear, a truck, a stage", "", lambda: self.new_rate("vendor")),
                    (
                        "table",
                        "Import JSON…",
                        "Rates from another tool",
                        "Or drop a file on this page.",
                        self.import_json,
                    ),
                ),
                sheet_tile=2,
            )
        elif which == "globals":
            self.empty.show_for((("sliders", "New Global", "Shoot days, prep weeks…", "", self.new_global),))
        elif which == "fringes":
            self.empty.show_for((("percent", "New Fringe", "Payroll tax, P&H, comp…", "", self.new_fringe),))
        else:
            section = section_of(self.view_key) or "production"
            self.empty.show_for(
                (
                    ("folder", "New Category", "A top-sheet row", "", lambda: self.new_category(section)),
                    (
                        "table",
                        "Import CSV…",
                        "Budget lines from a sheet",
                        "Or drop a file on this page.",
                        self.import_csv,
                    ),
                ),
                sheet_tile=1,
            )
        return self.empty

    # ------------------------------------------------------------------ opening
    def open(self, kind: str, obj_id: str) -> None:
        """Show a thing on the right (moving to its place first when it isn't on this page)."""
        self.flush()
        self._drop_fresh(keep=obj_id)
        b = self.budget
        panel = self.panels.get(kind)
        if panel is None:
            return
        if kind == "budget":
            got = self.lib.budgets.get(obj_id)
            if got is None:
                return
            panel.load(got)
        elif kind == "rate":
            r = self.lib.rates.get(obj_id)
            if r is None:
                return
            if self.view_key != "rates":
                self.go("rates")
            panel.load(r, self.budget is not None)
        else:
            if b is None:
                return
            if not self._load_budget_thing(kind, obj_id):
                self.toast("That's been deleted.")
                return
        self.open_kind, self.open_id = kind, obj_id
        t = self.current_table()
        if t is not None and t.current() != (kind, obj_id):
            t.select_id(kind, obj_id)
        self.inspector.setCurrentWidget(panel)
        self.dock.set_open(True)

    def _load_budget_thing(self, kind: str, obj_id: str) -> bool:
        """Load a part of the open budget into its panel (moving to the page it's on). False if it's gone."""
        b = self.budget
        if kind == "line":
            got = b.find_line(obj_id)
            if got is None:
                return False
            c, a, ln = got
            self._show_section_of(c.section)
            r = self.lib.rates.get(ln.rate_id) if ln.rate_id else None
            self.line_panel.load(b, c, a, ln, r.name if r is not None else "")
        elif kind == "account":
            got = b.find_account(obj_id)
            if got is None:
                return False
            self._show_section_of(got[0].section)
            self.account_panel.load(b, *got)
        elif kind == "category":
            c = b.find_category(obj_id)
            if c is None:
                return False
            if self.view_key != "top":
                self._show_section_of(c.section)
            self.category_panel.load(b, c)
        elif kind == "global":
            g = next((x for x in b.globals if x.id == obj_id), None)
            if g is None:
                return False
            if self.view_key != "globals":
                self.go("globals")
            self.global_panel.load(b, g)
        elif kind == "fringe":
            f = b.fringe(obj_id)
            if f is None:
                return False
            if self.view_key != "fringes":
                self.go("fringes")
            self.fringe_panel.load(b, f)
        elif kind == "adjustment":
            adj = next((x for x in b.adjustments if x.id == obj_id), None)
            if adj is None:
                return False
            if self.view_key != "top":
                self.go("top")
            self.adjustment_panel.load(b, adj)
        return True

    def _show_section_of(self, section: str) -> None:
        if self.view_key != f"sec:{section}":
            self.go(f"sec:{section}")

    def _reload_panel(self) -> None:
        """After a refresh: what's open on the right shows its new numbers (or goes, if it's gone)."""
        kind, obj_id = self.open_kind, self.open_id
        if not kind:
            return
        if kind == "budget":
            b = self.lib.budgets.get(obj_id)
            if b is None:
                self._close_panel()
            elif self.budget_panel.budget is not b:
                self.budget_panel.load(b)
            else:
                self.budget_panel.numbers()
            return
        if kind == "rate":
            r = self.lib.rates.get(obj_id)
            if r is None:
                self._close_panel()
            elif self.rate_panel.r is not r:
                self.rate_panel.load(r, self.budget is not None)
            return
        panel = self.panels[kind]
        b = self.budget
        if b is None:
            self._close_panel()
            return
        stale = getattr(panel, "budget", None) is not b
        exists = {
            "line": lambda: b.find_line(obj_id),
            "account": lambda: b.find_account(obj_id),
            "category": lambda: b.find_category(obj_id),
            "global": lambda: next((x for x in b.globals if x.id == obj_id), None),
            "fringe": lambda: b.fringe(obj_id),
            "adjustment": lambda: next((x for x in b.adjustments if x.id == obj_id), None),
        }[kind]()
        if exists is None:
            self._close_panel()
        elif stale:
            self._load_budget_thing(kind, obj_id)
        else:
            panel.numbers()

    def _opened(self, kind: str, obj_id: str) -> None:
        """A double-click: a budget opens, a category on the top sheet shows its accounts."""
        if kind == "budget":
            self.go(f"budget:{obj_id}")
        elif kind == "category" and self.budget is not None:
            c = self.budget.find_category(obj_id)
            if c is not None:
                self.go(f"sec:{c.section}")
                t = self.tables["section"]
                it = t.find("category", obj_id)
                if it is not None:
                    t.set_fold(it, True)
                    t.select_id("category", obj_id)
                    t.scrollToItem(it, t.ScrollHint.PositionAtTop)
                self.open("category", obj_id)

    def _close_panel(self) -> None:
        def blank() -> None:
            for p in self.panels.values():
                p.show_empty("Nothing selected")

        self.open_kind, self.open_id = "", ""
        self.dock.after_close(blank)  # it slides away still showing what was picked
        self.dock.set_open(False)

    def deselect(self) -> None:
        """Esc, or a click on empty space: nothing picked, the panel slides away (and a new thing you didn't
        fill in goes away)."""
        self.flush()
        self._drop_fresh()
        t = self.current_table()
        if t is not None:
            t._quiet = True
            t.clearSelection()
            t.setCurrentItem(None)
            t._quiet = False
        self._close_panel()

    def _remember_folds(self) -> None:
        folded: set[str] = set()
        for t in self.tables.values():
            folded |= t.folded
        self.lib.settings["folded"] = sorted(folded)

    def _selection_count(self) -> None:
        t = self.current_table()
        if t is None:
            return
        picked = len(t.chosen()) if len(t.selectedItems()) > 1 else 0
        if picked > 1:
            self.count.set_full_text(f"{picked} selected")
        else:
            self._apply_search()

    # ------------------------------------------------------------------ misc
    def toast(self, text: str, tone: str = "") -> None:
        """A short message over the page. `tone`: "done" (it worked), "problem" (it didn't: say what to do),
        or "" for news."""
        self.toaster.show_message(text, tone)

    def _toast_area(self) -> QRect:
        """Where toasts float: centred over the page, between the side panels, above the totals."""
        return QRect(self.pages.mapTo(self, QPoint(0, 0)), self.pages.size())

    def show(self) -> None:
        """The first time: filling the screen (all of it but the menu bar and Dock). After that: the size
        and place you left it, if it still fits a screen you have (else filling the screen again)."""
        if self._restored:
            super().show()
            return
        geo = self.lib.settings.get("geometry")
        if isinstance(geo, str) and geo and self._fits_after(geo):
            super().show()
        elif self.titlebar is not None:  # the Mac: fill the free area ourselves (zooming is unreliable here)
            titlebar.fill_screen(self)
            super().show()
        else:
            self.showMaximized()

    def _fits_after(self, geo: str) -> bool:
        """Put the window back where it was; True if that lands wholly on a screen."""
        try:
            if not self.restoreGeometry(QByteArray.fromHex(geo.encode())):
                return False
        except (TypeError, ValueError):
            return False
        frame = self.frameGeometry()
        return any(
            s.availableGeometry().adjusted(-2, -2, 2, 2).contains(frame) for s in QGuiApplication.screens()
        )

    def _fit_toolbar(self) -> None:
        """The search gives way so the title and its total always show whole (it asks for SEARCH_W and
        shrinks to SEARCH_MIN); past that, a money total shows in its short form. The toolbar's three parts
        never touch."""
        bar = self.toolbar
        gap = tokens.SPACE_4
        fm = self.count.fontMetrics()
        m = bar.layout().contentsMargins()
        right = sum(
            b.sizeHint().width() + tokens.SPACE_2 for b in (self.btn_share, self.btn_new) if not b.isHidden()
        )
        mid = self.filter_btn.sizeHint().width() + tokens.SPACE_2 if not self.filter_btn.isHidden() else 0

        def room_for(count: str) -> int:
            left = self.title.sizeHint().width() + tokens.SPACE_2 + fm.horizontalAdvance(count) + 2
            return bar.width() - m.left() - m.right() - 2 * max(left, right) - 2 * gap - mid

        full = getattr(self, "_count_full", self.count.full_text())
        short = getattr(self, "_count_short", "")
        room = room_for(full)
        text = full
        if room < tokens.SEARCH_MIN and short:
            text, room = short, room_for(short)
        if self.count.full_text() != text:
            self.count.set_full_text(text)
        width = max(tokens.SEARCH_MIN, min(tokens.SEARCH_W, room))
        if self.search.maximumWidth() != width:
            self.search.setMaximumWidth(width)

    def eventFilter(self, obj, e):
        if obj is getattr(self, "toolbar", None) and e.type() == e.Type.Resize:
            self._fit_toolbar()
        return super().eventFilter(obj, e)

    def resizeEvent(self, e):
        """The inspector gives up some width on a smaller window, so the toolbar never crowds."""
        super().resizeEvent(e)
        w = max(tokens.INSPECTOR_MIN, min(tokens.INSPECTOR_W, int(self.width() * tokens.INSPECTOR_SHARE)))
        self.dock.set_target(w)
        for i in range(self.inspector.count()):  # every right-hand panel, whatever it is
            self.inspector.widget(i).setFixedWidth(w)
        if self.toaster.isVisible():
            self.toaster.place()

    def _let_work_finish(self) -> None:
        """An update check may still be waiting on GitHub. Give it a moment; if it's still busy, quit without
        waiting for it (everything's saved by now), instead of crashing on the way out."""
        from PySide6.QtCore import QThread
        from PySide6.QtWidgets import QApplication

        busy = [t for t in self.findChildren(QThread) if t.isRunning()]
        for t in busy:
            t.wait(tokens.QUIT_WAIT_MS)
        if any(t.isRunning() for t in busy):
            log.info("quitting while a download is still running")
            QApplication.instance().setProperty("exit_now", True)

    def showEvent(self, e):
        super().showEvent(e)
        if self.titlebar is not None:
            QTimer.singleShot(0, self.titlebar.fit)

    def closeEvent(self, e):
        self.shutdown()
        super().closeEvent(e)

    def shutdown(self) -> None:
        """Save everything before quitting (and the window's size and place for next time)."""
        self.flush()
        self._drop_fresh()
        if not self._restored:
            self.lib.settings["geometry"] = bytes(self.saveGeometry().toHex()).decode()
        self._let_work_finish()
        try:
            self.lib.save_settings()
        except OSError:
            log.warning("couldn't save settings", exc_info=True)
