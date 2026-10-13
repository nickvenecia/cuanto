"""Lay out a budget's pages (the top sheet, the detail) and paint them on any device.

layout() works in points on the paper (Letter is 612 × 792) and returns a list of Pages, each a list of
simple steps (text in a box, a filled box, a line, the logo). paint() replays one page on a QPainter
scaled so one point = one page unit; the preview, the PDF, the PNG and the printer all use the same steps.
Headings stay with the row under them, table headers repeat on a new page, and the totals stay together.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter, QPen
from PySide6.QtSvg import QSvgRenderer

from cuanto.core.document import DocView, Row, Table
from cuanto.core.looks import FONT, MONO, WHITE_PAPER, Palette
from cuanto.doc.fonts import FontSpec, make, metrics

LEFT = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
RIGHT = int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
CENTER = int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
WRAP = int(Qt.TextFlag.TextWordWrap)
ALIGN = {"left": LEFT, "right": RIGHT, "center": CENTER}

LETTER = (612.0, 792.0)
A4 = (595.0, 842.0)
MARGIN = 44.0
FOOTER_H = 18.0
LABEL_SPACING = 0.14  # letter-spacing of the small capital labels
INDENT = 12.0  # lines under their account
LOGO_H = 40.0


# ---------------------------------------------------------------------------- drawing steps
@dataclass
class Text:
    rect: QRectF
    text: str
    font: FontSpec
    color: str
    flags: int = LEFT


@dataclass
class Fill:
    rect: QRectF
    color: str
    radius: float = 0.0


@dataclass
class Line:
    a: QPointF
    b: QPointF
    width: float
    color: str


@dataclass
class Box:
    rect: QRectF
    color: str
    width: float = 0.7
    radius: float = 1.2


@dataclass
class Logo:
    rect: QRectF
    path: Path


@dataclass
class Page:
    size: tuple[float, float]
    steps: list = field(default_factory=list)
    paper: str = WHITE_PAPER


# ---------------------------------------------------------------------------- logo files
def logo_size(path: Path) -> tuple[float, float] | None:
    if not path.is_file():
        return None
    if path.suffix.lower() == ".svg":
        r = QSvgRenderer(str(path))
        if not r.isValid():
            return None
        s = r.defaultSize()
        return (float(s.width()), float(s.height())) if s.width() > 0 and s.height() > 0 else (1.0, 1.0)
    s = QImageReader(str(path)).size()
    return (float(s.width()), float(s.height())) if s.width() > 0 and s.height() > 0 else None


def _draw_logo(p: QPainter, step: Logo) -> None:
    if step.path.suffix.lower() == ".svg":
        r = QSvgRenderer(str(step.path))
        if r.isValid():
            r.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
            r.render(p, step.rect)
        return
    img = QImage(str(step.path))
    if not img.isNull():
        p.drawImage(step.rect, img)


# ---------------------------------------------------------------------------- measuring
def text_h(text: str, spec: FontSpec, width: float) -> float:
    if not text:
        return 0.0
    fm = metrics(spec)
    r = fm.boundingRect(QRectF(0, 0, max(1.0, width), 1e6), LEFT | WRAP, text)
    return max(r.height(), fm.lineSpacing())


def text_w(text: str, spec: FontSpec) -> float:
    return metrics(spec).horizontalAdvance(text)


def fit_size(text: str, spec_at, start: float, smallest: float, room: float) -> float:
    size = start
    while size > smallest and text_w(text, spec_at(size)) > room:
        size -= 0.5
    return size


class _Pages:
    """A cursor that adds steps to the current page and starts new pages."""

    def __init__(self, size: tuple[float, float], paper: str):
        self.size = size
        self.paper = paper
        self.pages: list[Page] = [Page(size, paper=paper)]
        self.y = MARGIN

    @property
    def steps(self) -> list:
        return self.pages[-1].steps

    @property
    def bottom(self) -> float:
        return self.size[1] - MARGIN - FOOTER_H

    def fits(self, h: float) -> bool:
        return self.y + h <= self.bottom

    def new_page(self) -> None:
        self.pages.append(Page(self.size, paper=self.paper))
        self.y = MARGIN

    def ensure(self, h: float) -> bool:
        """Start a new page unless h more points fit. Returns True when it did."""
        if not self.fits(h):
            self.new_page()
            return True
        return False

    def text(self, x, y, w, text, spec, color, flags=LEFT, wrap=True) -> float:
        if not text:
            return 0.0
        h = text_h(text, spec, w) if wrap else metrics(spec).lineSpacing()
        self.steps.append(Text(QRectF(x, y, w, h + 1), text, spec, color, flags | (WRAP if wrap else 0)))
        return h

    def line(self, x1, y, x2, width, color) -> None:
        self.steps.append(Line(QPointF(x1, y), QPointF(x2, y), width, color))


# ---------------------------------------------------------------------------- the layout
SEMIBOLD, BOLD = 600, 700  # the paper's two heavier weights
TIGHT = -0.01  # letter spacing for big figures and names


class _Fonts:
    """Every type style on the paper (one place, like the app's tokens)."""

    def __init__(self):
        self.name = lambda pt: FontSpec(FONT, pt, BOLD, TIGHT)  # names and big figures, sized to fit
        self.title = FontSpec(FONT, 11, SEMIBOLD)
        self.body = FontSpec(FONT, 8.6)
        self.body_strong = FontSpec(FONT, 8.6, SEMIBOLD)
        self.small = FontSpec(FONT, 7.6)
        self.sub = FontSpec(FONT, 8.0)
        self.label = FontSpec(FONT, 6.4, SEMIBOLD, LABEL_SPACING)
        self.heading = FontSpec(FONT, 10.5, BOLD)
        self.mono = FontSpec(MONO, 7.2)
        self.mono_cell = FontSpec(MONO, 7.6)
        self.mono_strong = FontSpec(MONO, 7.6, SEMIBOLD)
        self.total = FontSpec(FONT, 11, BOLD)
        self.para = FontSpec(FONT, 7.8)
        self.para_lead = FontSpec(FONT, 7.8, SEMIBOLD)


def layout(
    v: DocView, pal: Palette, logo: Path | None = None, size: tuple[float, float] = LETTER
) -> list[Page]:
    W, _H = size
    cw = W - 2 * MARGIN
    x0 = MARGIN
    F = _Fonts()
    out = _Pages(size, pal.paper)
    _header(out, v, pal, F, logo, x0, cw)
    if v.strip:
        _strip(out, v, pal, F, x0, cw)
    if v.blocks:
        _blocks(out, v, pal, F, x0, cw)
    if v.table is not None and v.table.rows:
        _table(out, v.table, pal, F, x0, cw)
    if v.totals:
        _totals(out, v, pal, F, x0, cw)
    if v.paragraphs:
        _paragraphs(out, v, pal, F, x0, cw)
    if v.note:
        out.y += 12
        out.ensure(14)
        out.y += out.text(x0, out.y, cw, v.note, F.small, pal.soft)
    _footers(out, v, pal, F, x0, cw)
    return out.pages


def layout_all(
    views: list[DocView], pal: Palette, logo: Path | None = None, size: tuple[float, float] = LETTER
) -> list[Page]:
    """Several documents one after another (the top sheet, then the detail), each starting a page."""
    pages: list[Page] = []
    for v in views:
        pages += layout(v, pal, logo, size)
    return pages


def _header(
    out: _Pages, v: DocView, pal: Palette, F: _Fonts, logo: Path | None, x0: float, cw: float
) -> None:
    right_w = 210.0
    left_w = cw - right_w - 20
    y = out.y
    x = x0
    dims = logo_size(logo) if logo else None
    if dims:
        lh = LOGO_H
        lw = min(lh * dims[0] / dims[1], left_w * 0.45)
        lh = lw * dims[1] / dims[0]
        out.steps.append(Logo(QRectF(x, y, lw, lh), logo))
        x += lw + 12
    nw = x0 + left_w - x
    name = v.business or "Your Production Company"
    pt = fit_size(name, F.name, 20, 12, nw - 6)
    spec = F.name(pt)
    ly = y
    ly += out.text(x, ly, nw, name, spec, pal.ink, wrap=text_w(name, spec) > nw - 6)
    if v.tagline:
        ly += 2
        ly += out.text(x, ly, nw, v.tagline.upper(), F.label, pal.soft)
    ly += 4
    for c in v.contact:
        ly += out.text(x, ly, nw, c, F.small, pal.soft)
    if dims:
        ly = max(ly, y + LOGO_H)

    rx = x0 + cw - right_w
    ry = y
    ry += out.text(rx, ry, right_w, v.title, F.title, pal.ink, RIGHT)
    ry += 6
    if v.big_label:
        ry += out.text(rx, ry, right_w, v.big_label.upper(), F.label, pal.soft, RIGHT)
        ry += 1
    if v.big_value:
        bpt = fit_size(v.big_value, F.name, 22, 14, right_w)
        ry += out.text(rx, ry, right_w, v.big_value, F.name(bpt), pal.accent, RIGHT, wrap=False)
    if v.big_sub:
        ry += 1
        ry += out.text(rx, ry, right_w, v.big_sub, F.small, pal.soft, RIGHT)
    out.y = max(ly, ry) + 16


def _strip(out: _Pages, v: DocView, pal: Palette, F: _Fonts, x0: float, cw: float) -> None:
    out.line(x0, out.y, x0 + cw, 1.2, pal.ink)
    out.y += 7
    n = len(v.strip)
    w = cw / n
    h = 0.0
    for i, (k, val) in enumerate(v.strip):
        x = x0 + i * w + (8 if i else 0)
        cell_w = w - (16 if i else 8)
        hh = out.text(x, out.y, cell_w, k.upper(), F.label, pal.soft)
        hh += 2 + out.text(x, out.y + hh + 2, cell_w, val, F.body, pal.ink)
        h = max(h, hh)
        if i:
            out.steps.append(Line(QPointF(x0 + i * w, out.y), QPointF(x0 + i * w, out.y + 20), 0.6, pal.rule))
    out.y += max(h, 20) + 7
    out.line(x0, out.y, x0 + cw, 0.6, pal.rule)
    out.y += 16


def _blocks(out: _Pages, v: DocView, pal: Palette, F: _Fonts, x0: float, cw: float) -> None:
    n = len(v.blocks)
    gap = 18.0
    w = (cw - gap * (n - 1)) / max(1, n) if n < 3 else (cw - 2 * gap) / 3
    h = 0.0
    for i, (k, text) in enumerate(v.blocks):
        x = x0 + i * (w + gap)
        hh = out.text(x, out.y, w, k.upper(), F.label, pal.soft) + 3
        lines = text.split("\n")
        first, rest = lines[0], "\n".join(lines[1:])
        hh += out.text(x, out.y + hh, w, first, F.body_strong, pal.ink)
        if rest:
            hh += 1 + out.text(x, out.y + hh + 1, w, rest, F.body, pal.soft)
        h = max(h, hh)
    out.y += h + 20


def _col_x(t: Table, x0: float, cw: float) -> list[tuple[float, float]]:
    total = sum(c.width for c in t.cols) or 1
    xs, x = [], x0
    for c in t.cols:
        w = cw * c.width / total
        xs.append((x, w))
        x += w
    return xs


def _table_head(out: _Pages, t: Table, pal: Palette, F: _Fonts, x0: float, cw: float) -> None:
    xs = _col_x(t, x0, cw)
    for c, (x, w) in zip(t.cols, xs, strict=True):
        out.text(
            x, out.y, w - (6 if c.align == "left" else 0), c.title.upper(), F.label, pal.soft, ALIGN[c.align]
        )
    out.y += metrics(F.label).lineSpacing() + 5
    out.line(x0, out.y, x0 + cw, 0.9, pal.ink)
    out.y += 6


def _row_fonts(row: Row, F: _Fonts) -> tuple[FontSpec, FontSpec, FontSpec]:
    """(the name's font, the other cells', the code's) for a kind of row."""
    if row.kind == "section":
        return F.heading, F.body_strong, F.mono_strong
    if row.kind == "heading":
        return F.title, F.body_strong, F.mono_strong
    if row.kind in ("account", "subtotal"):
        return F.body_strong, F.body_strong, F.mono_strong
    if row.kind == "fringe":
        return F.small, F.small, F.mono_cell
    return F.body, F.body, F.mono_cell


SPACE_BEFORE = {"section": 10.0, "heading": 8.0, "account": 2.0}
PADDING = {"line": 6.0, "fringe": 5.0}  # under a row (8 for the bolder kinds)


def _row_height(row: Row, t: Table, xs, F: _Fonts) -> float:
    name_font, cell_font, mono = _row_fonts(row, F)
    h = 0.0
    for i, (c, (_x, w)) in enumerate(zip(t.cols, xs, strict=True)):
        text = row.cells[i] if i < len(row.cells) else ""
        if i == t.name_col:
            iw = w - INDENT * row.depth - 6
            hh = text_h(text, name_font, iw)
            if row.note:
                hh += 1 + text_h(row.note, F.small, iw)
        else:
            hh = text_h(text, mono if c.mono else cell_font, w - 6)
        h = max(h, hh)
    return h + PADDING.get(row.kind, 8.0)


def _table(out: _Pages, t: Table, pal: Palette, F: _Fonts, x0: float, cw: float) -> None:
    xs = _col_x(t, x0, cw)
    out.ensure(60)
    _table_head(out, t, pal, F, x0, cw)
    rows = t.rows
    for idx, row in enumerate(rows):
        h = _row_height(row, t, xs, F)
        space = SPACE_BEFORE.get(row.kind, 0.0) if idx else 0.0
        # keep headings (a section, a category, an account) with the first row under them
        need = space + h
        k = idx
        while rows[k].kind in ("section", "heading", "account") and k + 1 < len(rows):
            k += 1
            need += _row_height(rows[k], t, xs, F)
        if out.ensure(need):
            _table_head(out, t, pal, F, x0, cw)
            space = 0.0
        y = out.y + space
        name_font, cell_font, mono = _row_fonts(row, F)
        color = pal.soft if row.kind == "fringe" else pal.ink
        for i, (c, (x, w)) in enumerate(zip(t.cols, xs, strict=True)):
            text = row.cells[i] if i < len(row.cells) else ""
            if not text:
                continue
            if i == t.name_col:
                ix = x + INDENT * row.depth
                iw = w - INDENT * row.depth - 6
                tone = pal.accent if row.kind == "section" else color
                th = out.text(ix, y, iw, text, name_font, tone)
                if row.note:
                    out.text(ix, y + th + 1, iw, row.note, F.small, pal.faint)
            else:
                f = mono if c.mono else cell_font
                tone = (
                    pal.accent
                    if row.kind == "section" and c.align == "right"
                    else (pal.faint if c.mono else color)
                )
                out.text(
                    x,
                    y + (1 if row.kind == "section" else 0),
                    w - (6 if c.align == "left" else 0),
                    text,
                    f,
                    tone,
                    ALIGN[c.align],
                )
        out.y = y + h
        nxt = rows[idx + 1] if idx + 1 < len(rows) else None
        if row.kind == "section":
            out.line(x0, out.y - 3, x0 + cw, 0.9, pal.ink)
        elif row.kind == "heading":
            out.line(x0, out.y - 3, x0 + cw, 0.6, pal.rule)
        elif nxt is None or nxt.kind in ("section", "heading", "account"):
            out.line(x0, out.y - 4, x0 + cw, 0.5, pal.rule)
    out.y += 6


def _totals(out: _Pages, v: DocView, pal: Palette, F: _Fonts, x0: float, cw: float) -> None:
    w = 250.0
    x = x0 + cw - w
    rows = v.totals
    need = sum(metrics(F.total if s else F.body).lineSpacing() + 7 for _k, _v, s in rows) + 10
    out.ensure(need)
    out.y += 4
    for k, val, strong in rows:
        if strong:
            out.y += 2
            out.line(x, out.y, x + w, 1.0, pal.ink)
            out.y += 6
            out.text(x, out.y + 1, w * 0.6, k, F.body_strong, pal.ink)
            hh = out.text(x + w * 0.35, out.y, w * 0.65, val, F.total, pal.accent, RIGHT)
            out.y += hh + 6
            out.line(x, out.y - 2, x + w, 0.6, pal.rule)
            out.y += 4
        else:
            out.text(x, out.y, w * 0.65, k, F.body, pal.soft)
            hh = out.text(x + w * 0.4, out.y, w * 0.6, val, F.body, pal.ink, RIGHT)
            out.y += hh + 5


def _paragraphs(out: _Pages, v: DocView, pal: Palette, F: _Fonts, x0: float, cw: float) -> None:
    out.y += 14
    lead_w = 108.0
    gap = 14.0
    body_w = cw - lead_w - gap
    first = True
    for para in v.paragraphs:
        lead, body = "", para
        head, dot, rest = para.partition(". ")
        if dot and len(head) <= 32 and "\n" not in head:
            lead, body = head, rest
        h = max(text_h(lead, F.para_lead, lead_w), text_h(body, F.para, body_w))
        title_h = metrics(F.label).lineSpacing() + 8 if first else 0
        if out.ensure(h + title_h + 6) or first:
            if v.paragraphs_title:
                out.line(x0, out.y, x0 + cw, 0.9, pal.ink)
                out.y += 6
                out.text(x0, out.y, cw, v.paragraphs_title.upper(), F.label, pal.soft)
                out.y += metrics(F.label).lineSpacing() + 6
            first = False
        if lead:
            out.text(x0, out.y, lead_w, lead, F.para_lead, pal.ink)
        out.text(x0 + (lead_w + gap if lead else 0), out.y, body_w if lead else cw, body, F.para, pal.soft)
        out.y += h + 6


def _footers(out: _Pages, v: DocView, pal: Palette, F: _Fonts, x0: float, cw: float) -> None:
    n = len(out.pages)
    _W, H = out.size
    for i, page in enumerate(out.pages):
        y = H - MARGIN + 4
        page.steps.append(Line(QPointF(x0, y - 6), QPointF(x0 + cw, y - 6), 0.5, pal.rule))
        left = "  ·  ".join(x for x in (v.footer, v.title) if x)
        page.steps.append(Text(QRectF(x0, y, cw * 0.7, 12), left, F.small, pal.faint, LEFT))
        page.steps.append(
            Text(QRectF(x0 + cw * 0.5, y, cw * 0.5, 12), f"Page {i + 1} of {n}", F.small, pal.faint, RIGHT)
        )


# ---------------------------------------------------------------------------- painting
def paint(p: QPainter, page: Page) -> None:
    W, H = page.size
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.fillRect(QRectF(0, 0, W, H), QColor(page.paper))
    dev = p.device()
    for s in page.steps:
        if isinstance(s, Text):
            p.setFont(make(s.font, dev))
            p.setPen(QColor(s.color))
            p.drawText(s.rect, s.flags, s.text)
        elif isinstance(s, Fill):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(s.color))
            if s.radius:
                p.drawRoundedRect(s.rect, s.radius, s.radius)
            else:
                p.drawRect(s.rect)
        elif isinstance(s, Line):
            pen = QPen(QColor(s.color), s.width)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.drawLine(s.a, s.b)
        elif isinstance(s, Box):
            p.setPen(QPen(QColor(s.color), s.width))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(s.rect, s.radius, s.radius)
        elif isinstance(s, Logo):
            _draw_logo(p, s)
    p.restore()
