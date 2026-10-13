"""Screenshots of every screen without a display, for checking UI changes (light and dark, and in a light
accent, to catch anything that assumed white on the accent).

    QT_QPA_PLATFORM=offscreen python tests/screenshot.py OUTDIR [--look light|dark] [--accent yellow]

Uses a throwaway data folder with the made-up sample budgets, never your real ones.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication

from cuanto.app import set_appearance, setup_app
from cuanto.core import sample
from cuanto.core.paths import use_data_dir
from cuanto.core.store import Library

SIZE = (1600, 1000)
SMALL = (1280, 760)


def wait(ms: int = 400) -> None:
    from PySide6.QtCore import QEventLoop, QTimer

    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def shot(w, path: Path) -> None:
    wait()
    w.grab().save(str(path))
    print("wrote", path)


def main(out: Path, look: str = "dark", accent: str = "") -> int:
    out.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv[:1])
    tmp = Path(tempfile.mkdtemp(prefix="cuanto-shots-"))
    use_data_dir(tmp)
    setup_app(app)
    set_appearance(app, look, accent)
    from cuanto.ui.dialogs.preview import PageDialog
    from cuanto.ui.window.main_window import MainWindow

    def window(lib, size=SIZE):
        w = MainWindow(lib)
        w._restored = True  # a fixed size, not the screen's
        w.resize(*size)
        w.show()
        return w

    w = window(Library(tmp).load())
    shot(w, out / "01-first-launch.png")
    w.close()

    lib = sample.fill(Library(tmp).load())
    feature = next(b for b in lib.budgets.values() if b.kind == "feature")
    w = window(lib)
    w.go("budgets")
    w.open("budget", feature.id)
    shot(w, out / "02-all-budgets.png")
    w.go(f"budget:{feature.id}")
    shot(w, out / "03-top-sheet.png")
    w.open("category", feature.categories[16].id)
    shot(w, out / "04-top-sheet-category.png")
    w.go("sec:production")
    camera = next(c for c in feature.categories if c.name == "Camera")
    dp = camera.accounts[0].lines[0]
    w.open("line", dp.id)
    shot(w, out / "05-production-line.png")
    w.open("account", camera.accounts[0].id)
    shot(w, out / "06-account.png")
    w.go("sec:atl")
    w.deselect()
    shot(w, out / "07-above-the-line.png")
    w.go("globals")
    w.open("global", feature.globals[1].id)
    shot(w, out / "08-globals.png")
    w.go("fringes")
    w.open("fringe", feature.fringes[0].id)
    shot(w, out / "09-fringes.png")
    w.go("top")
    w.open("adjustment", feature.adjustments[0].id)
    shot(w, out / "10-fee.png")
    w.go("rates")
    w.open("rate", next(iter(lib.rates)))
    shot(w, out / "11-rate-library.png")
    for name, menu in (("12-filter-menu", w.filter_btn.m), ("13-share-menu", w.btn_share.menu())):
        menu.popup(w.mapToGlobal(w.rect().center()))
        shot(menu, out / f"{name}.png")
        menu.close()
    w.go("sec:production")
    w.search.setText("camera")
    shot(w, out / "14-search.png")
    w.search.clear()
    w.close()

    w = window(lib, SMALL)
    w.go("sec:production")
    w.open("line", dp.id)
    shot(w, out / "15-small-window.png")

    from cuanto.core import templates
    from cuanto.ui.dialogs.common import Alert
    from cuanto.ui.dialogs.pickers import NewBudgetDialog, RatePicker, SaveTemplateDialog
    from cuanto.ui.dialogs.settings import SettingsDialog

    for name, d in (
        ("16-alert", Alert(w, "Delete 2701 Camera Crew?", "Its 4 lines go too.", "Delete", "Cancel", True)),
        ("17-new-budget", NewBudgetDialog(w)),
        ("18-rate-picker", RatePicker(lib.ordered_rates(), w, "")),
        ("18-save-as-template", SaveTemplateDialog(w, feature.name)),
    ):
        d.show()
        shot(d, out / f"{name}.png")
        d.close()
    lib.add_template(templates.from_budget(feature, "Our Feature"))
    for pane in ("general", "profiles", "templates", "shortcuts", "data"):
        d = SettingsDialog(w.lib, w, pane)
        d.show()
        shot(d, out / f"19-settings-{pane}.png")
        d.close()

    names = iter(["20-pages-both.png", "21-pages-detail.png"])

    def page_shot(d):
        d.show()
        shot(d, out / next(names))
        d.close()
        return 0

    PageDialog.exec = page_shot
    w.show_pages("both")
    w.show_pages("detail")
    w.close()
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--look", choices=("light", "dark"), default="dark")
    ap.add_argument("--accent", default="")
    a = ap.parse_args()
    sys.exit(main(Path(a.out), a.look, a.accent))
