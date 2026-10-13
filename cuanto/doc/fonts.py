"""The paper's fonts: loading the bundled ones, and making a QFont that measures the same everywhere.

Sizes on the page are in points. A QFont's point size is turned into pixels using the device's
dots per inch, and the painter's scale is applied on top of that, so size_for() divides the dpi
back out: a 10 pt line is 10 page units on screen, in a PDF and on a printer alike.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from PySide6.QtGui import QFont, QFontDatabase, QFontMetricsF, QImage, QPaintDevice

from cuanto.core.looks import FONT as FALLBACK_FONT
from cuanto.core.paths import ASSETS

FONT_DIR = ASSETS / "fonts"

# Some faces look smaller or bigger than others at the same point size.
SCALE = {"IBM Plex Mono": 0.94}

_loaded: set[str] = set()


def load_bundled() -> set[str]:
    """Register every font in assets/fonts with Qt (once). Returns the families found."""
    if _loaded:
        return set(_loaded)
    for f in sorted(FONT_DIR.glob("*")):
        if f.suffix.lower() not in (".ttf", ".otf"):
            continue
        fid = QFontDatabase.addApplicationFont(str(f))
        if fid >= 0:
            _loaded.update(QFontDatabase.applicationFontFamilies(fid))
    return set(_loaded)


def installed_families() -> set[str]:
    load_bundled()
    return set(QFontDatabase.families())


@dataclass(frozen=True)
class FontSpec:
    family: str
    size: float  # points
    weight: int = 400
    spacing: float = 0.0  # extra space between letters, as a fraction of the size (0.12 = small caps feel)

    def scaled(self) -> float:
        return self.size * SCALE.get(self.family, 1.0)


def make(spec: FontSpec, device: QPaintDevice) -> QFont:
    """A QFont for this device whose size, in page units, is spec.size (see the module note)."""
    f = QFont(spec.family if spec.family else FALLBACK_FONT)
    f.setFamilies([spec.family or FALLBACK_FONT, FALLBACK_FONT])
    dpi = device.logicalDpiY() or 72
    size = spec.scaled()
    f.setPointSizeF(size * 72.0 / dpi)
    f.setWeight(QFont.Weight(spec.weight))
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    f.setKerning(True)
    if spec.spacing:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, size * spec.spacing)
    return f


@lru_cache(maxsize=1)
def _measure_device() -> QImage:
    img = QImage(4, 4, QImage.Format.Format_ARGB32)
    dpm = round(72 / 0.0254)
    img.setDotsPerMeterX(dpm)
    img.setDotsPerMeterY(dpm)
    return img


@lru_cache(maxsize=256)
def metrics(spec: FontSpec) -> QFontMetricsF:
    """Measurements in page units (points), the same for every device."""
    dev = _measure_device()
    return QFontMetricsF(make(spec, dev), dev)
