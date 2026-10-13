"""Every icon the code names exists (a missing one only shows up as a crash when its button is drawn)."""

from __future__ import annotations

import re
from pathlib import Path

from cuanto.ui.style import theme

ROOT = Path(__file__).resolve().parent.parent / "cuanto"
CALLS = re.compile(
    r'(?:icon|menu_icon|IconLabel|circle_button|icon_button|header_icon|set_icon)\(\s*"([a-z0-9-]+)"'
)


def test_every_named_icon_exists():
    names = set()
    for f in ROOT.rglob("*.py"):
        text = f.read_text()
        names |= set(CALLS.findall(text))
    missing = sorted(n for n in names if n not in theme._SVG)
    assert not missing, missing


def test_settings_and_sidebar_icons_exist():
    from cuanto.ui.dialogs.settings import PANES
    from cuanto.ui.window.common import PLACE_ICONS

    names = {icon for _k, _l, icon in PANES} | set(PLACE_ICONS.values())
    assert names and all(n in theme._SVG for n in names), names


def test_the_shared_icons_are_all_here():
    shared = ("plus", "x", "more", "search", "filter", "share", "cog", "user", "key", "keyboard", "message",
              "calendar", "clock", "box", "case", "tag", "camera", "image", "link", "check", "trash", "copy",
              "edit", "folder", "receipt", "chevron", "updown", "alert", "moon", "assistant")  # fmt: skip
    assert all(n in theme._SVG for n in shared)
