# The exchange format

Cuánto reads and writes plain JSON so other tools can work with it: send rates, a schedule and crew in, and
take a budget (a locked one, say, for invoicing) out. Everything here is generic; nothing is tied to a
particular app.

Money and quantities are written as text (`"725"`, `"12500.00"`), so nothing is lost to floating point.
Numbers are fine too when you write them.

## Coming in: `cuanto.exchange`

**File › Import JSON…** (or drop the file on an empty page). Rates go into the rate library; the schedule
and crew go into the budget that's open (without one, only the rates come in).

```json
{
  "format": "cuanto.exchange",
  "version": 1,
  "rates": [
    {"name": "Gaffer", "kind": "crew", "department": "Electric", "union": true, "local": "IATSE Local 728",
     "rate": "725", "unit": "days", "fringes": ["FICA", "Union P&H"]},
    {"name": "Grip Truck 5-Ton", "kind": "vendor", "department": "Grip", "vendor": "A Rental House",
     "rate": "1800", "unit": "days"}
  ],
  "schedule": {"globals": {"shoot_days": 22, "prep_days": 10}},
  "crew": [
    {"role": "Gaffer", "name": "A. Rivera", "account": "2901", "rate": "725", "unit": "days",
     "units": "shoot_days", "fringes": ["FICA", "Union P&H"]},
    {"role": "Drone Pilot", "department": "Camera", "rate": "1200", "unit": "days", "units": "2"}
  ]
}
```

- **rates**: `name` is required. A rate that's already in the library (same name, department, kind and
  union or not) gets the new numbers instead of a second copy. `unit` is one of `allow`, `flat`, `days`,
  `weeks`, `hours`, `months`, `each`, `units`.
- **schedule.globals**: a `{name: value}` map, or a list of `{"name", "label", "value", "unit"}`. Names are
  cleaned to what formulas can use (`"Shoot Days"` becomes `shoot_days`). A global that's there gets the new
  value; a new one is added.
- **crew**: each becomes a line, described as `role — name`. It goes in the account whose code (or name) is
  `account`, else an account or category named like `department`, else an account called Imported Crew.
  Importing the same crew again updates those lines instead of adding them twice. `amount`, `units` and
  `rate` may be formulas over the budget's globals. `fringes` are names of the budget's fringes.

## Going out: `cuanto.budget`

**File › Export JSON…** (also `python -m cuanto cli totals BUDGET.json`).

```json
{
  "format": "cuanto.budget",
  "version": 1,
  "app": "Cuánto 1.0.0",
  "exported": "2026-10-13T14:00:00",
  "budget": { "…every field of the budget, as Cuánto saves it…" },
  "totals": {
    "currency": "USD",
    "sections": {"atl": "419455.72", "production": "763843.33", "post": "178041.60", "other": "78006.00"},
    "above_the_line": "419455.72",
    "below_the_line": "1019890.93",
    "fringes": "139236.65",
    "adjustments": [{"id": "…", "name": "Contingency", "amount": "143934.67"}],
    "grand": "1583281.32",
    "categories": [{"id": "…", "code": "2700", "name": "Camera", "section": "production",
                    "subtotal": "…", "fringes": "…", "total": "…"}],
    "accounts": [{"id": "…", "category_id": "…", "code": "2701", "name": "Camera Crew", "subtotal": "…",
                  "fringes": "…", "total": "…"}],
    "lines": [{"id": "…", "account_id": "…", "category_code": "2700", "account_code": "2701",
               "description": "Director of Photography", "amount": "1", "units": "35", "unit": "days",
               "rate": "900.00", "subtotal": "31500.00", "fringes": "4425.75", "total": "35925.75",
               "problem": ""}]
  }
}
```

- `budget.stage` says whether it's a `bid`, `locked` or `actuals`.
- Line ids stay the same from version to version of a budget, so a tool can match lines across versions.
- A `cuanto.budget` file imported back into Cuánto becomes a budget of its own.

## Safety

Everything that comes in is data: it's read through the same checks as Cuánto's own files (lengths capped,
unknown fields ignored, wrong types dropped) and never run. Files over 10 MB, or from a newer version of the
format, are refused with a message that says why.
