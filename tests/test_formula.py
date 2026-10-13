"""Formulas in a line's amount, units and rate (core/formula.py): numbers and globals, never eval."""

from __future__ import annotations

from decimal import Decimal

import pytest

from cuanto.core import formula
from cuanto.core.formula import FormulaError

GLOBALS = {"shoot_days": Decimal(20), "prep_days": Decimal(10)}


def look(name: str) -> Decimal:
    if name not in GLOBALS:
        raise FormulaError(f"There's no global called “{name}”.")
    return GLOBALS[name]


@pytest.mark.parametrize(
    ("text", "want"),
    [
        ("25", "25"),
        ("1,250.50", "1250.50"),
        ("$900", "900"),
        ("10%", "0.1"),
        ("shoot_days", "20"),
        ("Shoot_Days", "20"),
        ("prep_days + 1", "11"),
        ("2 × (shoot_days + 3)", "46"),
        ("shoot_days / 5", "4"),
        ("-shoot_days + 30", "10"),
        ("2*3+4", "10"),
        ("2*(3+4)", "14"),
        ("10 ÷ 4", "2.5"),
        ("7 − 2", "5"),
    ],
)
def test_formulas_work_out(text, want):
    assert formula.evaluate(text, look) == Decimal(want)


def test_blank_is_the_default():
    assert formula.evaluate("", look) == 0
    assert formula.evaluate("  ", look, blank=Decimal(1)) == 1


@pytest.mark.parametrize(
    "text",
    ["__import__('os')", "shoot_days +", "(1 + 2", "1 + 2)", "2 ** 3", "rest_days", "1 / 0", "9" * 40, "a.b"],
)
def test_anything_else_is_a_problem_in_words(text):
    with pytest.raises(FormulaError) as e:
        formula.evaluate(text, look)
    assert str(e.value) and "Traceback" not in str(e.value)


def test_names_and_renames():
    assert formula.names("prep_days + Shoot_Days * 2") == {"prep_days", "shoot_days"}
    assert formula.names("not valid +") == set()
    assert formula.rename("shoot_days + shoot_days_extra", "shoot_days", "days") == "days + shoot_days_extra"
    assert formula.is_plain("1,200") and not formula.is_plain("shoot_days")


def test_global_names_are_cleaned():
    assert formula.clean_name("Shoot Days") == "shoot_days"
    assert formula.clean_name("2nd Unit") == "g_2nd_unit"
    assert formula.clean_name("  --  ") == ""
