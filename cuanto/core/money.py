"""Amounts in exact decimals (never floats, so cents always add up)."""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")
ZERO = Decimal(0)
LIMIT = Decimal("1e12")  # a trillion: anything bigger is a typo, and too big to round to the cent
MINUS = "−"  # a real minus sign, the width of a digit


def parse(text: str | int | float | Decimal | None) -> Decimal:
    """What someone typed -> a number. "$1,500.50", "1500", " 2.5 " all work; anything else is 0."""
    if isinstance(text, Decimal):
        return text
    if text is None:
        return ZERO
    s = re.sub(r"[^\d.\-]", "", str(text))
    if s in ("", "-", ".", "-."):
        return ZERO
    try:
        d = Decimal(s)
    except InvalidOperation:
        return ZERO
    return d if d.is_finite() and abs(d) < LIMIT else ZERO


def cents(d: Decimal) -> Decimal:
    try:
        return d.quantize(CENT, rounding=ROUND_HALF_UP)
    except InvalidOperation:  # too big to have cents (only reachable by building a Decimal by hand)
        return ZERO


def fmt(d: Decimal, symbol: str = "$") -> str:
    """2700 -> "$2,700.00"; -50 -> "−$50.00"."""
    d = cents(d)
    sign = MINUS if d < 0 else ""
    return f"{sign}{symbol}{abs(d):,.2f}"


def fmt_qty(d: Decimal) -> str:
    """1 -> "1", 2.50 -> "2.5"."""
    if d == d.to_integral_value():
        return f"{int(d):,}"
    return f"{d.normalize():f}"


def fmt_rate(text: str) -> str:
    """A tax rate as typed -> "8.25%"."""
    return f"{fmt_qty(parse(text))}%"


def whole(d: Decimal) -> Decimal:
    """Round to whole dollars (day rates read best that way)."""
    try:
        return d.quantize(Decimal(1), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return ZERO


def fmt_short(d: Decimal, symbol: str = "$") -> str:
    """Whole amounts without cents: 24 -> "$24", 24.5 -> "$24.50"."""
    d = cents(d)
    if d == d.to_integral_value():
        sign = MINUS if d < 0 else ""
        return f"{sign}{symbol}{abs(int(d)):,}"
    return fmt(d, symbol)


def pct(text: str) -> Decimal:
    """A percent as typed ("4", "8.25%") -> 0.04, 0.0825. Never negative."""
    return max(ZERO, parse(text)) / 100
