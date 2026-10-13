"""The accent color you pick: every choice gets a full, readable set of shades; the choice is kept."""

from __future__ import annotations

import colorsys
import re

from cuanto.core import sample
from cuanto.core.store import Library, read_json
from cuanto.ui.style import tokens

COLOR = re.compile(r"^(#[0-9A-F]{6}|rgba\(\d+, \d+, \d+, [0-9.]+\))$")


def test_every_choice_has_every_shade_and_reads():
    keys = {k for k in tokens.DARK if k.startswith(("ACCENT", "DIVIDER", "CHIP")) or k == "ON_ACCENT"}
    for name, dark, light in tokens.ACCENTS.values():
        for base, scheme in ((dark, "dark"), (light, "light")):
            shades = tokens.accent_set(base, scheme)
            assert keys <= set(shades), name
            assert all(COLOR.match(v) for v in shades.values()), name
            assert tokens.contrast(shades["ON_ACCENT"], base) >= 3, (name, scheme)


def test_no_red_accent():
    for _name, dark, light in tokens.ACCENTS.values():
        for c in (dark, light):
            h, _l, sat = colorsys.rgb_to_hls(*(v / 255 for v in tokens._rgb(c)))
            assert sat < 0.25 or 18 <= h * 360 <= 340, c  # red means late, failed or delete


def test_use_switches_and_comes_back():
    try:
        tokens.use("dark", "green")
        assert tokens.ACCENTS["green"][1] == tokens.ACCENT and tokens.ON_ACCENT == tokens.DARK_ON_ACCENT
        tokens.use("light")  # keeps the accent
        assert tokens.ACCENTS["green"][2] == tokens.ACCENT
        tokens.use("dark", "")  # Cuánto's own: the hand-set shades, exactly
        assert tokens.DARK["ACCENT"] == tokens.ACCENT and tokens.DARK["DIVIDER"] == tokens.DIVIDER
        tokens.use("dark", "blue")  # white reads on the blue, so its words are white
        assert tokens.ACCENT == "#4A90F7" and tokens.ON_ACCENT == "#FFFFFF"
        tokens.use("dark", "no-such-color")
        assert tokens.ACCENT_KEY == tokens.APP_ACCENT
    finally:
        tokens.use("dark", "")


def test_picking_an_accent_in_settings(qapp, data_folder):
    from cuanto.app import set_appearance
    from cuanto.ui.dialogs.settings import SettingsDialog
    from cuanto.ui.window.main_window import MainWindow

    win = MainWindow(sample.fill(Library(data_folder).load()))
    win.show()
    try:
        d = SettingsDialog(win.lib, win, "general")
        assert d.accent.current == tokens.APP_ACCENT
        d.accent._pick("purple")
        assert tokens.ACCENTS["purple"][1] == tokens.ACCENT
        assert tokens.ACCENTS["purple"][1] in qapp.styleSheet()
        assert read_json(data_folder / "settings.json", {}).get("accent") == "purple"
        d.accent._pick(tokens.APP_ACCENT)
        assert read_json(data_folder / "settings.json", {}).get("accent") == ""
        assert tokens.DARK["ACCENT"] == tokens.ACCENT
        d.close()
    finally:
        set_appearance(qapp, "dark", "")
        win.close()
