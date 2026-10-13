"""Dates the way Cuánto shows them ("Oct 10, 2026"), the same on every computer."""

from __future__ import annotations

from datetime import date, timedelta

MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)
MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)  # fmt: skip
CAL_WEEKDAYS = (
    "Sun",
    "Mon",
    "Tue",
    "Wed",
    "Thu",
    "Fri",
    "Sat",
)  # a calendar's columns: Sunday first, like a wall calendar


def today() -> date:
    return date.today()


def parse(s: str) -> date | None:
    try:
        return date.fromisoformat(s.strip()) if s else None
    except ValueError:
        return None


def iso(d: date) -> str:
    return d.isoformat()


def fmt(d: date | None) -> str:
    """date(2026, 10, 10) -> "Oct 10, 2026" (the same on every computer, whatever its language)."""
    if d is None:
        return ""
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"


def fmt_short(d: date | None) -> str:
    """date(2026, 10, 10) -> "Oct 10"."""
    if d is None:
        return ""
    return f"{MONTHS[d.month - 1]} {d.day}"


WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def fmt_day(d: date | None) -> str:
    """date(2026, 10, 9) -> "Fri, Oct 9, 2026"."""
    if d is None:
        return ""
    return f"{WEEKDAYS[d.weekday()]}, {fmt(d)}"


def span(a: date | None, b: date | None) -> str:
    """Two dates as a short range: "Oct 9–12, 2026", "Oct 30 – Nov 2, 2026", "Dec 30, 2026 – Jan 2, 2027"."""
    if a is None and b is None:
        return ""
    if a is None or b is None or a == b:
        return fmt(a or b)
    if a.year != b.year:
        return f"{fmt(a)} – {fmt(b)}"
    if a.month != b.month:
        return f"{fmt_short(a)} – {fmt_short(b)}, {b.year}"
    return f"{MONTHS[a.month - 1]} {a.day}–{b.day}, {a.year}"


def plus(d: date, days: int) -> date:
    return d + timedelta(days=days)
