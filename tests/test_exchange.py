"""The exchange format (core/exchange.py): rates, a schedule and crew in; a whole budget out and back."""

from __future__ import annotations

import json
from decimal import Decimal

from cuanto.core import calc, exchange, sample, templates
from cuanto.core.store import Library

CREW_FILE = {
    "format": "cuanto.exchange",
    "version": 1,
    "rates": [
        {"name": "Gaffer", "department": "Electric", "union": True, "local": "IATSE 728", "rate": "725", "unit": "days"},
    ],
    "schedule": {"globals": {"shoot_days": 22, "Company Moves": "3"}},
    "crew": [
        {"role": "Gaffer", "name": "A. Rivera", "account": "2901", "rate": "725", "unit": "days", "fringes": ["FICA"]},
        {"role": "Boom Operator", "department": "Sound Crew", "rate": "450", "unit": "days"},
        {"role": "Drone Pilot", "rate": "1200", "unit": "days", "units": "2"},
    ],
}  # fmt: skip


def test_rates_schedule_and_crew_come_in(data_folder):
    lib = Library(data_folder).load()
    b = templates.build("feature", "Test")
    rep = exchange.apply(exchange.check(CREW_FILE), lib.rates, b)
    assert rep.rates_added == 1 and rep.globals_set == 2
    assert (
        rep.lines_added == 2 and rep.lines_updated == 1
    )  # the template's own Boom Operator line gets the rate
    assert b.global_named("shoot_days").value == "22" and b.global_named("company_moves").value == "3"
    electric = next(a for _c, a in b.accounts() if a.code == "2901")
    gaffer = next(ln for ln in electric.lines if ln.description == "Gaffer — A. Rivera")
    assert (
        gaffer.rate == "725"
        and gaffer.units == "shoot_days"
        and [b.fringe(f).name for f in gaffer.fringes] == ["FICA"]
    )
    sound = next(a for _c, a in b.accounts() if a.name == "Sound Crew")
    assert next(ln for ln in sound.lines if ln.description == "Boom Operator").rate == "450"
    crew = next(a for _c, a in b.accounts() if a.name == exchange.CREW_ACCOUNT)
    assert crew.lines[0].description == "Drone Pilot" and crew.lines[0].units == "2"
    assert rep.words().startswith("Brought in 1 rate, 2 globals and 3 crew lines")


def test_importing_the_same_crew_again_updates_instead_of_doubling(data_folder):
    lib = Library(data_folder).load()
    b = templates.build("feature", "Test")
    exchange.apply(exchange.check(CREW_FILE), lib.rates, b)
    lines_before = sum(1 for _ in b.lines())
    again = json.loads(json.dumps(CREW_FILE))
    again["crew"][0]["rate"] = "800"
    again["rates"][0]["rate"] = "800"
    rep = exchange.apply(exchange.check(again), lib.rates, b)
    assert rep.lines_added == 0 and rep.lines_updated == 3 and rep.rates_updated == 1
    assert sum(1 for _ in b.lines()) == lines_before
    assert next(iter(lib.rates.values())).rate == "800"


def test_without_an_open_budget_only_rates_come_in(data_folder):
    lib = Library(data_folder).load()
    rep = exchange.apply(exchange.check(CREW_FILE), lib.rates, None)
    assert rep.rates_added == 1 and rep.lines_added == 0 and rep.skipped == 5


def test_a_budget_goes_out_with_every_number_and_comes_back(data_folder, tmp_path):
    lib = sample.fill(Library(data_folder).load())
    b = lib.ordered_budgets()[1]
    b.stage = "locked"
    data = exchange.export_budget(b)
    t = calc.totals(b)
    assert data["format"] == "cuanto.budget" and data["budget"]["stage"] == "locked"
    assert Decimal(data["totals"]["grand"]) == t.grand
    assert sum(Decimal(x["total"]) for x in data["totals"]["lines"]) == t.direct.total
    path = tmp_path / "out.json"
    path.write_text(json.dumps(data))
    read = exchange.read(path)
    back = exchange.budget_from(read, set(lib.budgets))
    assert back.id != b.id and calc.totals(back).grand == t.grand and back.family == b.family
