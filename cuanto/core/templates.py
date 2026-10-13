"""Where a new budget starts: an indie feature, a short film, a commercial (laid out like the AICP bid
form), a music video, or blank.

A template is the shape of a budget: the categories and accounts people expect, the usual lines in each
(their amounts and units already tied to the schedule's globals), the usual fringes on crew and cast, and
the usual fees on the top sheet. Rates start empty: they're yours to fill in (or bring from the rate
library). Fringe percentages are typical starting points; check them with your payroll company.
"""

from __future__ import annotations

from cuanto.core.model import (
    KIND_NAMES,
    Account,
    Adjustment,
    Budget,
    Category,
    Fringe,
    Global,
    Line,
)

# fringe sets, by key (each template names the fringes it makes)
CREW = ("fica", "unemployment", "comp")
UNION_CREW = ("fica", "unemployment", "comp", "union")
CAST = ("fica", "unemployment", "comp", "talent")
DIRECTOR = ("fica", "unemployment", "comp", "dga")

_FRINGES = {
    "fica": ("FICA", "percent", "7.65", "", "Social Security and Medicare."),
    "unemployment": ("Unemployment (FUTA/SUTA)", "percent", "3.4", "", "Federal and state, on each wage."),
    "comp": ("Workers' Comp", "percent", "3", "", ""),
    "union": ("Union P&H", "percent", "", "", "The local's pension and health."),
    "talent": ("Talent P&H", "percent", "", "", "The performers' union pension and health."),
    "dga": ("Director P&H", "percent", "", "", "The directors' guild pension and health."),
    "payroll_fee": ("Payroll Service", "percent", "1", "", ""),
}


def L(description: str, units: str = "1", unit: str = "allow", amount: str = "1", fr=()) -> tuple:
    """A line in a template (rates start empty)."""
    return (description, amount, units, unit, tuple(fr))


# ---------------------------------------------------------------------------- an indie feature
PREP_SHOOT = "prep_days + shoot_days"
CREW_DAYS = "shoot_days"

FEATURE = {
    "globals": [
        ("prep_days", "Prep Days", "15", "days"),
        ("shoot_days", "Shoot Days", "20", "days"),
        ("wrap_days", "Wrap Days", "5", "days"),
        ("post_weeks", "Post Weeks", "16", "weeks"),
        ("crew_size", "Crew Size", "30", ""),
        ("cast_size", "Cast Size", "10", ""),
    ],
    "fringes": ("fica", "unemployment", "comp", "union", "talent", "dga", "payroll_fee"),
    "adjustments": [("Contingency", "percent", "10", "atl_btl")],
    "categories": [
        (
            "1100",
            "Story & Rights",
            "atl",
            [
                ("1101", "Rights", [L("Option"), L("Purchase Price")]),
                ("1102", "Writers", [L("Screenplay", fr=CREW), L("Revisions", fr=CREW)]),
            ],
        ),
        (
            "1200",
            "Producers",
            "atl",
            [
                (
                    "1201",
                    "Producers",
                    [L("Producer", "1", "flat", fr=CREW), L("Co-Producer", "1", "flat", fr=CREW)],
                ),
                (
                    "1202",
                    "Producers' Assistants",
                    [L("Assistant to Producer", "prep_days + shoot_days + wrap_days", "days", fr=CREW)],
                ),
            ],
        ),
        (
            "1300",
            "Director",
            "atl",
            [
                ("1301", "Director", [L("Director", "1", "flat", fr=DIRECTOR)]),
                ("1302", "Director's Assistant", [L("Assistant to Director", PREP_SHOOT, "days", fr=CREW)]),
            ],
        ),
        (
            "1400",
            "Cast",
            "atl",
            [
                (
                    "1401",
                    "Principal Cast",
                    [L("Lead", "shoot_days", "days", fr=CAST), L("Lead", "shoot_days", "days", fr=CAST)],
                ),
                ("1402", "Supporting Cast", [L("Supporting", "8", "days", "3", fr=CAST)]),
                ("1403", "Day Players", [L("Day Players", "1", "days", "6", fr=CAST)]),
                ("1404", "Casting", [L("Casting Director", "1", "flat"), L("Casting Sessions", "3", "days")]),
                ("1405", "Rehearsals", [L("Rehearsal Days", "3", "days", "cast_size", fr=CAST)]),
            ],
        ),
        (
            "1500",
            "Above-the-Line Travel",
            "atl",
            [
                (
                    "1501",
                    "Travel & Living",
                    [
                        L("Airfare", "1", "each", "4"),
                        L("Lodging", "shoot_days", "days", "4"),
                        L("Per Diem", "shoot_days", "days", "4"),
                    ],
                ),
            ],
        ),
        (
            "2000",
            "Production Staff",
            "production",
            [
                (
                    "2001",
                    "Production Management",
                    [
                        L("Line Producer / UPM", "prep_days + shoot_days + wrap_days", "days", fr=CREW),
                        L("Production Coordinator", "prep_days + shoot_days + wrap_days", "days", fr=CREW),
                        L("Production Accountant", "prep_days + shoot_days + wrap_days", "days", fr=CREW),
                    ],
                ),
                (
                    "2002",
                    "Assistant Directors",
                    [
                        L("1st Assistant Director", PREP_SHOOT, "days", fr=CREW),
                        L("2nd Assistant Director", PREP_SHOOT, "days", fr=CREW),
                    ],
                ),
                ("2003", "Script Supervisor", [L("Script Supervisor", "shoot_days + 2", "days", fr=CREW)]),
                (
                    "2004",
                    "Production Assistants",
                    [L("Production Assistants", "shoot_days", "days", "4", fr=CREW)],
                ),
            ],
        ),
        (
            "2100",
            "Background",
            "production",
            [
                ("2101", "Background Actors", [L("Background", "1", "days", "40")]),
                ("2102", "Stand-Ins", [L("Stand-Ins", "shoot_days", "days", "2", fr=CREW)]),
            ],
        ),
        (
            "2200",
            "Art Department",
            "production",
            [
                ("2201", "Production Designer", [L("Production Designer", PREP_SHOOT, "days", fr=CREW)]),
                ("2202", "Art Director", [L("Art Director", PREP_SHOOT, "days", fr=CREW)]),
                ("2203", "Art Department Crew", [L("Set Dresser", "shoot_days", "days", "2", fr=CREW)]),
            ],
        ),
        (
            "2300",
            "Set Construction",
            "production",
            [
                ("2301", "Construction Labor", [L("Carpenters", "10", "days", "2", fr=CREW)]),
                ("2302", "Materials", [L("Lumber, Paint, Hardware")]),
            ],
        ),
        (
            "2400",
            "Set Dressing & Props",
            "production",
            [
                ("2401", "Property Master", [L("Property Master", PREP_SHOOT, "days", fr=CREW)]),
                ("2402", "Purchases & Rentals", [L("Set Dressing"), L("Props"), L("Picture Vehicles")]),
            ],
        ),
        (
            "2500",
            "Wardrobe",
            "production",
            [
                (
                    "2501",
                    "Wardrobe Crew",
                    [
                        L("Costume Designer", PREP_SHOOT, "days", fr=CREW),
                        L("Wardrobe Supervisor", "shoot_days", "days", fr=CREW),
                    ],
                ),
                ("2502", "Purchases & Rentals", [L("Costumes"), L("Cleaning & Repairs")]),
            ],
        ),
        (
            "2600",
            "Makeup & Hair",
            "production",
            [
                (
                    "2601",
                    "Makeup & Hair Crew",
                    [
                        L("Key Makeup", "shoot_days", "days", fr=CREW),
                        L("Key Hair", "shoot_days", "days", fr=CREW),
                    ],
                ),
                ("2602", "Supplies", [L("Makeup & Hair Supplies")]),
            ],
        ),
        (
            "2700",
            "Camera",
            "production",
            [
                (
                    "2701",
                    "Camera Crew",
                    [
                        L("Director of Photography", PREP_SHOOT, "days", fr=CREW),
                        L("1st Assistant Camera", "shoot_days + 2", "days", fr=CREW),
                        L("2nd Assistant Camera", "shoot_days + 2", "days", fr=CREW),
                        L("DIT", "shoot_days", "days", fr=CREW),
                    ],
                ),
                (
                    "2702",
                    "Camera Equipment",
                    [L("Camera Package", "shoot_days / 5", "weeks"), L("Expendables")],
                ),
            ],
        ),
        (
            "2800",
            "Grip",
            "production",
            [
                (
                    "2801",
                    "Grip Crew",
                    [
                        L("Key Grip", "shoot_days + 2", "days", fr=CREW),
                        L("Best Boy Grip", "shoot_days", "days", fr=CREW),
                        L("Grips", "shoot_days", "days", "2", fr=CREW),
                    ],
                ),
                ("2802", "Grip Equipment", [L("Grip Package", "shoot_days / 5", "weeks"), L("Expendables")]),
            ],
        ),
        (
            "2900",
            "Electric",
            "production",
            [
                (
                    "2901",
                    "Electric Crew",
                    [
                        L("Gaffer", "shoot_days + 2", "days", fr=CREW),
                        L("Best Boy Electric", "shoot_days", "days", fr=CREW),
                        L("Electricians", "shoot_days", "days", "2", fr=CREW),
                    ],
                ),
                (
                    "2902",
                    "Lighting Equipment",
                    [
                        L("Lighting Package", "shoot_days / 5", "weeks"),
                        L("Generator", "shoot_days", "days"),
                        L("Expendables"),
                    ],
                ),
            ],
        ),
        (
            "3000",
            "Production Sound",
            "production",
            [
                (
                    "3001",
                    "Sound Crew",
                    [
                        L("Sound Mixer", "shoot_days", "days", fr=CREW),
                        L("Boom Operator", "shoot_days", "days", fr=CREW),
                    ],
                ),
                ("3002", "Sound Equipment", [L("Sound Package", "shoot_days", "days"), L("Expendables")]),
            ],
        ),
        (
            "3100",
            "Locations",
            "production",
            [
                (
                    "3101",
                    "Location Staff",
                    [
                        L("Location Manager", PREP_SHOOT, "days", fr=CREW),
                        L("Location Scout", "prep_days", "days", fr=CREW),
                    ],
                ),
                (
                    "3102",
                    "Location Fees",
                    [
                        L("Site Fees", "shoot_days", "days"),
                        L("Permits"),
                        L("Police & Fire", "shoot_days", "days"),
                        L("Security", "shoot_days", "days"),
                    ],
                ),
            ],
        ),
        (
            "3200",
            "Transportation",
            "production",
            [
                (
                    "3201",
                    "Vehicles",
                    [
                        L("Grip & Electric Truck", "shoot_days / 5", "weeks"),
                        L("Cargo Vans", "shoot_days / 5", "weeks", "2"),
                        L("Fuel"),
                    ],
                ),
                ("3202", "Drivers", [L("Drivers", "shoot_days", "days", "2", fr=CREW)]),
            ],
        ),
        (
            "3300",
            "Catering",
            "production",
            [
                (
                    "3301",
                    "Meals",
                    [
                        L("Catered Meals", "shoot_days", "days", "crew_size + cast_size"),
                        L("Craft Service", "shoot_days", "days"),
                    ],
                ),
            ],
        ),
        (
            "3400",
            "Media & Data",
            "production",
            [
                ("3401", "Media", [L("Drives & Media"), L("Backup & Transfer")]),
            ],
        ),
        (
            "3500",
            "Production Travel",
            "production",
            [
                (
                    "3501",
                    "Travel & Living",
                    [
                        L("Airfare", "1", "each", "6"),
                        L("Lodging", "shoot_days", "days", "6"),
                        L("Per Diem", "shoot_days", "days", "6"),
                    ],
                ),
            ],
        ),
        (
            "4000",
            "Editorial",
            "post",
            [
                (
                    "4001",
                    "Editors",
                    [
                        L("Editor", "post_weeks", "weeks", fr=CREW),
                        L("Assistant Editor", "post_weeks", "weeks", fr=CREW),
                    ],
                ),
                ("4002", "Editing Room", [L("Edit Suite & Storage", "post_weeks", "weeks")]),
            ],
        ),
        (
            "4100",
            "Music",
            "post",
            [
                ("4101", "Score", [L("Composer", "1", "flat")]),
                ("4102", "Licensing", [L("Songs", "1", "each", "3")]),
            ],
        ),
        (
            "4200",
            "Post Sound",
            "post",
            [
                (
                    "4201",
                    "Sound Editorial",
                    [L("Sound Design & Edit", "4", "weeks"), L("ADR & Foley", "3", "days")],
                ),
                ("4202", "Mix", [L("Final Mix", "5", "days")]),
            ],
        ),
        (
            "4300",
            "Visual Effects",
            "post",
            [
                ("4301", "VFX", [L("VFX Shots", "1", "each", "20")]),
            ],
        ),
        (
            "4400",
            "Color & Finishing",
            "post",
            [
                ("4401", "Color", [L("Color Grade", "8", "days")]),
                ("4402", "Finishing", [L("Conform & Online", "3", "days"), L("Titles & Graphics")]),
                ("4403", "Deliverables", [L("DCP & Masters"), L("Closed Captions")]),
            ],
        ),
        (
            "5000",
            "Insurance",
            "other",
            [
                (
                    "5001",
                    "Insurance",
                    [L("Production Package"), L("General Liability"), L("Errors & Omissions")],
                ),
            ],
        ),
        (
            "5100",
            "Legal & Accounting",
            "other",
            [
                ("5101", "Legal", [L("Production Counsel", "1", "flat"), L("Clearances")]),
                ("5102", "Accounting", [L("Audit")]),
            ],
        ),
        (
            "5200",
            "Publicity & Festivals",
            "other",
            [
                (
                    "5201",
                    "Publicity",
                    [L("Unit Stills Photographer", "5", "days", fr=CREW), L("Key Art & Trailer")],
                ),
                ("5202", "Festivals", [L("Submission Fees", "1", "each", "15"), L("Festival Travel")]),
            ],
        ),
        (
            "5300",
            "General Expenses",
            "other",
            [
                (
                    "5301",
                    "Office",
                    [
                        L("Production Office", "prep_days + shoot_days + wrap_days", "days"),
                        L("Phones & Internet"),
                        L("Office Supplies"),
                    ],
                ),
                ("5302", "Bank & Payroll", [L("Bank Fees")]),
            ],
        ),
    ],
}

# ---------------------------------------------------------------------------- a short film
SHORT = {
    "globals": [
        ("prep_days", "Prep Days", "5", "days"),
        ("shoot_days", "Shoot Days", "3", "days"),
        ("post_weeks", "Post Weeks", "6", "weeks"),
        ("crew_size", "Crew Size", "14", ""),
        ("cast_size", "Cast Size", "4", ""),
    ],
    "fringes": ("fica", "unemployment", "comp", "talent"),
    "adjustments": [("Contingency", "percent", "10", "atl_btl")],
    "categories": [
        ("1100", "Writing", "atl", [("1101", "Writer", [L("Screenplay")])]),
        ("1200", "Producing", "atl", [("1201", "Producer", [L("Producer", "1", "flat")])]),
        ("1300", "Directing", "atl", [("1301", "Director", [L("Director", "1", "flat")])]),
        (
            "1400",
            "Cast",
            "atl",
            [
                (
                    "1401",
                    "Cast",
                    [
                        L("Leads", "shoot_days", "days", "2", fr=CAST),
                        L("Supporting", "1", "days", "2", fr=CAST),
                    ],
                ),
                ("1402", "Casting", [L("Casting Director", "1", "flat")]),
            ],
        ),
        (
            "2000",
            "Production Staff",
            "production",
            [
                (
                    "2001",
                    "Production",
                    [
                        L("1st Assistant Director", PREP_SHOOT, "days", fr=CREW),
                        L("Script Supervisor", "shoot_days", "days", fr=CREW),
                        L("Production Assistants", "shoot_days", "days", "2", fr=CREW),
                    ],
                ),
            ],
        ),
        (
            "2100",
            "Camera",
            "production",
            [
                (
                    "2101",
                    "Camera Crew",
                    [
                        L("Director of Photography", "shoot_days + 1", "days", fr=CREW),
                        L("1st Assistant Camera", "shoot_days", "days", fr=CREW),
                    ],
                ),
                ("2102", "Camera Equipment", [L("Camera Package", "shoot_days", "days"), L("Expendables")]),
            ],
        ),
        (
            "2200",
            "Grip & Electric",
            "production",
            [
                (
                    "2201",
                    "G&E Crew",
                    [
                        L("Gaffer", "shoot_days", "days", fr=CREW),
                        L("Key Grip", "shoot_days", "days", fr=CREW),
                        L("Swing", "shoot_days", "days", fr=CREW),
                    ],
                ),
                (
                    "2202",
                    "G&E Equipment",
                    [L("Grip & Lighting Package", "shoot_days", "days"), L("Expendables")],
                ),
            ],
        ),
        (
            "2300",
            "Sound",
            "production",
            [
                (
                    "2301",
                    "Sound",
                    [
                        L("Sound Mixer", "shoot_days", "days", fr=CREW),
                        L("Sound Package", "shoot_days", "days"),
                    ],
                ),
            ],
        ),
        (
            "2400",
            "Art, Wardrobe & Makeup",
            "production",
            [
                (
                    "2401",
                    "Art",
                    [L("Production Designer", PREP_SHOOT, "days", fr=CREW), L("Set Dressing & Props")],
                ),
                (
                    "2402",
                    "Wardrobe & Makeup",
                    [
                        L("Costume Designer", "shoot_days + 2", "days", fr=CREW),
                        L("Makeup & Hair", "shoot_days", "days", fr=CREW),
                        L("Costumes & Supplies"),
                    ],
                ),
            ],
        ),
        (
            "2500",
            "Locations",
            "production",
            [
                (
                    "2501",
                    "Locations",
                    [L("Site Fees", "shoot_days", "days"), L("Permits"), L("Insurance Certificates")],
                )
            ],
        ),
        (
            "2600",
            "Transportation",
            "production",
            [("2601", "Vehicles", [L("Cargo Van", "shoot_days", "days"), L("Fuel & Parking")])],
        ),
        (
            "2700",
            "Catering",
            "production",
            [
                (
                    "2701",
                    "Meals",
                    [
                        L("Meals", "shoot_days", "days", "crew_size + cast_size"),
                        L("Craft Service", "shoot_days", "days"),
                    ],
                )
            ],
        ),
        ("2800", "Media", "production", [("2801", "Media", [L("Drives & Media")])]),
        ("3000", "Editorial", "post", [("3001", "Editor", [L("Editor", "post_weeks", "weeks")])]),
        (
            "3100",
            "Sound & Music",
            "post",
            [
                ("3101", "Sound Post", [L("Sound Design & Mix")]),
                ("3102", "Music", [L("Composer or Licensing")]),
            ],
        ),
        (
            "3200",
            "Color & Finishing",
            "post",
            [("3201", "Finishing", [L("Color Grade", "2", "days"), L("Deliverables")])],
        ),
        (
            "4000",
            "Festivals & Marketing",
            "other",
            [("4001", "Festivals", [L("Submission Fees", "1", "each", "10"), L("Poster & Stills")])],
        ),
        (
            "4100",
            "Insurance & Legal",
            "other",
            [("4101", "Insurance & Legal", [L("Production Insurance"), L("Legal & Clearances")])],
        ),
    ],
}

# ---------------------------------------------------------------------------- a commercial (AICP-style)
PREP_WRAP = "prep_days + wrap_days"

COMMERCIAL = {
    "globals": [
        ("prep_days", "Prep Days", "3", "days"),
        ("shoot_days", "Shoot Days", "2", "days"),
        ("wrap_days", "Wrap Days", "1", "days"),
        ("build_days", "Build Days", "1", "days"),
        ("post_days", "Post Days", "10", "days"),
    ],
    "fringes": ("fica", "unemployment", "comp", "union", "talent", "payroll_fee"),
    "adjustments": [("Production Fee", "percent", "20", "production")],
    "categories": [
        (
            "A",
            "Pre-Production & Wrap Crew",
            "production",
            [
                (
                    "A1",
                    "Production",
                    [
                        L("Producer", PREP_WRAP, "days", fr=CREW),
                        L("Production Supervisor", PREP_WRAP, "days", fr=CREW),
                        L("Assistant Director", "prep_days", "days", fr=CREW),
                        L("Production Assistants", PREP_WRAP, "days", "2", fr=CREW),
                    ],
                ),
                (
                    "A2",
                    "Department Heads",
                    [
                        L("Director of Photography", "prep_days", "days", fr=UNION_CREW),
                        L("Production Designer", "prep_days", "days", fr=CREW),
                        L("Wardrobe Stylist", "prep_days", "days", fr=CREW),
                        L("Location Scout", "prep_days", "days", fr=CREW),
                    ],
                ),
            ],
        ),
        (
            "B",
            "Shooting Crew",
            "production",
            [
                (
                    "B1",
                    "Production",
                    [
                        L("Producer", "shoot_days", "days", fr=CREW),
                        L("Production Supervisor", "shoot_days", "days", fr=CREW),
                        L("Assistant Director", "shoot_days", "days", fr=CREW),
                        L("Script Supervisor", "shoot_days", "days", fr=CREW),
                        L("Production Assistants", "shoot_days", "days", "4", fr=CREW),
                    ],
                ),
                (
                    "B2",
                    "Camera",
                    [
                        L("Director of Photography", "shoot_days", "days", fr=UNION_CREW),
                        L("1st Assistant Camera", "shoot_days", "days", fr=UNION_CREW),
                        L("2nd Assistant Camera", "shoot_days", "days", fr=UNION_CREW),
                        L("DIT", "shoot_days", "days", fr=UNION_CREW),
                    ],
                ),
                (
                    "B3",
                    "Grip & Electric",
                    [
                        L("Gaffer", "shoot_days + 1", "days", fr=UNION_CREW),
                        L("Best Boy Electric", "shoot_days + 1", "days", fr=UNION_CREW),
                        L("Electricians", "shoot_days", "days", "2", fr=UNION_CREW),
                        L("Key Grip", "shoot_days + 1", "days", fr=UNION_CREW),
                        L("Best Boy Grip", "shoot_days + 1", "days", fr=UNION_CREW),
                        L("Grips", "shoot_days", "days", "2", fr=UNION_CREW),
                    ],
                ),
                (
                    "B4",
                    "Art, Wardrobe, Hair & Makeup",
                    [
                        L("Production Designer", "shoot_days", "days", fr=CREW),
                        L("Prop Master", "shoot_days", "days", fr=CREW),
                        L("Wardrobe Stylist", "shoot_days", "days", fr=CREW),
                        L("Hair & Makeup", "shoot_days", "days", "2", fr=CREW),
                    ],
                ),
                ("B5", "Sound", [L("Sound Mixer", "shoot_days", "days", fr=UNION_CREW)]),
            ],
        ),
        (
            "C",
            "Pre-Production & Wrap Expenses",
            "production",
            [
                (
                    "C1",
                    "Office & Casting",
                    [
                        L("Office Rental", "prep_days + shoot_days + wrap_days", "days"),
                        L("Casting Facility", "2", "days"),
                        L("Working Meals"),
                        L("Messengers & Shipping"),
                    ],
                ),
            ],
        ),
        (
            "D",
            "Location & Travel",
            "production",
            [
                (
                    "D1",
                    "Locations",
                    [
                        L("Location Fees", "shoot_days", "days"),
                        L("Permits"),
                        L("Police & Fire", "shoot_days", "days"),
                    ],
                ),
                (
                    "D2",
                    "Transportation",
                    [
                        L("Production Trucks", "shoot_days", "days"),
                        L("Passenger Vans", "shoot_days", "days"),
                        L("Parking & Fuel"),
                    ],
                ),
                (
                    "D3",
                    "Meals",
                    [L("Catering", "shoot_days", "days", "40"), L("Craft Service", "shoot_days", "days")],
                ),
                (
                    "D4",
                    "Travel",
                    [L("Airfare", "1", "each"), L("Hotel", "1", "days"), L("Per Diem", "1", "days")],
                ),
            ],
        ),
        (
            "E",
            "Props, Wardrobe & Animals",
            "production",
            [
                (
                    "E1",
                    "Props & Wardrobe",
                    [L("Props"), L("Wardrobe"), L("Picture Vehicles"), L("Animals & Handlers")],
                ),
            ],
        ),
        (
            "F",
            "Studio Rental & Expenses",
            "production",
            [
                (
                    "F1",
                    "Stage",
                    [
                        L("Build Days", "build_days", "days"),
                        L("Shoot Days", "shoot_days", "days"),
                        L("Strike Days", "1", "days"),
                        L("Power & Cyc Paint"),
                    ],
                ),
            ],
        ),
        (
            "G",
            "Set Construction Labor",
            "production",
            [
                (
                    "G1",
                    "Construction Crew",
                    [
                        L("Set Designer", "build_days", "days", fr=CREW),
                        L("Carpenters", "build_days", "days", "3", fr=CREW),
                        L("Scenic Painter", "build_days", "days", fr=CREW),
                    ],
                ),
            ],
        ),
        (
            "H",
            "Set Construction Materials",
            "production",
            [
                ("H1", "Materials", [L("Lumber & Hardware"), L("Paint & Backings"), L("Set Dressing")]),
            ],
        ),
        (
            "I",
            "Equipment Rental",
            "production",
            [
                (
                    "I1",
                    "Equipment",
                    [
                        L("Camera Package", "shoot_days", "days"),
                        L("Grip Package", "shoot_days", "days"),
                        L("Lighting Package", "shoot_days", "days"),
                        L("Generator", "shoot_days", "days"),
                        L("Sound Package", "shoot_days", "days"),
                        L("Walkies", "shoot_days", "days"),
                    ],
                ),
            ],
        ),
        (
            "J",
            "Media",
            "production",
            [
                ("J1", "Media & Data", [L("Drives & Media"), L("Data Management", "shoot_days", "days")]),
            ],
        ),
        (
            "K",
            "Miscellaneous",
            "production",
            [
                ("K1", "Miscellaneous", [L("Petty Cash"), L("Production Insurance"), L("Payroll Handling")]),
            ],
        ),
        (
            "L",
            "Director & Creative Fees",
            "atl",
            [
                (
                    "L1",
                    "Director",
                    [
                        L("Prep", "prep_days", "days", fr=DIRECTOR),
                        L("Shoot", "shoot_days", "days", fr=DIRECTOR),
                        L("Post", "2", "days", fr=DIRECTOR),
                        L("Travel Days", "0", "days", fr=DIRECTOR),
                    ],
                ),
            ],
        ),
        (
            "M",
            "Talent",
            "atl",
            [
                (
                    "M1",
                    "On-Camera",
                    [
                        L("Principals", "shoot_days", "days", "2", fr=CAST),
                        L("Extras", "shoot_days", "days", "10", fr=CAST),
                        L("Fitting Fees", "1", "each", "2", fr=CAST),
                    ],
                ),
                ("M2", "Voice", [L("Voice-Over", "1", "each", fr=CAST)]),
            ],
        ),
        (
            "N",
            "Talent Expenses",
            "atl",
            [
                ("N1", "Expenses", [L("Agency Fees"), L("Wardrobe Allowance"), L("Talent Travel")]),
            ],
        ),
        (
            "O",
            "Editorial & Finishing",
            "post",
            [
                (
                    "O1",
                    "Editorial",
                    [
                        L("Editor", "post_days", "days"),
                        L("Assistant Editor", "post_days", "days"),
                        L("Edit Suite", "post_days", "days"),
                    ],
                ),
                (
                    "O2",
                    "Finishing",
                    [
                        L("Color", "1", "days"),
                        L("Online & Conform", "1", "days"),
                        L("Graphics"),
                        L("Sound Mix", "1", "days"),
                        L("Music"),
                        L("Deliverables"),
                    ],
                ),
            ],
        ),
    ],
}

# ---------------------------------------------------------------------------- a music video
MUSIC_VIDEO = {
    "globals": [
        ("prep_days", "Prep Days", "3", "days"),
        ("shoot_days", "Shoot Days", "1", "days"),
        ("post_days", "Post Days", "7", "days"),
        ("crew_size", "Crew Size", "18", ""),
    ],
    "fringes": ("fica", "unemployment", "comp"),
    "adjustments": [("Production Fee", "percent", "15", "production")],
    "categories": [
        (
            "1000",
            "Creative",
            "atl",
            [
                ("1001", "Director", [L("Director's Fee", "1", "flat"), L("Treatment & Boards")]),
            ],
        ),
        (
            "1100",
            "Talent",
            "atl",
            [
                (
                    "1101",
                    "Performers",
                    [
                        L("Dancers", "shoot_days + 1", "days", "4", fr=CREW),
                        L("Featured Extras", "shoot_days", "days", "6"),
                        L("Choreographer", "prep_days", "days", fr=CREW),
                    ],
                ),
            ],
        ),
        (
            "2000",
            "Production",
            "production",
            [
                (
                    "2001",
                    "Production Staff",
                    [
                        L("Producer", "prep_days + shoot_days", "days", fr=CREW),
                        L("Production Manager", "prep_days + shoot_days", "days", fr=CREW),
                        L("Production Assistants", "shoot_days", "days", "3", fr=CREW),
                    ],
                ),
            ],
        ),
        (
            "2100",
            "Camera",
            "production",
            [
                (
                    "2101",
                    "Camera",
                    [
                        L("Director of Photography", "shoot_days + 1", "days", fr=CREW),
                        L("1st Assistant Camera", "shoot_days", "days", fr=CREW),
                        L("Camera Package", "shoot_days", "days"),
                    ],
                ),
            ],
        ),
        (
            "2200",
            "Grip & Electric",
            "production",
            [
                (
                    "2201",
                    "G&E",
                    [
                        L("Gaffer", "shoot_days + 1", "days", fr=CREW),
                        L("Key Grip", "shoot_days + 1", "days", fr=CREW),
                        L("Swings", "shoot_days", "days", "2", fr=CREW),
                        L("Grip & Lighting Package", "shoot_days", "days"),
                    ],
                ),
            ],
        ),
        (
            "2300",
            "Art Department",
            "production",
            [
                (
                    "2301",
                    "Art",
                    [
                        L("Production Designer", "prep_days + shoot_days", "days", fr=CREW),
                        L("Set Build & Dressing"),
                        L("Props"),
                    ],
                ),
            ],
        ),
        (
            "2400",
            "Artist Styling",
            "production",
            [
                (
                    "2401",
                    "Styling",
                    [
                        L("Stylist", "shoot_days + 1", "days", fr=CREW),
                        L("Hair & Makeup", "shoot_days", "days", "2", fr=CREW),
                        L("Wardrobe"),
                    ],
                ),
            ],
        ),
        (
            "2500",
            "Stage & Locations",
            "production",
            [
                ("2501", "Stage & Locations", [L("Stage or Location", "shoot_days", "days"), L("Permits")]),
            ],
        ),
        (
            "2600",
            "Transportation & Catering",
            "production",
            [
                ("2601", "Transportation", [L("Truck", "shoot_days", "days"), L("Fuel & Parking")]),
                (
                    "2602",
                    "Catering",
                    [L("Meals", "shoot_days", "days", "crew_size"), L("Craft Service", "shoot_days", "days")],
                ),
            ],
        ),
        (
            "3000",
            "Post Production",
            "post",
            [
                ("3001", "Editorial", [L("Editor", "post_days", "days")]),
                ("3002", "Finishing", [L("Color", "1", "days"), L("VFX & Graphics"), L("Deliverables")]),
            ],
        ),
        (
            "4000",
            "Insurance & Miscellaneous",
            "other",
            [
                ("4001", "Insurance & Misc", [L("Production Insurance"), L("Petty Cash")]),
            ],
        ),
    ],
}

BLANK = {"globals": [], "fringes": (), "adjustments": [], "categories": []}

TEMPLATES = {
    "feature": FEATURE,
    "short": SHORT,
    "commercial": COMMERCIAL,
    "music_video": MUSIC_VIDEO,
    "blank": BLANK,
}


def build(kind: str, name: str = "") -> Budget:
    """A new budget from a template (a blank one for a kind it doesn't know)."""
    spec = TEMPLATES.get(kind, BLANK)
    b = Budget(name=name, kind=kind if kind in TEMPLATES else "blank")
    b.globals = [Global(name=n, label=label, value=v, unit=u) for n, label, v, u in spec["globals"]]
    fringe_ids: dict[str, str] = {}
    for key in spec["fringes"]:
        fname, fkind, rate, cap, notes = _FRINGES[key]
        f = Fringe(name=fname, kind=fkind, rate=rate, cap=cap, notes=notes)
        fringe_ids[key] = f.id
        b.fringes.append(f)
    b.adjustments = [Adjustment(name=n, kind=k, rate=r, base=base) for n, k, r, base in spec["adjustments"]]
    for code, cname, section, accounts in spec["categories"]:
        c = Category(code=code, name=cname, section=section)
        for acode, aname, lines in accounts:
            a = Account(code=acode, name=aname)
            for desc, amount, units, unit, fr in lines:
                a.lines.append(
                    Line(
                        description=desc,
                        amount=amount,
                        units=units,
                        unit=unit,
                        fringes=[fringe_ids[k] for k in fr if k in fringe_ids],
                    )
                )
            c.accounts.append(a)
        b.categories.append(c)
    return b


def choices() -> list[tuple[str, str]]:
    """(kind, name) for every template, in the order they're offered."""
    return [(k, KIND_NAMES[k]) for k in TEMPLATES]
