"""Bringing budgets, lines, rates, a schedule and crew in (CSV, JSON) and sending budgets out (Excel, JSON),
and backing everything up.

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog

from cuanto.core import dates, exchange, sheets, templates
from cuanto.core.fileutil import zip_folder
from cuanto.core.log import get_logger
from cuanto.core.paths import data_dir, documents_dir
from cuanto.core.store import write_json
from cuanto.ui.dialogs.common import notice

log = get_logger(__name__)


def file_name(text: str) -> str:
    """Something safe to name a file after ("The Long Night" stays; "a/b:c" becomes "a-b-c")."""
    import re

    out = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "-", text).strip(" .-")
    return out[:120] or "Budget"


class TransferMixin:
    # ------------------------------------------------------------------ in
    def import_any(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import a Budget", str(Path.home()), "Budgets (*.csv *.json);;CSV (*.csv);;JSON (*.json)"
        )
        if path:
            self.import_file(Path(path))

    def import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import Budget Lines", str(Path.home()), "CSV (*.csv)")
        if path:
            self.import_file(Path(path))

    def import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import JSON", str(Path.home()), "JSON (*.json)")
        if path:
            self.import_file(Path(path))

    def import_file(self, path: Path) -> None:
        """A CSV (lines: into the open budget, or a new one from All Budgets) or a JSON file (a whole budget,
        or rates, a schedule and crew from another tool)."""
        self.flush()
        try:
            if path.suffix.lower() == ".json":
                self._import_json(path)
            else:
                self._import_csv(path)
        except (sheets.SheetError, exchange.ExchangeError) as e:
            notice(self, "Couldn't Import It", str(e))
        except OSError:
            log.warning("import failed", exc_info=True)
            notice(
                self, "Couldn't Open It", f"Cuánto couldn't read {path.name}. Check that it's still there."
            )

    def _import_csv(self, path: Path) -> None:
        got = sheets.read_csv(path)
        into_open = self.budget is not None and self.view_key != "budgets"
        if into_open:
            b = self.budget
            self.lib.snapshot(b.id, "import-csv")
        else:
            b = self.lib.add_budget(templates.build("blank", path.stem))
            self.set_budget(b)
        n = sheets.merge_into(b, got)
        self._dirty.add(b.id)
        self.flush()
        log.info("imported %d lines from a CSV", n)
        first = next((c.section for c in b.categories for a in c.accounts if a.lines), "production")
        self.go(f"sec:{first}" if not into_open else self.view_key)
        skipped = f" Skipped {got.skipped} rows." if got.skipped else ""
        self.toast(f"Brought in {n:,} line{'s' if n != 1 else ''}.{skipped}", "done")

    def _import_json(self, path: Path) -> None:
        data = exchange.read(path)
        if exchange.is_budget(data):
            b = exchange.budget_from(data, set(self.lib.budgets))
            self.lib.add_budget(b)
            self.go(f"budget:{b.id}")
            self.toast(f"Brought in {b.name or 'the budget'}.", "done")
            return
        b = self.budget
        if b is not None:
            self.lib.snapshot(b.id, "import-json")
        rep = exchange.apply(data, self.lib.rates, b)
        self.lib.save_rates()
        if b is not None:
            self._dirty.add(b.id)
        self.flush()
        self.refresh()
        words = rep.words()
        if b is None and rep.skipped:
            words += " Open a budget to bring in its schedule and crew."
        self.toast(
            words,
            "done"
            if rep.rates_added + rep.rates_updated + rep.globals_set + rep.lines_added + rep.lines_updated
            else "",
        )

    # ------------------------------------------------------------------ out
    def _export_folder(self) -> Path:
        saved = self.lib.settings.get("export_dir")
        if isinstance(saved, str) and Path(saved).is_dir():
            return Path(saved)
        return documents_dir()

    def _ask_save(self, title: str, name: str, suffix: str, kinds: str, parent=None) -> Path | None:
        folder = self._export_folder()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            folder = Path.home()
        path, _ = QFileDialog.getSaveFileName(
            parent or self, title, str(folder / f"{file_name(name)}{suffix}"), kinds
        )
        if not path:
            return None
        p = Path(path)
        if p.suffix.lower() != suffix:
            p = p.with_name(p.name + suffix)
        self.lib.settings["export_dir"] = str(p.parent)
        return p

    def export_xlsx(self) -> None:
        b = self.budget
        if b is None:
            self.toast("Open a budget first.")
            return
        self.flush()
        path = self._ask_save("Export Excel", b.name or "Budget", ".xlsx", "Excel (*.xlsx)")
        if path is None:
            return
        p = self.lib.profile(b)
        try:
            sheets.write_xlsx(b, path, p.name if p else "")
        except OSError:
            log.warning("Excel export failed", exc_info=True)
            self.toast(f"Couldn't save {path.name}. Check that the folder is writable.", "problem")
            return
        self.last_export = path
        self.toast(f"Saved {path.name}.", "done")

    def export_json(self, budget_id: str = "") -> None:
        """A budget and every number in it, in the exchange format (for invoicing, a cost report…)."""
        b = self.lib.budgets.get(budget_id) if budget_id else self.budget
        if b is None:
            self.toast("Open a budget first.")
            return
        self.flush()
        path = self._ask_save("Export JSON", b.name or "Budget", ".json", "JSON (*.json)")
        if path is None:
            return
        try:
            write_json(path, exchange.export_budget(b))
        except OSError:
            log.warning("JSON export failed", exc_info=True)
            self.toast(f"Couldn't save {path.name}. Check that the folder is writable.", "problem")
            return
        self.last_export = path
        self.toast(f"Saved {path.name}.", "done")

    def back_up(self) -> None:
        """Everything in the data folder, zipped, where you choose."""
        self.flush()
        self.lib.save_settings()
        name = f"Cuanto Backup {dates.iso(dates.today())}"
        path = self._ask_save("Back Up", name, ".zip", "Zip (*.zip)")
        if path is None:
            return
        try:
            n = zip_folder(data_dir(), path, skip=("logs", "ui"))
        except OSError:
            log.warning("backup failed", exc_info=True)
            self.toast(f"Couldn't save {path.name}. Check that the folder is writable.", "problem")
            return
        self.toast(f"Backed up {n:,} files to {path.name}.", "done")

    def open_data_folder(self) -> None:
        folder = data_dir()
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
