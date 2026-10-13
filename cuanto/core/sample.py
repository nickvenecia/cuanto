"""Made-up sample data for tests, the smoke test and screenshots: Mesa Alta Pictures, an indie feature called
The Long Night, a commercial for a made-up drink, and a small rate library. None of it is real: no real
people, companies or prices."""

from __future__ import annotations

from cuanto.core import templates
from cuanto.core.model import BudgetInfo, Profile, Rate
from cuanto.core.store import Library

# made-up day (or week, or flat) rates, by line description
FEATURE_RATES = {
    "Option": "5000", "Purchase Price": "25000", "Screenplay": "40000", "Revisions": "8000",
    "Producer": "45000", "Co-Producer": "20000", "Assistant to Producer": "250", "Director": "60000",
    "Assistant to Director": "250", "Lead": "1250", "Supporting": "1056", "Day Players": "1056",
    "Casting Director": "12000", "Casting Sessions": "650", "Rehearsal Days": "400", "Airfare": "450",
    "Lodging": "165", "Per Diem": "60", "Line Producer / UPM": "650", "Production Coordinator": "350",
    "Production Accountant": "400", "1st Assistant Director": "600", "2nd Assistant Director": "425",
    "Script Supervisor": "450", "Production Assistants": "200", "Background": "182", "Stand-Ins": "220",
    "Production Designer": "600", "Art Director": "450", "Set Dresser": "325", "Carpenters": "350",
    "Lumber, Paint, Hardware": "9500", "Property Master": "400", "Set Dressing": "12000", "Props": "6000",
    "Picture Vehicles": "3500", "Costume Designer": "500", "Wardrobe Supervisor": "350", "Costumes": "14000",
    "Cleaning & Repairs": "1500", "Key Makeup": "450", "Key Hair": "425", "Makeup & Hair Supplies": "2500",
    "Director of Photography": "900", "1st Assistant Camera": "500", "2nd Assistant Camera": "400",
    "DIT": "450", "Camera Package": "7500", "Expendables": "1200", "Key Grip": "500",
    "Best Boy Grip": "425", "Grips": "375", "Grip Package": "4500", "Gaffer": "500",
    "Best Boy Electric": "425", "Electricians": "375", "Lighting Package": "6000", "Generator": "450",
    "Sound Mixer": "600", "Boom Operator": "400", "Sound Package": "350", "Location Manager": "450",
    "Location Scout": "350", "Site Fees": "1500", "Permits": "4500", "Police & Fire": "900",
    "Security": "450", "Grip & Electric Truck": "1600", "Cargo Vans": "700", "Fuel": "3200",
    "Drivers": "300", "Catered Meals": "22", "Craft Service": "180", "Drives & Media": "4500",
    "Backup & Transfer": "1800", "Editor": "2800", "Assistant Editor": "1400",
    "Edit Suite & Storage": "650", "Composer": "18000", "Songs": "2500", "Sound Design & Edit": "3500",
    "ADR & Foley": "1200", "Final Mix": "1500", "VFX Shots": "800", "Color Grade": "1250",
    "Conform & Online": "900", "Titles & Graphics": "4000", "DCP & Masters": "6500",
    "Closed Captions": "1200", "Production Package": "18000", "General Liability": "4500",
    "Errors & Omissions": "6000", "Production Counsel": "15000", "Clearances": "4000", "Audit": "5000",
    "Unit Stills Photographer": "400", "Key Art & Trailer": "8000", "Submission Fees": "75",
    "Festival Travel": "6000", "Production Office": "120", "Phones & Internet": "1500",
    "Office Supplies": "1200", "Bank Fees": "600",
}  # fmt: skip

COMMERCIAL_RATES = {
    "Producer": "850", "Production Supervisor": "600", "Assistant Director": "750",
    "Production Assistants": "250", "Director of Photography": "1800", "Production Designer": "900",
    "Wardrobe Stylist": "700", "Location Scout": "550", "Script Supervisor": "650",
    "1st Assistant Camera": "650", "2nd Assistant Camera": "500", "DIT": "750", "Gaffer": "700",
    "Best Boy Electric": "600", "Electricians": "550", "Key Grip": "700", "Best Boy Grip": "600",
    "Grips": "550", "Prop Master": "600", "Hair & Makeup": "700", "Sound Mixer": "900",
    "Office Rental": "300", "Casting Facility": "1200", "Working Meals": "800",
    "Messengers & Shipping": "400", "Location Fees": "6500", "Permits": "2200", "Police & Fire": "1100",
    "Production Trucks": "1400", "Passenger Vans": "450", "Parking & Fuel": "900", "Catering": "45",
    "Craft Service": "600", "Props": "3500", "Wardrobe": "4500", "Build Days": "3500",
    "Shoot Days": "4500", "Strike Days": "2500", "Power & Cyc Paint": "2800", "Set Designer": "800",
    "Carpenters": "550", "Scenic Painter": "600", "Lumber & Hardware": "6500", "Paint & Backings": "3800",
    "Set Dressing": "4200", "Camera Package": "4200", "Grip Package": "2500", "Lighting Package": "4800",
    "Generator": "900", "Sound Package": "450", "Walkies": "120", "Drives & Media": "1500",
    "Data Management": "600", "Petty Cash": "1500", "Production Insurance": "3500",
    "Payroll Handling": "1800", "Prep": "2500", "Shoot": "5000", "Post": "2500", "Principals": "1200",
    "Extras": "250", "Fitting Fees": "300", "Voice-Over": "1800", "Agency Fees": "2400",
    "Wardrobe Allowance": "600", "Editor": "1100", "Assistant Editor": "500", "Edit Suite": "450",
    "Color": "4500", "Online & Conform": "2500", "Graphics": "6000", "Sound Mix": "3500",
    "Music": "7500", "Deliverables": "1800",
}  # fmt: skip

LIBRARY = [
    # name, department, union, local, rate, unit, fringes
    ("Director of Photography", "Camera", True, "IATSE Local 600", "1250", "days", ["FICA", "Union P&H"]),
    ("Director of Photography", "Camera", False, "", "900", "days", ["FICA"]),
    ("1st Assistant Camera", "Camera", True, "IATSE Local 600", "650", "days", ["FICA", "Union P&H"]),
    ("1st Assistant Camera", "Camera", False, "", "500", "days", ["FICA"]),
    ("Gaffer", "Electric", True, "IATSE Local 728", "725", "days", ["FICA", "Union P&H"]),
    ("Gaffer", "Electric", False, "", "500", "days", ["FICA"]),
    ("Key Grip", "Grip", True, "IATSE Local 80", "725", "days", ["FICA", "Union P&H"]),
    ("Key Grip", "Grip", False, "", "500", "days", ["FICA"]),
    ("Sound Mixer", "Sound", True, "IATSE Local 695", "800", "days", ["FICA", "Union P&H"]),
    ("Sound Mixer", "Sound", False, "", "600", "days", ["FICA"]),
    ("Production Designer", "Art", False, "", "600", "days", ["FICA"]),
    ("Script Supervisor", "Production", False, "", "450", "days", ["FICA"]),
    ("Production Assistant", "Production", False, "", "200", "days", ["FICA"]),
]
VENDORS = [
    # name, department, vendor, rate, unit
    ("Cinema Camera Package", "Camera", "Northlight Rentals", "1500", "days"),
    ("Grip & Electric 5-Ton", "Grip", "Arroyo Grip & Light", "1800", "days"),
    ("Production Van", "Transportation", "Mesa Vehicle Co.", "175", "days"),
    ("Catering, Per Person", "Catering", "Canyon Kitchen", "24", "each"),
]


def fill(lib: Library) -> Library:
    """The sample profile, two budgets and a rate library, saved into `lib`."""
    p = Profile(
        name="Mesa Alta Pictures",
        tagline="Features, commercials and music videos",
        email="hello@mesaalta.example",
        phone="(505) 555-0142",
        address="214 Calle Polvo\nSanta Fe, NM 87501",
        note="Estimate valid for 30 days. Rates assume a 12-hour day.",
    )
    lib.add_profile(p)
    lib.settings["profile"] = p.id

    feature = templates.build("feature", "The Long Night")
    feature.info = BudgetInfo(
        client="Mesa Alta Pictures",
        company="Mesa Alta Pictures",
        director="R. Valdez",
        producer="C. Ortega",
        format="4K, 2.39:1",
        dates="Nov 2–27, 2026",
        location="Santa Fe, New Mexico",
        notes="Assumes a non-union crew with union talent, 20 shoot days on location.",
    )
    _rates(feature, FEATURE_RATES)
    lib.add_budget(feature)

    spot = templates.build("commercial", "Agua Clara Summer Spot")
    spot.info = BudgetInfo(
        client="Agua Clara Sparkling Water",
        company="Mesa Alta Pictures",
        director="L. Moreno",
        producer="C. Ortega",
        format="1 × 30s, 2 × 15s",
        dates="Jun 8–9, 2026",
        location="Stage 2, Albuquerque",
    )
    _rates(spot, COMMERCIAL_RATES)
    lib.add_budget(spot)

    for name, dept, union, local, rate, unit, fringes in LIBRARY:
        r = Rate(name=name, department=dept, union=union, local=local, rate=rate, unit=unit, fringes=fringes)
        lib.rates[r.id] = r
    for name, dept, vendor, rate, unit in VENDORS:
        r = Rate(name=name, kind="vendor", department=dept, vendor=vendor, rate=rate, unit=unit)
        lib.rates[r.id] = r
    lib.save_rates()
    lib.save_settings()
    return lib


def _rates(budget, table: dict[str, str]) -> None:
    for _c, _a, ln in budget.lines():
        ln.rate = table.get(ln.description, ln.rate)
    for f in budget.fringes:  # the made-up union fringes get made-up numbers too
        if not f.rate:
            f.rate = {"Union P&H": "8", "Talent P&H": "21", "Director P&H": "17.5"}.get(f.name, "")
