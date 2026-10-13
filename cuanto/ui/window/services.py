"""Settings, your profiles, your account, feedback, updates, and light or dark.

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

import time

from cuanto import __version__
from cuanto.core import update
from cuanto.core.model import Profile
from cuanto.ui.style import theme, tokens


class ServicesMixin:
    def open_settings(self, pane: str = "general", **kw) -> None:
        """Settings, at a section: general, profiles, templates, account, shortcuts, data."""
        from cuanto.ui.dialogs.settings import SettingsDialog

        self.flush()
        SettingsDialog(self.lib, self, pane, **kw).exec()
        self.lib.save_settings()
        self.sidebar.show_who()
        self.refresh()

    # ------------------------------------------------------------------ profiles
    def current_profile(self) -> Profile | None:
        return self.lib.profile()

    def use_profile(self, profile_id: str) -> None:
        """Work as another of your profiles (budgets without their own print with it)."""
        if profile_id in self.lib.profiles:
            self.lib.settings["profile"] = profile_id
            self.lib.save_settings()
            self.sidebar.show_who()
            self.refresh()

    def edit_profile(self, add: bool = False) -> None:
        cur = self.current_profile()
        self.open_settings("profiles", profile=cur.id if cur and not add else None, add_profile=add)

    def profile_start(self, pick: str | None) -> tuple[Profile | None, Profile | None, bool]:
        """For the profile form: (the profile being edited, what the form starts from, can it be deleted)."""
        cur = self.lib.profiles.get(pick) if pick else None
        if cur is not None:
            return cur, cur, True
        return None, None, False

    def profile_saved(self, d, current: Profile | None) -> str:
        """The profile form was saved (or Delete was chosen). Returns the saved profile's id ("" if deleted)."""
        if d.deleted and current is not None:
            self.lib.delete_profile(current.id)
            if self.lib.settings.get("profile") == current.id:
                self.lib.settings["profile"] = next(iter(self.lib.profiles), "")
            self.lib.save_settings()
            self.sidebar.show_who()
            return ""
        p = d.profile
        self.lib.add_profile(p)
        if current is None and (len(self.lib.profiles) == 1 or not self.lib.settings.get("profile")):
            self.lib.settings["profile"] = p.id
            self.lib.save_settings()
        self.sidebar.show_who()
        return p.id

    # ------------------------------------------------------------------ account and feedback
    def open_account(self) -> None:
        self.open_settings("account")

    def open_feedback(self) -> None:
        from cuanto.ui.dialogs.feedback import FeedbackDialog

        d = FeedbackDialog(self)
        if d.exec():
            self.toast(
                "Thanks! Sent."
                if d.sent_now
                else "Thanks! It's saved and goes out once sending is switched on.",
                "done",
            )

    # ------------------------------------------------------------------ updates
    def _auto_check_updates(self) -> None:
        if not self.lib.settings.get("auto_update", True) or update.install_kind() == "source":
            return
        self.check_updates(quiet=True)  # every time Cuánto opens

    def check_updates(self, quiet: bool = False) -> None:
        from cuanto.ui.dialogs.update import CheckThread

        self._check = CheckThread(self)
        self._check.found.connect(lambda rel: self._found_release(rel, quiet))
        self._check.failed.connect(
            lambda _m: (
                None
                if quiet
                else self.toast("Couldn't reach GitHub. Check your internet and try again.", "problem")
            )
        )
        self._check.start()

    def _found_release(self, rel: update.Release, quiet: bool) -> None:
        self.lib.settings["last_update_check"] = time.time()
        if rel.newer:
            self._release = rel
            self.sidebar.btn_update.setText(f"Update to {rel.version}")
            self.sidebar.btn_update.show()
            if quiet:
                self._offer_update()  # found on its own: say so right away (Later closes it, like any window)
            else:
                self.show_update()
        elif not quiet:
            self.toast(f"You have the newest Cuánto ({__version__}).", "done")

    def _offer_update(self) -> None:
        """Show the update window once Cuánto is free: never on top of another window or an open menu."""
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        busy = QApplication.activeModalWidget() is not None or QApplication.activePopupWidget() is not None
        if busy or not self.isVisible():
            QTimer.singleShot(tokens.UPDATE_WAIT_MS, self._offer_update)
            return
        self.show_update()

    def show_update(self) -> None:
        if self._release is None:
            return
        from cuanto.ui.dialogs.update import UpdateDialog, restart_into

        d = UpdateDialog(self._release, parent=self)
        if d.exec() == UpdateDialog.DialogCode.Accepted and d.plan is not None:
            self.shutdown()
            restart_into(d.plan)

    # ------------------------------------------------------------------ the look
    def set_look(self, appearance: str) -> None:
        """Light, Dark, or Match the System."""
        from PySide6.QtWidgets import QApplication

        from cuanto.app import set_appearance

        self.lib.settings["appearance"] = appearance
        set_appearance(QApplication.instance(), appearance)

    def set_accent(self, key: str) -> None:
        """The accent color ("" or Cuánto's own orange: the default)."""
        from PySide6.QtWidgets import QApplication

        from cuanto.app import set_appearance

        key = "" if key == tokens.APP_ACCENT or key not in tokens.ACCENTS else key
        self.lib.settings["accent"] = key
        self.lib.save_settings()
        app = QApplication.instance()
        set_appearance(app, getattr(app, "_appearance", "system"), key)

    def look_changed(self) -> None:
        """The colors changed: redraw what holds its own."""
        from PySide6.QtWidgets import QApplication

        current = getattr(QApplication.instance(), "_appearance", "system")
        for k, a in getattr(self, "look_actions", {}).items():
            a.setChecked(k == current)
        self.sidebar.word.setText(theme.wordmark())
        self.sidebar.recolor()
        self.line_panel.recolor()
        self.btn_share.setIcon(theme.icon("share", theme.MUTED))
        self.btn_new.setIcon(theme.icon("plus", theme.ON_ACCENT))
        self.filter_btn.show_state()
        if self.titlebar is not None:
            self.titlebar.word.setText(theme.wordmark())
        if getattr(self, "history", None) is not None:
            self.refresh()
        self.redraw()
