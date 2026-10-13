"""Turn laid-out pages into a PDF, PNG pictures, a printout, or a picture for the preview.

Files are written to a hidden temp file in the same folder and moved into place only when complete,
so a failed export never leaves a broken file (or replaces a good one).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from PySide6.QtCore import QMarginsF, QSizeF
from PySide6.QtGui import QImage, QPageLayout, QPageSize, QPainter, QPdfWriter

from cuanto import APP_NAME, __version__
from cuanto.core.log import get_logger
from cuanto.doc.render import Page, paint

log = get_logger(__name__)


def _temp_beside(path: Path, suffix: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=suffix, dir=path.parent)
    os.close(fd)
    # mkstemp makes the file private to you; an exported page gets normal file permissions
    mask = os.umask(0)
    os.umask(mask)
    os.chmod(tmp, 0o666 & ~mask)
    return Path(tmp)


def page_size(page: Page) -> QPageSize:
    w, h = page.size
    return QPageSize(QSizeF(w, h), QPageSize.Unit.Point, "", QPageSize.SizeMatchPolicy.FuzzyMatch)


def to_pdf(pages: list[Page], path: Path, title: str = "") -> Path:
    """Write every page into one PDF (fonts embedded, text selectable)."""
    tmp = _temp_beside(path, ".pdf")
    try:
        w = QPdfWriter(str(tmp))
        w.setResolution(72)  # 1 unit = 1 point
        w.setPageSize(page_size(pages[0]))
        w.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Point)
        w.setTitle(title)
        w.setCreator(f"{APP_NAME} {__version__}")
        p = QPainter()
        if not p.begin(w):
            raise OSError(f"Couldn't write {path.name}. Check that the folder is writable.")
        for i, page in enumerate(pages):
            if i:
                w.setPageSize(page_size(page))
                w.newPage()
            paint(p, page)
        p.end()
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    log.info("saved PDF %s (%d pages)", path, len(pages))
    return path


def image(page: Page, scale: float) -> QImage:
    """One page as a picture, `scale` pixels per point."""
    w, h = page.size
    img = QImage(
        max(1, round(w * scale)),
        max(1, round(h * scale)),
        QImage.Format.Format_ARGB32_Premultiplied,
    )
    dpm = round(72 / 0.0254)
    img.setDotsPerMeterX(dpm)
    img.setDotsPerMeterY(dpm)
    img.fill(0xFFFFFFFF)
    p = QPainter(img)
    p.scale(scale, scale)
    paint(p, page)
    p.end()
    return img


def to_png(pages: list[Page], path: Path, dpi: int = 200) -> list[Path]:
    """One PNG per page (…-2.png, …-3.png for longer invoices)."""
    out = []
    for i, page in enumerate(pages):
        target = path if i == 0 else path.with_name(f"{path.stem}-{i + 1}{path.suffix}")
        img = image(page, dpi / 72)
        dpm = round(dpi / 0.0254)
        img.setDotsPerMeterX(dpm)
        img.setDotsPerMeterY(dpm)
        tmp = _temp_beside(target, ".png")
        try:
            if not img.save(str(tmp), "PNG"):
                raise OSError(f"Couldn't write {target.name}. Check that the folder is writable.")
            os.replace(tmp, target)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
        out.append(target)
    log.info("saved PNG %s (%d pages)", path, len(pages))
    return out


def print_pages(printer, pages: list[Page]) -> None:
    """Print on a QPrinter the person already set up in the print dialog."""
    printer.setPageSize(page_size(pages[0]))
    printer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Point)
    printer.setFullPage(True)
    p = QPainter()
    if not p.begin(printer):
        raise OSError("The printer couldn't start.")
    for i, page in enumerate(pages):
        if i:
            printer.newPage()
        dpi = printer.resolution()
        p.save()
        p.scale(dpi / 72, dpi / 72)
        paint(p, page)
        p.restore()
    p.end()
