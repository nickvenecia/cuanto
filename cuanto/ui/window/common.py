"""What the main window's parts share: the places in the sidebar, their titles, and what each one shows."""

from __future__ import annotations

from cuanto.core.model import SECTION_NAMES, SECTIONS

# places that belong to the open budget (the sidebar's second section)
BUDGET_PLACES = ["top", *[f"sec:{s}" for s in SECTIONS], "globals", "fringes"]
TITLES = {
    "budgets": "All Budgets",
    "rates": "Rate Library",
    "top": "Top Sheet",
    "globals": "Globals",
    "fringes": "Fringes",
    **{f"sec:{s}": SECTION_NAMES[s] for s in SECTIONS},
}
PLACE_ICONS = {
    "budgets": "folder",
    "rates": "tag",
    "top": "receipt",
    "sec:atl": "star",
    "sec:production": "camera",
    "sec:post": "film",
    "sec:other": "box",
    "globals": "sliders",
    "fringes": "percent",
}


def kind_of(view: str) -> str:
    """What a place shows: budgets, rates, top (the top sheet), section (a section's detail), globals,
    fringes."""
    if view.startswith("sec:"):
        return "section"
    if view in ("budgets", "rates", "top", "globals", "fringes"):
        return view
    return "budgets"


def section_of(view: str) -> str:
    return view[4:] if view.startswith("sec:") else ""


def needs_budget(view: str) -> bool:
    return view in BUDGET_PLACES
