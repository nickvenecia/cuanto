"""What Cuánto keeps: budgets (a top sheet of categories, their accounts, and the lines in each), their
globals, fringes and fees; your own templates; your rate library; your profiles.

Plain dataclasses with to_dict()/from_dict(). from_dict() tolerates files from older and newer versions:
unknown keys are ignored, missing keys get their default (defaults always mean "off" or empty), and a
broken part (one line, one fringe) is dropped instead of the whole budget. Numbers are kept as the text that
was typed ("1,250", "shoot_days + 2") and worked out in calc.py, the one place money is computed.

Room for what comes next, already in the files:
- versions: every version of one budget shares `family`; `stage` is bid, locked or actuals. Lines keep their
  ids from version to version, so a cost report can line them up (and `Line.actual` holds what was spent)
- more than one currency: `Line.currency` ("" means the budget's own) and `Budget.fx` (how many of each
  currency one unit of the budget's currency buys)
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------------- the words for things
SECTIONS = ("atl", "production", "post", "other")  # the top sheet's parts, in order
BELOW_THE_LINE = ("production", "post", "other")
SECTION_NAMES = {
    "atl": "Above the Line",
    "production": "Production",
    "post": "Post Production",
    "other": "Other",
}
UNITS = ("allow", "flat", "days", "weeks", "hours", "months", "each", "units")
UNIT_NAMES = {
    "allow": "Allow",
    "flat": "Flat",
    "days": "Days",
    "weeks": "Weeks",
    "hours": "Hours",
    "months": "Months",
    "each": "Each",
    "units": "Units",
}
KINDS = ("feature", "short", "commercial", "music_video", "blank")  # the template a budget started from
KIND_NAMES = {
    "feature": "Indie Feature",
    "short": "Short Film",
    "commercial": "Commercial",
    "music_video": "Music Video",
    "blank": "Blank",
}
STAGES = ("bid", "locked", "actuals")
STAGE_NAMES = {"bid": "Bid", "locked": "Locked", "actuals": "Actuals"}
FRINGE_KINDS = ("percent", "flat")  # a percent of the line, or a flat amount for each unit of it
ADJUSTMENT_KINDS = ("percent", "flat")
ADJUSTMENT_BASES = ("atl_btl", "btl", "production", "running")  # what a percent fee is a percent of
BASE_NAMES = {
    "atl_btl": "Above and Below the Line",
    "btl": "Below the Line",
    "production": "Production Only",
    "running": "Everything Above It",
}
RATE_KINDS = ("crew", "vendor")
CURRENCIES = ("USD", "MXN", "CAD", "EUR", "GBP")
SYMBOLS = {"USD": "$", "MXN": "MX$", "CAD": "CA$", "EUR": "€", "GBP": "£"}

MAX_TEXT = 2000  # one field: more than this is pasted by mistake (a whole document)
MAX_NOTES = 20_000


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _known(cls, d: dict) -> dict:
    names = {f.name for f in fields(cls)}
    return {k: v for k, v in d.items() if k in names}


def _text(v: Any, limit: int = MAX_TEXT) -> str:
    if v is None or isinstance(v, (dict, list)):
        return ""
    return str(v)[:limit]


def _one_of(v: Any, allowed: tuple[str, ...], default: str) -> str:
    return v if isinstance(v, str) and v in allowed else default


def _ids(v: Any) -> list[str]:
    return [str(x) for x in v if isinstance(x, (str, int))] if isinstance(v, list) else []


def _many(cls, raw: Any) -> list:
    """A list of records; a broken one is skipped (and the rest kept)."""
    out = []
    for d in raw if isinstance(raw, list) else []:
        if not isinstance(d, dict):
            continue
        try:
            out.append(cls.from_dict(d))
        except (TypeError, ValueError, AttributeError, KeyError):
            continue
    return out


def _fix_id(obj) -> None:
    obj.id = _text(obj.id, 64) or new_id()


# ---------------------------------------------------------------------------- a budget
@dataclass
class Line:
    """One line of an account: so many (amount) of so many units (5 days) at a rate. Amount, units and rate
    are numbers or formulas over the budget's globals ("shoot_days"). `fringes` are the ids of the budget's
    fringes that go on it (payroll taxes on a crew member, say)."""

    id: str = field(default_factory=new_id)
    description: str = ""
    amount: str = "1"
    units: str = "1"
    unit: str = "allow"
    rate: str = ""
    fringes: list[str] = field(default_factory=list)
    notes: str = ""
    rate_id: str = ""  # the rate library entry it came from, if any
    currency: str = ""  # "" = the budget's own (more than one currency comes later)
    actual: str = ""  # what was really spent (actuals come later)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Line:
        ln = cls(**_known(cls, d))
        _fix_id(ln)
        for k in ("description", "amount", "units", "rate", "rate_id", "currency", "actual"):
            setattr(ln, k, _text(getattr(ln, k)))
        ln.notes = _text(ln.notes, MAX_NOTES)
        ln.unit = _one_of(ln.unit, UNITS, "allow")
        ln.fringes = _ids(ln.fringes)
        return ln


@dataclass
class Account:
    """An account under a category (2301 Director of Photography): the lines that add up to it."""

    id: str = field(default_factory=new_id)
    code: str = ""
    name: str = ""
    notes: str = ""
    lines: list[Line] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.id, "code": self.code, "name": self.name, "notes": self.notes,
                "lines": [ln.to_dict() for ln in self.lines]}  # fmt: skip

    @classmethod
    def from_dict(cls, d: dict) -> Account:
        a = cls(**{k: v for k, v in _known(cls, d).items() if k != "lines"})
        _fix_id(a)
        a.code, a.name, a.notes = _text(a.code, 32), _text(a.name), _text(a.notes, MAX_NOTES)
        a.lines = _many(Line, d.get("lines"))
        return a


@dataclass
class Category:
    """A top-sheet row (2300 Camera): its accounts, in one section of the budget."""

    id: str = field(default_factory=new_id)
    code: str = ""
    name: str = ""
    section: str = "production"
    notes: str = ""
    accounts: list[Account] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.id, "code": self.code, "name": self.name, "section": self.section,
                "notes": self.notes, "accounts": [a.to_dict() for a in self.accounts]}  # fmt: skip

    @classmethod
    def from_dict(cls, d: dict) -> Category:
        c = cls(**{k: v for k, v in _known(cls, d).items() if k != "accounts"})
        _fix_id(c)
        c.code, c.name, c.notes = _text(c.code, 32), _text(c.name), _text(c.notes, MAX_NOTES)
        c.section = _one_of(c.section, SECTIONS, "production")
        c.accounts = _many(Account, d.get("accounts"))
        return c


@dataclass
class Global:
    """A named number any line can use: shoot_days = 25. Change it and every line using it follows.
    `value` may itself be a formula over other globals (prep_days = shoot_days / 2)."""

    id: str = field(default_factory=new_id)
    name: str = ""  # what lines type: letters, digits and _ (see formula.clean_name)
    label: str = ""  # what it is, in words: "Shoot Days"
    value: str = ""
    unit: str = ""  # one of UNITS, or "" for a plain number

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Global:
        g = cls(**_known(cls, d))
        _fix_id(g)
        g.name, g.label, g.value = _text(g.name, 64), _text(g.label), _text(g.value)
        g.unit = g.unit if g.unit in UNITS else ""
        return g


@dataclass
class Fringe:
    """Payroll tax, union pension & health, workers' comp…: a percent of each line it's on (up to an
    optional cap on that line's wages), or a flat amount for each unit of the line (per day, per hour)."""

    id: str = field(default_factory=new_id)
    name: str = ""
    kind: str = "percent"
    rate: str = ""
    cap: str = ""  # percent fringes: only this much of a line counts (a wage base); "" = no cap
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Fringe:
        f = cls(**_known(cls, d))
        _fix_id(f)
        f.name, f.rate, f.cap, f.notes = _text(f.name), _text(f.rate), _text(f.cap), _text(f.notes, MAX_NOTES)
        f.kind = _one_of(f.kind, FRINGE_KINDS, "percent")
        return f


@dataclass
class Adjustment:
    """Contingency, a production fee, a markup: added at the top sheet, in order, as a percent of `base` or a
    flat amount."""

    id: str = field(default_factory=new_id)
    name: str = ""
    kind: str = "percent"
    rate: str = ""
    base: str = "atl_btl"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Adjustment:
        a = cls(**_known(cls, d))
        _fix_id(a)
        a.name, a.rate = _text(a.name), _text(a.rate)
        a.kind = _one_of(a.kind, ADJUSTMENT_KINDS, "percent")
        a.base = _one_of(a.base, ADJUSTMENT_BASES, "atl_btl")
        return a


@dataclass
class BudgetInfo:
    """What the budget is for: the words at the top of its pages."""

    client: str = ""
    company: str = ""  # the production company
    director: str = ""
    producer: str = ""
    format: str = ""  # "4K, 2.39:1", "3 × 30s spots"
    dates: str = ""  # shoot dates, as written ("Nov 3–21, 2026")
    location: str = ""
    notes: str = ""  # assumptions, printed under the top sheet

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> BudgetInfo:
        i = cls(**_known(cls, d))
        for k in ("client", "company", "director", "producer", "format", "dates", "location"):
            setattr(i, k, _text(getattr(i, k)))
        i.notes = _text(i.notes, MAX_NOTES)
        return i


@dataclass
class Budget:
    id: str = field(default_factory=new_id)
    name: str = ""
    kind: str = "blank"
    info: BudgetInfo = field(default_factory=BudgetInfo)
    profile_id: str = ""  # whose name is on its pages ("" = the profile in use)
    currency: str = "USD"
    fx: dict[str, str] = field(default_factory=dict)  # code -> how many of it one unit of `currency` buys
    fx_date: str = ""
    family: str = ""  # shared by every version of this budget ("" = its own id)
    stage: str = "bid"
    globals: list[Global] = field(default_factory=list)
    fringes: list[Fringe] = field(default_factory=list)
    categories: list[Category] = field(default_factory=list)
    adjustments: list[Adjustment] = field(default_factory=list)
    created: str = field(default_factory=now_iso)
    updated: str = field(default_factory=now_iso)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "info": self.info.to_dict(),
            "profile_id": self.profile_id,
            "currency": self.currency,
            "fx": dict(self.fx),
            "fx_date": self.fx_date,
            "family": self.family,
            "stage": self.stage,
            "globals": [g.to_dict() for g in self.globals],
            "fringes": [f.to_dict() for f in self.fringes],
            "categories": [c.to_dict() for c in self.categories],
            "adjustments": [a.to_dict() for a in self.adjustments],
            "created": self.created,
            "updated": self.updated,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Budget:
        simple = {k: v for k, v in _known(cls, d).items() if k not in _PARTS}
        b = cls(**simple)
        _fix_id(b)
        b.name, b.profile_id = _text(b.name), _text(b.profile_id, 64)
        b.kind = _one_of(b.kind, KINDS, "blank")
        b.stage = _one_of(b.stage, STAGES, "bid")
        b.currency = _text(b.currency, 8).upper() or "USD"
        b.family = _text(b.family, 64)
        b.fx_date, b.created, b.updated = _text(b.fx_date, 32), _text(b.created, 32), _text(b.updated, 32)
        info = d.get("info")
        b.info = BudgetInfo.from_dict(info) if isinstance(info, dict) else BudgetInfo()
        fx = d.get("fx")
        b.fx = {str(k)[:8].upper(): _text(v, 32) for k, v in fx.items()} if isinstance(fx, dict) else {}
        b.globals = _many(Global, d.get("globals"))
        b.fringes = _many(Fringe, d.get("fringes"))
        b.categories = _many(Category, d.get("categories"))
        b.adjustments = _many(Adjustment, d.get("adjustments"))
        return b

    # ---- finding things
    def accounts(self):
        """Every (category, account), top to bottom."""
        for c in self.categories:
            for a in c.accounts:
                yield c, a

    def lines(self):
        """Every (category, account, line), top to bottom."""
        for c in self.categories:
            for a in c.accounts:
                for ln in a.lines:
                    yield c, a, ln

    def find_line(self, line_id: str) -> tuple[Category, Account, Line] | None:
        for c, a, ln in self.lines():
            if ln.id == line_id:
                return c, a, ln
        return None

    def find_account(self, account_id: str) -> tuple[Category, Account] | None:
        for c, a in self.accounts():
            if a.id == account_id:
                return c, a
        return None

    def find_category(self, category_id: str) -> Category | None:
        return next((c for c in self.categories if c.id == category_id), None)

    def fringe(self, fringe_id: str) -> Fringe | None:
        return next((f for f in self.fringes if f.id == fringe_id), None)

    def global_named(self, name: str) -> Global | None:
        key = name.casefold()
        return next((g for g in self.globals if g.name.casefold() == key), None)


_PARTS = ("info", "fx", "globals", "fringes", "categories", "adjustments")


# ---------------------------------------------------------------------------- your templates
@dataclass
class Template:
    """A budget you keep to start new ones from (Save as Template…): its categories, accounts and lines,
    globals, fringes and fees, and its rates unless you left them out (core/templates.from_budget)."""

    id: str = field(default_factory=new_id)
    name: str = ""
    budget: Budget = field(default_factory=Budget)
    created: str = field(default_factory=now_iso)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "created": self.created, "budget": self.budget.to_dict()}

    @classmethod
    def from_dict(cls, d: dict) -> Template:
        raw = d.get("budget")
        if not isinstance(raw, dict):
            raise ValueError("a template without its budget")
        t = cls(id=d.get("id", ""), name=_text(d.get("name")), budget=Budget.from_dict(raw))
        _fix_id(t)
        t.created = _text(d.get("created"), 32)
        return t


# ---------------------------------------------------------------------------- the rate library
@dataclass
class Rate:
    """A rate you keep and reuse across budgets: a crew position (union or not) or a vendor's price.
    `fringes` are fringe names ("FICA", "IATSE P&H"); a budget's fringes with those names go on a line made
    from it."""

    id: str = field(default_factory=new_id)
    name: str = ""  # the position or the thing: "Director of Photography", "Grip Truck 5-Ton"
    kind: str = "crew"
    department: str = ""  # Camera, Grip, Locations…
    union: bool = False
    local: str = ""  # "IATSE Local 600"
    rate: str = ""
    unit: str = "days"
    fringes: list[str] = field(default_factory=list)
    vendor: str = ""  # who it's from (vendors), or a crew member's name
    link: str = ""  # a vendor's site (opened only through core/web.web_link)
    notes: str = ""
    updated: str = field(default_factory=now_iso)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Rate:
        r = cls(**_known(cls, d))
        _fix_id(r)
        for k in ("name", "department", "local", "rate", "vendor", "link"):
            setattr(r, k, _text(getattr(r, k)))
        r.notes = _text(r.notes, MAX_NOTES)
        r.updated = _text(r.updated, 32)
        r.kind = _one_of(r.kind, RATE_KINDS, "crew")
        r.unit = _one_of(r.unit, UNITS, "days")
        r.union = (
            bool(r.union) if not isinstance(r.union, str) else r.union.strip().lower() in ("1", "true", "yes")
        )
        r.fringes = (
            [_text(x, 64) for x in r.fringes if isinstance(x, str) and x.strip()]
            if isinstance(r.fringes, list)
            else []
        )
        return r


# ---------------------------------------------------------------------------- your profiles
@dataclass
class Profile:
    """Your production company: whose name, logo and contact go on the budgets you print."""

    id: str = field(default_factory=new_id)
    name: str = ""
    tagline: str = ""
    email: str = ""
    phone: str = ""
    website: str = ""
    address: str = ""
    logo: str = ""  # a file name inside data_dir()/logos, never a path
    color: str = "orange"  # the accent on the paper (core/looks.py)
    note: str = ""  # a closing line under every top sheet ("Valid for 30 days.")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Profile:
        p = cls(**_known(cls, d))
        _fix_id(p)
        for k in ("name", "tagline", "email", "phone", "website", "logo", "color"):
            setattr(p, k, _text(getattr(p, k)))
        p.address, p.note = _text(p.address, MAX_NOTES), _text(p.note, MAX_NOTES)
        return p
