"""The page window: a budget's top sheet and detail, as they print; Save PDF, PNG, Print, copy as text.

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication

from cuanto.core import document
from cuanto.core.fileutil import reveal
from cuanto.core.log import get_logger
from cuanto.core.looks import DEFAULT_COLOR, palette
from cuanto.doc import export, render
from cuanto.ui.dialogs.preview import PageDialog

log = get_logger(__name__)


class PagesMixin:
    def show_pages(self, which: str = "") -> None:
        """Open the open budget's top sheet and detail in their own window."""
        self.flush()
        b = self.budget
        if b is None:
            self.toast("Open a budget first.")
            return
        d = PageDialog(b.name or "Untitled Budget", self)
        self.page = d
        panel = d.panel
        saved = self.lib.settings.get("page_doc", "both")
        current = which or (saved if saved in {k for k, _l in document.PAGES} else "both")
        panel.set_docs(document.PAGES, current)
        panel.set_dark(bool(self.lib.settings.get("dark_preview", False)))
        panel.save_pdf.connect(self.save_pdf)
        panel.print_wanted.connect(self.print_pages)
        panel.save_png.connect(self.save_png)
        panel.copy_text.connect(self.copy_text)
        panel.open_folder.connect(self.open_folder)
        panel.show_file.connect(lambda: self.last_export and reveal(self.last_export))
        panel.dark_changed.connect(self._dark_changed)
        panel.doc_changed.connect(self._doc_changed)
        self.redraw()
        d.exec()
        self.page = None

    def _doc_changed(self, key: str) -> None:
        self.lib.settings["page_doc"] = key
        self.redraw()

    def page_list(self, dark: bool = False, which: str = "") -> list[render.Page]:
        """The pages, laid out. `dark` only ever for the window's Dark Page: exports stay white."""
        b = self.budget
        if b is None:
            return []
        if not which:
            which = self.page.panel.current_doc() if self.page is not None else "both"
        p = self.lib.profile(b)
        from cuanto.ui.dialogs.profile import logo_path

        logo = logo_path(p.logo) if p is not None else None
        views = document.build(b, p, which)
        return render.layout_all(views, palette(p.color if p else DEFAULT_COLOR, dark), logo)

    def redraw(self) -> None:
        if self.page is None:
            return
        panel = self.page.panel
        pages = self.page_list(dark=panel.dark)
        if pages:
            panel.set_pages(pages)
        else:
            panel.clear("Nothing to show.")

    def _stem(self) -> str:
        from cuanto.ui.window.transfer import file_name

        b = self.budget
        which = self.page.panel.current_doc() if self.page is not None else "both"
        words = {"topsheet": "Top Sheet", "detail": "Detail", "both": "Budget"}[which]
        return file_name(f"{b.name or 'Untitled'} {words}" if b is not None else words)

    def _exported(self, path: Path) -> None:
        self.last_export = path
        if self.page is not None:
            self.page.panel.saved_hint(path.name)

    def save_pdf(self) -> None:
        pages = self.page_list()
        if not pages:
            return
        path = self._ask_save("Save PDF", self._stem(), ".pdf", "PDF (*.pdf)", self.page)
        if path is None:
            return
        try:
            export.to_pdf(pages, path, title=self.budget.name if self.budget else "")
        except OSError as e:
            log.warning("PDF not saved", exc_info=True)
            self.toast(str(e) or "Couldn't save the PDF.", "problem")
            return
        self._exported(path)

    def save_png(self) -> None:
        pages = self.page_list()
        if not pages:
            return
        path = self._ask_save("Save as PNG", self._stem(), ".png", "PNG picture (*.png)", self.page)
        if path is None:
            return
        try:
            files = export.to_png(pages, path)
        except OSError as e:
            log.warning("PNG not saved", exc_info=True)
            self.toast(str(e) or "Couldn't save the picture.", "problem")
            return
        self._exported(files[0])

    def print_pages(self) -> None:
        pages = self.page_list()
        if not pages:
            return
        try:
            from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        except ImportError:
            self.toast("Printing isn't available here. Save a PDF and print that.", "problem")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setDocName(self._stem())
        dlg = QPrintDialog(printer, self.page or self)
        if dlg.exec() != QPrintDialog.DialogCode.Accepted:
            return
        try:
            export.print_pages(printer, pages)
        except OSError as e:
            log.warning("print failed", exc_info=True)
            self.toast(str(e), "problem")

    def copy_text(self) -> None:
        b = self.budget
        if b is not None:
            QGuiApplication.clipboard().setText(document.summary_text(b, self.lib.profile(b)))
            self.toast("Copied the top sheet.", "done")

    def open_folder(self) -> None:
        folder = self._export_folder()
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _dark_changed(self, on: bool) -> None:
        self.lib.settings["dark_preview"] = on
        self.redraw()
