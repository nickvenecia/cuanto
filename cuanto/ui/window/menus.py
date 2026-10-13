"""The menu bar (on the Mac; its keys work everywhere), the toolbar's share and + menus, the profile card's
menu, and Undo, Redo, Copy, Paste, Select All and Delete.

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

import sys

from PySide6.QtCore import QPoint
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QLineEdit, QMenu, QPlainTextEdit, QTextEdit, QToolButton

from cuanto import __version__
from cuanto.core.fileutil import reveal
from cuanto.core.model import SECTION_NAMES, SECTIONS
from cuanto.core.paths import data_dir, log_dir
from cuanto.ui.dialogs.common import about
from cuanto.ui.style import theme, tokens
from cuanto.ui.window.common import kind_of, section_of


class MenusMixin:
    def _menus(self) -> None:
        """Every command with its key. The menu bar shows on the Mac; on Windows and Linux it's hidden and
        the keys still work (the same commands are on the toolbar, the panels' ⋯ and the profile card)."""
        bar = self.menuBar()

        def act(m: QMenu, text: str, slot, keys=None) -> QAction:
            a = m.addAction(text)
            a.triggered.connect(slot)
            if keys is not None:
                a.setShortcut(QKeySequence(keys))
                self.addAction(a)
            return a

        f = bar.addMenu("File")
        act(f, "New", self.new_here, QKeySequence.StandardKey.New)
        act(f, "New Budget…", lambda: self.new_budget(), "Ctrl+Shift+N")
        act(f, "Save as Template…", lambda: self.save_as_template())
        f.addSeparator()
        act(f, "Import…", self.import_any, "Ctrl+Shift+I")
        act(f, "Import CSV…", self.import_csv)
        act(f, "Import JSON…", self.import_json)
        act(f, "Export Excel…", self.export_xlsx, "Ctrl+Shift+E")
        act(f, "Export JSON…", lambda: self.export_json())
        f.addSeparator()
        act(f, "Top Sheet & Detail…", lambda: self.show_pages(), QKeySequence.StandardKey.Print)
        act(f, "Back Up…", self.back_up)
        f.addSeparator()
        prefs = act(f, "Settings…", self.open_settings, QKeySequence.StandardKey.Preferences)
        prefs.setMenuRole(QAction.MenuRole.PreferencesRole)  # the Mac puts it under Cuánto, ⌘,
        if sys.platform != "darwin":
            prefs.setShortcut(QKeySequence("Ctrl+,"))  # (Windows and Linux have no standard key for it)
        quit_ = act(f, "Quit Cuánto", self.close, QKeySequence.StandardKey.Quit)
        quit_.setMenuRole(QAction.MenuRole.QuitRole)

        e = bar.addMenu("Edit")
        self.act_undo = act(e, "Undo", self.undo, QKeySequence.StandardKey.Undo)
        self.act_redo = act(e, "Redo", self.redo, "Ctrl+Shift+Z")
        if sys.platform != "darwin":  # Ctrl+Y too, as Windows apps do
            self.act_redo.setShortcuts([QKeySequence("Ctrl+Shift+Z"), QKeySequence("Ctrl+Y")])
        e.aboutToShow.connect(self._edit_menu_state)
        e.addSeparator()
        act(e, "Cut", lambda: self._text_do("cut"), QKeySequence.StandardKey.Cut)
        act(e, "Copy", self.copy, QKeySequence.StandardKey.Copy)
        act(e, "Paste", lambda: self._text_do("paste"), QKeySequence.StandardKey.Paste)
        act(e, "Select All", self.select_all, QKeySequence.StandardKey.SelectAll)
        e.addSeparator()
        act(e, "Duplicate", self.duplicate_current, "Ctrl+D")
        act(e, "Delete…", self.delete_current, "Ctrl+Backspace")
        e.addSeparator()
        act(e, "Find", self._focus_search, QKeySequence.StandardKey.Find)

        v = bar.addMenu("View")
        act(v, "All Budgets", lambda: self.go("budgets"), "Ctrl+1")
        act(v, "Top Sheet", lambda: self.go("top"), "Ctrl+2")
        act(v, "Production", lambda: self.go("sec:production"), "Ctrl+3")
        act(v, "Rate Library", lambda: self.go("rates"), "Ctrl+4")
        for s in SECTIONS:
            if s != "production":
                act(v, SECTION_NAMES[s], lambda _c=False, s=s: self.go(f"sec:{s}"))
        act(v, "Globals", lambda: self.go("globals"))
        act(v, "Fringes", lambda: self.go("fringes"))
        act(v, "Close Panel", self.deselect)
        v.addSeparator()
        self.look_actions = {}
        looks = v.addMenu("Appearance")
        for key, label in (("system", "Match the System"), ("light", "Light"), ("dark", "Dark")):
            a = looks.addAction(label)
            a.setCheckable(True)
            a.triggered.connect(lambda _c=False, k=key: self.set_look(k))
            self.look_actions[key] = a

        b = bar.addMenu("Budget")
        act(b, "New Line", lambda: self.new_line(), "Ctrl+Alt+N")
        act(b, "New Account", lambda: self.new_account())
        act(b, "New Category", lambda: self.new_category())
        act(b, "New Global", self.new_global)
        act(b, "New Fringe", self.new_fringe)
        act(b, "New Fee or Markup", self.new_adjustment)
        b.addSeparator()
        act(b, "Use a Rate…", lambda: self.open_kind == "line" and self.use_rate(self.open_id), "Ctrl+R")
        act(b, "Save Line to Rate Library", lambda: self.open_kind == "line" and self.save_rate(self.open_id))
        act(b, "New Crew Rate", lambda: self.new_rate("crew"))
        act(b, "New Vendor Rate", lambda: self.new_rate("vendor"))
        b.addSeparator()
        act(b, "Move Up", lambda: self._step_open(-1), "Ctrl+Alt+Up")
        act(b, "Move Down", lambda: self._step_open(1), "Ctrl+Alt+Down")
        b.addSeparator()
        act(b, "Budget Details…", lambda: self.budget_details(), "Ctrl+I")

        w = bar.addMenu("Window")
        act(w, "Minimize", self.showMinimized, "Ctrl+M")
        act(w, "Zoom", self.toggle_zoom)
        h = bar.addMenu("Help")
        act(h, "Keyboard Shortcuts", self.show_shortcuts, "Ctrl+/")
        act(h, "Send Feedback…", self.open_feedback)
        upd = act(h, "Check for Updates…", lambda: self.check_updates())
        upd.setMenuRole(
            QAction.MenuRole.ApplicationSpecificRole
        )  # on the Mac: in the Cuánto menu, like Mac apps
        act(h, "Open Data Folder", self.open_data_folder)
        act(h, "Open Log File", lambda: reveal(log_dir() / "cuanto.log"))
        act(h, "About Cuánto", lambda: about(self, __version__, str(data_dir())))
        bar.setVisible(sys.platform == "darwin")

        # the sidebar's section +: what's new there (a budget; or a line, an account, a category)
        here = QMenu(self.sidebar.btn_new_here)
        here.addAction(theme.menu_icon("plus"), "New Line", lambda: self.new_line())
        here.addAction(theme.menu_icon("folder"), "New Account", lambda: self.new_account())
        here.addAction(theme.menu_icon("table"), "New Category", lambda: self.new_category())
        here.addSeparator()
        here.addAction(theme.menu_icon("sliders"), "New Global", self.new_global)
        here.addAction(theme.menu_icon("percent"), "New Fringe", self.new_fringe)
        here.addAction(theme.menu_icon("receipt"), "New Fee or Markup", self.new_adjustment)
        self.sidebar.btn_new_here.setMenu(here)
        self.sidebar.btn_new_here.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

    def _toolbar_menus(self) -> None:
        """The share menu and the +, for the page you're on."""
        kind = kind_of(self.view_key)
        share = QMenu(self.btn_share)
        if self.budget is not None and kind != "budgets" and kind != "rates":
            share.addAction(theme.menu_icon("printer"), "Top Sheet & Detail…", lambda: self.show_pages())
            share.addAction(theme.menu_icon("table"), "Export Excel…", self.export_xlsx)
            share.addAction(theme.menu_icon("share"), "Export JSON…", lambda: self.export_json())
            share.addSeparator()
            share.addAction(theme.menu_icon("drop"), "Import CSV…", self.import_csv)
            share.addAction(theme.menu_icon("drop"), "Import JSON…", self.import_json)
        else:
            share.addAction(theme.menu_icon("drop"), "Import…", self.import_any)
            if kind == "budgets" and self.budget is not None:
                share.addSeparator()
                share.addAction(theme.menu_icon("table"), "Export Excel…", self.export_xlsx)
                share.addAction(theme.menu_icon("share"), "Export JSON…", lambda: self.export_json())
        old = self.btn_share.menu()
        self.btn_share.setMenu(share)
        if old is not None:
            old.deleteLater()
        tips = {
            "budgets": "New Budget…",
            "top": "New category or fee",
            "section": "New line, account or category",
            "globals": "New Global",
            "fringes": "New Fringe",
            "rates": "New Rate",
        }
        self.btn_new.setToolTip(tips[kind])
        menu = None
        if kind == "top":
            menu = QMenu(self.btn_new)
            menu.addAction(theme.menu_icon("table"), "New Category", lambda: self.new_category())
            menu.addAction(theme.menu_icon("receipt"), "New Fee or Markup", self.new_adjustment)
        elif kind == "section":
            menu = QMenu(self.btn_new)
            menu.addAction(theme.menu_icon("plus"), "New Line", lambda: self.new_line())
            menu.addAction(theme.menu_icon("folder"), "New Account", lambda: self.new_account())
            menu.addAction(
                theme.menu_icon("table"), "New Category", lambda: self.new_category(section_of(self.view_key))
            )
        elif kind == "rates":
            menu = QMenu(self.btn_new)
            menu.addAction(theme.menu_icon("tag"), "New Crew Rate", lambda: self.new_rate("crew"))
            menu.addAction(theme.menu_icon("box"), "New Vendor Rate", lambda: self.new_rate("vendor"))
        old = self.btn_new.menu()
        self.btn_new.setMenu(menu)
        self.btn_new.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
            if menu is not None
            else QToolButton.ToolButtonPopupMode.DelayedPopup
        )
        if old is not None and old is not menu:
            old.deleteLater()

    def _step_open(self, by: int) -> None:
        if self.open_kind in ("line", "account", "category", "adjustment"):
            self.step(self.open_kind, self.open_id, by)

    def _app_menu(self) -> None:
        """The profile card's menu: your profiles (pick one to work as), feedback, updates, and Settings."""
        card = self.sidebar.profile_card
        m = QMenu(card)
        current = self.current_profile()
        if len(self.lib.profiles) > 1:
            for p in self.lib.profiles.values():
                a = m.addAction(p.name or "Unnamed Profile")
                a.setCheckable(True)
                a.setChecked(current is not None and p.id == current.id)
                a.triggered.connect(lambda _c=False, pid=p.id: self.use_profile(pid))
            m.addSeparator()
        m.addAction(
            theme.menu_icon("edit"), "Edit Profile…", lambda: self.edit_profile(not self.lib.profiles)
        )
        m.addAction(theme.menu_icon("plus"), "Add a Profile…", lambda: self.edit_profile(True))
        m.addSeparator()
        m.addAction(theme.menu_icon("message"), "Send Feedback…", self.open_feedback)
        m.addAction(theme.menu_icon("arrow-down"), "Check for Updates…", lambda: self.check_updates())
        s = m.addAction(theme.menu_icon("cog"), "Settings…", self.open_settings)
        s.setShortcut(QKeySequence.StandardKey.Preferences)  # shown for reference; the menu bar's runs it
        s.setShortcutVisibleInContextMenu(True)
        at = card.mapToGlobal(QPoint(0, 0))
        m.exec(QPoint(at.x(), at.y() - m.sizeHint().height() - tokens.MENU_GAP))
        self.sidebar.show_who()

    # ------------------------------------------------------------------ Edit
    def _text_widget(self):
        """The text box you're typing in, if any (it keeps its own undo, cut, copy and paste)."""
        w = QApplication.focusWidget()
        return w if isinstance(w, (QLineEdit, QPlainTextEdit, QTextEdit)) else None

    def _text_do(self, what: str) -> None:
        w = self._text_widget()
        if w is not None and not (what in ("cut", "paste") and w.isReadOnly()):
            getattr(w, what)()

    def _text_can_undo(self, redo: bool = False) -> bool:
        w = self._text_widget()
        if isinstance(w, QLineEdit):
            return w.isRedoAvailable() if redo else w.isUndoAvailable()
        if w is not None:
            doc = w.document()
            return doc.isRedoAvailable() if redo else doc.isUndoAvailable()
        return False

    def undo(self) -> None:
        """⌘Z: in a text box, its typing; otherwise the last change to your budgets, rates or profiles."""
        if self._text_can_undo():
            self._text_do("undo")
            return
        self.flush()
        self._fresh = None
        what = self.history.undo() if self.history is not None else None
        if what is None:
            self.toast("Nothing to undo.")
            return
        self._after_history()
        self.toast(f"Undid the last change to {what}.", "done")

    def redo(self) -> None:
        if self._text_can_undo(redo=True):
            self._text_do("redo")
            return
        self.flush()
        what = self.history.redo() if self.history is not None else None
        if what is None:
            self.toast("Nothing to redo.")
            return
        self._after_history()
        self.toast(f"Redid the change to {what}.", "done")

    def _edit_menu_state(self) -> None:
        h = self.history
        self.act_undo.setEnabled(self._text_can_undo() or (h is not None and h.can_undo()))
        self.act_redo.setEnabled(self._text_can_undo(redo=True) or (h is not None and h.can_redo()))

    def _after_history(self) -> None:
        """Undo/redo put new copies of everything in the library: point at them, and show them again."""
        if self.budget is not None:
            self.budget = self.lib.budgets.get(self.budget.id)
        for p in self.panels.values():  # each loads its thing again from the new copies
            for attr in ("budget", "r"):
                if hasattr(p, attr):
                    setattr(p, attr, None)
        self.sidebar.show_who()
        self.refresh()

    def copy(self) -> None:
        """⌘C: text you've selected, or the lines you've picked as a plain list (description, total)."""
        if self._text_widget() is not None:
            self._text_do("copy")
            return
        t = self.current_table()
        if t is None:
            return
        rows = []
        for r in t.showing_rows():
            if r.isSelected():
                cells = [r.text(c) for c in range(t.columnCount()) if not t.isColumnHidden(c) and r.text(c)]
                rows.append("\t".join(cells))
        if rows:
            QApplication.clipboard().setText("\n".join(rows))
            self.toast(f"Copied {len(rows)} row{'s' if len(rows) != 1 else ''}.", "done")

    def select_all(self) -> None:
        if self._text_widget() is not None:
            self._text_do("selectAll")
            return
        t = self.current_table()
        if t is not None:
            t.setFocus()
            t.select_showing()

    def toggle_zoom(self) -> None:
        """Window › Zoom: fill the screen, or back to the smallest size (like double-clicking the title bar)."""
        from cuanto.ui.components import titlebar

        titlebar.toggle_size(self)

    def show_shortcuts(self) -> None:
        self.open_settings("shortcuts")

    def _focus_search(self) -> None:
        self.search.setFocus()
        self.search.selectAll()
