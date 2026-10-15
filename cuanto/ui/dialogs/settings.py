"""Settings (⌘,): one window with a glass sidebar of sections, like the Mac's System Settings.

    General             Appearance, Accent Color; updates
    Profiles            your profiles (name, logo, contact, paper), edited right here
    Templates           your own templates: rename or delete them
    Account             sign in or out
    Keyboard Shortcuts  every key, read from the menus
    Your Data           the folder, Back Up

Everything is edited inside its section, so Settings never opens a window on top of itself. Things that aren't
settings (Send Feedback, About) have their own windows.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QStackedWidget, QWidget

from cuanto import __version__
from cuanto.core.model import KIND_NAMES, Template
from cuanto.core.paths import data_dir
from cuanto.core.store import Library
from cuanto.services import account
from cuanto.ui.components.glass import GlassRoot
from cuanto.ui.components.panels import LeftPanel
from cuanto.ui.components.widgets import (
    AccentPicker,
    ElidedLabel,
    FitScroll,
    Section,
    Segmented,
    ToggleRow,
    combo,
    hbox,
    vbox,
)
from cuanto.ui.dialogs.common import confirm
from cuanto.ui.style import tokens

LOOKS = [("system", "Match System"), ("light", "Light"), ("dark", "Dark")]
PANES = [
    ("general", "General", "cog"),
    ("profiles", "Profiles", "user"),
    ("templates", "Templates", "file"),
    ("account", "Account", "key"),
    ("shortcuts", "Keyboard Shortcuts", "keyboard"),
    ("data", "Your Data", "box"),
]


class SettingsDialog(QDialog):
    def __init__(
        self,
        lib: Library,
        window,
        pane: str = "general",
        profile: str | None = None,
        add_profile: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent or window)
        self.lib = lib
        self.win = window
        self.setWindowTitle("Settings")
        self.resize(*tokens.SETTINGS_SIZE)
        self.setMinimumSize(*tokens.SETTINGS_MIN)
        self._profile_id = profile
        self._adding = add_profile or not lib.profiles

        outer = vbox(self, 0, 0)
        root = GlassRoot()
        outer.addWidget(root)
        gap = tokens.GLASS_GAP
        body = hbox(root, gap, gap)
        self.side = side = LeftPanel(tokens.SETTINGS_SIDE_W)
        root.float(side)
        for key, label, icon in PANES:
            side.add_row(key, label, icon, foldable=False).clicked.connect(self.show_pane)
        side.lay.addStretch(1)
        self.rows = side.rows
        body.addWidget(side)

        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)
        self.panes: dict[str, QWidget] = {}
        for key, label, _icon in PANES:
            page = QWidget()
            lay = vbox(page, (tokens.SPACE_4, tokens.SPACE_4, tokens.SPACE_4, 0), tokens.SPACE_3)
            title = QLabel(label)
            title.setObjectName("PageTitle")
            lay.addWidget(title)
            holder = QWidget()
            vbox(holder, 0, 0)
            lay.addWidget(holder, 1)
            self.stack.addWidget(page)
            self.panes[key] = holder
        self._build_general()
        self._build_profiles()
        self._build_templates()
        self._build_account()
        self._build_shortcuts()
        self._build_data()
        self.show_pane(pane if pane in self.panes else "general")

    # ------------------------------------------------------------------ moving around
    def show_pane(self, key: str) -> None:
        self.side.select(key)
        self.stack.setCurrentIndex([k for k, _l, _i in PANES].index(key))
        self.setWindowTitle(dict((k, label) for k, label, _i in PANES)[key])

    def current_pane(self) -> str:
        return PANES[self.stack.currentIndex()][0]

    def _fill(self, key: str, w: QWidget, scroll: bool = True) -> None:
        """Put `w` in a section (replacing what was there)."""
        holder = self.panes[key]
        lay = holder.layout()
        while lay.count():
            old = lay.takeAt(0).widget()
            if old is not None:
                # hidden first, while it's whole, so the typing leaves it now: an embedded dialog (the profile,
                # Sign In) hides itself as it's thrown away, and moving the typing then crashed Cuánto on Save
                old.hide()
                old.deleteLater()
        inner = w
        if scroll:
            area = FitScroll()
            area.setWidget(w)
            w = area
        lay.addWidget(w)
        inner.show()  # (an embedded dialog starts hidden)

    @staticmethod
    def _column() -> tuple[QWidget, object]:
        w = QWidget()
        lay = vbox(w, (0, 0, tokens.SPACE_3, tokens.SPACE_4), tokens.SPACE_3)
        return w, lay

    def _row(self, text: str, *buttons: QPushButton) -> object:
        row = hbox(spacing=tokens.SPACE_2)
        label = ElidedLabel(text)
        label.setObjectName("Muted")
        row.addWidget(label, 1)
        for b in buttons:
            row.addWidget(b)
        return row

    # ------------------------------------------------------------------ General
    def _build_general(self) -> None:
        w, lay = self._column()
        look = Section("Appearance")
        self.look = Segmented(LOOKS)
        self.look.set_value(str(self.lib.settings.get("appearance", "system")))
        self.look.changed.connect(self.win.set_look)
        look.add(self.look)
        lay.addWidget(look)
        accent = Section("Accent Color")
        self.accent = AccentPicker(str(self.lib.settings.get("accent", "")))
        self.accent.picked.connect(self.win.set_accent)
        accent.add(self.accent)
        lay.addWidget(accent)
        upd = Section("Updates")
        self.auto = ToggleRow(
            "Check for Updates Automatically", bool(self.lib.settings.get("auto_update", True))
        )
        self.auto.toggled.connect(self._auto)
        upd.add(self.auto)
        version = ElidedLabel(f"Version {__version__}")
        version.setObjectName("Meta")
        upd.add(version)  # checking now is a command: the profile menu and Cuánto › Check for Updates…
        lay.addWidget(upd)
        lay.addStretch(1)
        self._fill("general", w)

    def _auto(self, on: bool) -> None:
        self.lib.settings["auto_update"] = on
        self.lib.save_settings()

    # ------------------------------------------------------------------ Profiles
    def _build_profiles(self) -> None:
        from cuanto.ui.dialogs.profile import ProfileDialog

        lib = self.lib
        w = QWidget()
        lay = vbox(w, 0, tokens.SPACE_2)
        if lib.profiles:
            row = hbox(spacing=tokens.SPACE_2)
            pick = self._profile_id if self._profile_id in lib.profiles else None
            if pick is None and not self._adding:
                cur = self.win.current_profile()
                pick = cur.id if cur is not None else None
            choices = [(p.id, p.name or "Unnamed Profile", "") for p in lib.profiles.values()]
            if self._adding:
                choices.append(("", "New Profile", ""))
            self.profile_pick = combo(choices, "" if self._adding else (pick or ""))
            self.profile_pick.activated.connect(lambda _i: self._pick_profile())
            row.addWidget(self.profile_pick, 1)
            add = QPushButton("Add a Profile")
            add.setEnabled(not self._adding)
            add.clicked.connect(self._add_profile)
            row.addWidget(add)
            row.setContentsMargins(0, 0, tokens.SPACE_3, 0)
            lay.addLayout(row)
        else:
            self.profile_pick = None
            pick = None
        current, start, can_delete = self.win.profile_start(None if self._adding else pick)
        d = ProfileDialog(start, can_delete, w, new=current is None)
        d.embed()
        d.layout().setContentsMargins(0, tokens.SPACE_2, 0, tokens.SPACE_4)
        d.side_margin(0)
        d.save.setText("Add Profile" if current is None else "Save Changes")
        d.accepted.connect(lambda: self._profile_done(d, current))
        lay.addWidget(d, 1)
        d.show()
        self.profile_editor = d
        self._fill("profiles", w, scroll=False)

    def _pick_profile(self) -> None:
        key = self.profile_pick.currentData()
        self._adding = not key
        self._profile_id = key or None
        self._build_profiles()

    def _add_profile(self) -> None:
        self._adding = True
        self._profile_id = None
        self._build_profiles()

    def _profile_done(self, d, current) -> None:
        saved = self.win.profile_saved(d, current)
        self._adding = False
        self._profile_id = saved or None
        self._build_profiles()
        self.win.toast("Profile deleted." if not saved else "Profile saved.", "done")

    # ------------------------------------------------------------------ Templates
    def _build_templates(self) -> None:
        w, lay = self._column()
        mine = self.lib.ordered_templates()
        if not mine:
            none = QLabel("No templates yet.")
            none.setObjectName("Muted")
            lay.addWidget(none)
        for t in mine:
            sec = Section(KIND_NAMES.get(t.budget.kind, ""))
            row = hbox(spacing=tokens.SPACE_2)
            name = QLineEdit(t.name)
            name.setPlaceholderText("Template name")
            name.editingFinished.connect(lambda t=t, name=name: self._rename_template(t, name))
            row.addWidget(name, 1)
            delete = QPushButton("Delete…")
            delete.setObjectName("Danger")
            delete.clicked.connect(lambda _c=False, t=t: self._delete_template(t))
            row.addWidget(delete)
            sec.add(row)
            lay.addWidget(sec)
        lay.addStretch(1)
        self._fill("templates", w)

    def _rename_template(self, t: Template, field: QLineEdit) -> None:
        new = field.text().strip()
        if not new or new == t.name:
            field.setText(t.name)
            return
        other = self.lib.template_named(new)
        if other is not None and other is not t:
            field.setText(t.name)
            self.win.toast(f"There's already a template called {other.name}.", "problem")
            return
        t.name = new
        self.lib.save_templates()
        self.win.refresh()

    def _delete_template(self, t: Template) -> None:
        if not confirm(
            self,
            f"Delete {t.name or 'this template'}?",
            "Budgets started from it stay as they are.",
            "Delete",
        ):
            return
        self.lib.delete_template(t.id)
        self.win.refresh()
        self._build_templates()
        self.win.toast("Deleted it.", "done")

    # ------------------------------------------------------------------ Account
    def _build_account(self) -> None:
        from cuanto.ui.dialogs.account import SignInDialog

        who = account.current()
        if who is not None:
            w, lay = self._column()
            out = QPushButton("Sign Out")
            out.clicked.connect(self._sign_out)
            lay.addLayout(self._row(f"Signed in as {who.email}", out))
            lay.addStretch(1)
            self._fill("account", w)
            return
        d = SignInDialog()
        d.embed()
        d.word.hide()
        d.layout().setContentsMargins(0, 0, tokens.SPACE_3, tokens.SPACE_4)
        d.layout().addStretch(1)
        d.accepted.connect(self._signed_in)
        self._fill("account", d)

    def _signed_in(self) -> None:
        self._build_account()
        self.win.sidebar.show_who()

    def _sign_out(self) -> None:
        try:
            account.sign_out()
        except OSError as e:
            self.win.toast(str(e), "problem")
        self._build_account()
        self.win.sidebar.show_who()

    # ------------------------------------------------------------------ Shortcuts
    def _build_shortcuts(self) -> None:
        from cuanto.ui.dialogs.shortcuts import ShortcutsList

        self._fill("shortcuts", ShortcutsList(self.win.menuBar()))

    # ------------------------------------------------------------------ Your Data
    def _build_data(self) -> None:
        w, lay = self._column()
        where = Section("Saved On This Computer")
        path = ElidedLabel(str(data_dir()))
        path.setObjectName("Muted")
        path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        where.add(path)
        show = QPushButton("Show Folder")
        show.clicked.connect(self.win.open_data_folder)
        back = QPushButton("Back Up…")
        back.clicked.connect(self.win.back_up)
        row = hbox(spacing=tokens.SPACE_2)
        row.addWidget(show)
        row.addWidget(back)
        row.addStretch(1)
        where.add(row)
        lay.addWidget(where)
        lay.addStretch(1)
        self._fill("data", w)
