"""Saving and loading: everything lives as small JSON files in Cuánto's data folder.

    budgets/<id>.json  one file per budget
    rates.json         your rate library
    profiles.json      your profile(s): whose name goes on the paper
    settings.json      window and app preferences
    backups/           a copy of a budget before a big change (an import into it), the newest kept

Every write goes to a temp file next to the real one, then replaces it in one step, so a crash or a full
disk never leaves a half-written file. A file that can't be read is set aside as <name>.unreadable-<time>
(never deleted) and logged; a budget with a few broken lines keeps the rest, and the original is kept too.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any

from cuanto.core.log import get_logger
from cuanto.core.model import Budget, Profile, Rate, new_id, now_iso
from cuanto.core.paths import data_dir

log = get_logger(__name__)


def write_json(path: Path, data: Any) -> None:
    """Write atomically: a temp file in the same folder, then os.replace."""
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def write_text(path: Path, text: str) -> None:
    """Write a text file atomically: a temp file in the same folder, then os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            log.warning("couldn't remove %s", tmp, exc_info=True)
        raise


ID_OK = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def safe_id(text: str) -> bool:
    """Ids name files (budgets/<id>.json): letters, digits, - and _ only."""
    return bool(ID_OK.match(str(text or "")))


def set_aside(path: Path, why: str, copy: bool = False) -> None:
    """Keep a file we couldn't use as <name>.<why>-<time>, so nothing is ever lost. `copy` leaves the
    original in place (when the good parts of it are still being used)."""
    aside = path.with_name(f"{path.name}.{why}-{int(time.time())}")
    log.warning("couldn't use all of %s; kept a copy as %s", path, aside.name)
    try:
        if copy:
            aside.write_bytes(path.read_bytes())
        else:
            path.replace(aside)
    except OSError:
        log.warning("couldn't set %s aside", path, exc_info=True)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):
        log.warning("couldn't read %s", path, exc_info=True)
        set_aside(path, "unreadable")
        return default


def _count(d: Any) -> int:
    """How many records a budget file holds (to tell whether reading it dropped any)."""
    if not isinstance(d, dict):
        return 0
    n = 0
    for key in ("globals", "fringes", "adjustments"):
        n += len(d[key]) if isinstance(d.get(key), list) else 0
    for c in d.get("categories") or []:
        n += 1
        for a in (c.get("accounts") or []) if isinstance(c, dict) else []:
            n += 1 + (len(a.get("lines") or []) if isinstance(a, dict) else 0)
    return n


def _count_budget(b: Budget) -> int:
    n = len(b.globals) + len(b.fringes) + len(b.adjustments)
    for c in b.categories:
        n += 1 + sum(1 + len(a.lines) for a in c.accounts)
    return n


class Library:
    """Everything Cuánto knows, loaded from the data folder and saved back file by file."""

    SNAPSHOTS_KEPT = 20

    def __init__(self, root: Path | None = None):
        self.root = root or data_dir()
        self.budgets: dict[str, Budget] = {}
        self.rates: dict[str, Rate] = {}
        self.profiles: dict[str, Profile] = {}
        self.settings: dict[str, Any] = {}

    @property
    def budget_dir(self) -> Path:
        return self.root / "budgets"

    # ------------------------------------------------------------------ files
    def load(self) -> Library:
        self.budgets = {}
        if self.budget_dir.is_dir():
            for f in sorted(self.budget_dir.glob("*.json")):
                raw = read_json(f, None)
                b = self._budget_from(raw, f)
                if b is None:
                    continue
                if f.stem != b.id:  # saved under its file's name from now on
                    b.id = f.stem if safe_id(f.stem) else b.id
                self.budgets[b.id] = b
        self.rates = self._many("rates.json", Rate)
        self.profiles = self._many("profiles.json", Profile)
        for p in self.profiles.values():  # a logo is a file name in the logos folder, nothing more
            p.logo = Path(p.logo).name if p.logo else ""
        s = read_json(self.root / "settings.json", {})
        self.settings = s if isinstance(s, dict) else {}
        log.info(
            "loaded %d budgets, %d rates, %d profiles from %s",
            len(self.budgets), len(self.rates), len(self.profiles), self.root,
        )  # fmt: skip
        return self

    @staticmethod
    def _budget_from(raw: Any, f: Path) -> Budget | None:
        if not isinstance(raw, dict):
            if f.exists():
                set_aside(f, "unreadable")
            return None
        try:
            b = Budget.from_dict(raw)
        except (TypeError, ValueError, AttributeError, KeyError, OverflowError, ArithmeticError):
            log.warning("skipped a broken budget %s", f.name, exc_info=True)
            set_aside(f, "unreadable")
            return None
        if not safe_id(b.id):
            b.id = new_id()
        if _count_budget(b) < _count(raw):  # some parts couldn't be read: keep the file as it was too
            set_aside(f, "partly-unreadable", copy=True)
        return b

    def _many(self, name: str, cls) -> dict:
        path = self.root / name
        raw = read_json(path, [])
        if not isinstance(raw, list):  # the wrong shape: keep it aside rather than save over it
            set_aside(path, "unreadable")
            return {}
        out = {}
        for d in raw:
            try:
                obj = cls.from_dict(d) if isinstance(d, dict) else None
            except (TypeError, ValueError, AttributeError, KeyError):
                log.warning("skipped a broken %s record", cls.__name__, exc_info=True)
                obj = None
            if obj is None:
                continue
            if not safe_id(obj.id):
                obj.id = new_id()
            out[obj.id] = obj
        if len(out) < len(raw):  # some records couldn't be read: keep the whole file as it was
            set_aside(path, "partly-unreadable", copy=True)
        return out

    def save_budget(self, b: Budget) -> None:
        b.updated = now_iso()
        self.budgets[b.id] = b
        write_json(self.budget_dir / f"{b.id}.json", b.to_dict())

    def save_rates(self) -> None:
        rates = sorted(self.rates.values(), key=lambda r: (r.department.casefold(), r.name.casefold()))
        write_json(self.root / "rates.json", [r.to_dict() for r in rates])

    def save_profiles(self) -> None:
        write_json(self.root / "profiles.json", [p.to_dict() for p in self.profiles.values()])

    def save_settings(self) -> None:
        write_json(self.root / "settings.json", self.settings)

    def snapshot(self, budget_id: str, why: str) -> Path | None:
        """A dated copy of a budget's file in backups/ before a big change (an import into it, say); the
        newest SNAPSHOTS_KEPT are kept. None if it has no file yet or the copy couldn't be written."""
        src = self.budget_dir / f"{budget_id}.json"
        if not src.exists() or not safe_id(budget_id):
            return None
        folder = self.root / "backups"
        stamp = time.strftime("%Y-%m-%d-%H%M%S")
        dest = folder / f"{budget_id}-{stamp}-{re.sub(r'[^a-z0-9-]', '', why.lower())}.json"
        try:
            folder.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
            for old in sorted(folder.glob(f"{budget_id}-*.json"))[: -self.SNAPSHOTS_KEPT]:
                old.unlink(missing_ok=True)
        except OSError:
            log.warning("couldn't keep a copy of the budget before %s", why, exc_info=True)
            return None
        return dest

    # ------------------------------------------------------------------ budgets
    def ordered_budgets(self) -> list[Budget]:
        """A to Z by name (untitled ones last)."""
        return sorted(self.budgets.values(), key=lambda b: (not b.name.strip(), b.name.casefold(), b.created))

    def add_budget(self, b: Budget) -> Budget:
        if not safe_id(b.id) or b.id in self.budgets:
            b.id = new_id()
        if not b.family:
            b.family = b.id
        self.save_budget(b)
        return b

    def duplicate_budget(self, src: Budget, name: str = "") -> Budget:
        """A copy to change freely (its lines keep their ids, so the two can be compared later)."""
        b = Budget.from_dict(src.to_dict())
        b.id = new_id()
        b.name = name or (f"{src.name} (Copy)" if src.name else "")
        b.stage = "bid"
        b.created = now_iso()
        return self.add_budget(b)

    def delete_budget(self, budget_id: str) -> None:
        self.budgets.pop(budget_id, None)
        if not safe_id(budget_id):
            return
        f = self.budget_dir / f"{budget_id}.json"
        try:
            f.unlink(missing_ok=True)
        except OSError:
            log.warning("couldn't remove %s", f, exc_info=True)

    # ------------------------------------------------------------------ profiles
    def profile(self, budget: Budget | None = None) -> Profile | None:
        """The profile a budget's pages are from: its own, else the one in use, else the first."""
        if budget is not None and budget.profile_id in self.profiles:
            return self.profiles[budget.profile_id]
        cur = self.settings.get("profile", "")
        return self.profiles.get(cur) or next(iter(self.profiles.values()), None)

    def add_profile(self, p: Profile) -> Profile:
        self.profiles[p.id] = p
        self.save_profiles()
        return p

    def delete_profile(self, profile_id: str) -> None:
        self.profiles.pop(profile_id, None)
        for b in self.budgets.values():
            if b.profile_id == profile_id:
                b.profile_id = ""
                self.save_budget(b)
        self.save_profiles()

    # ------------------------------------------------------------------ rates
    def departments(self) -> list[str]:
        """Every department in the rate library, A to Z."""
        return sorted({r.department for r in self.rates.values() if r.department}, key=str.casefold)

    def ordered_rates(self) -> list[Rate]:
        return sorted(self.rates.values(), key=lambda r: (r.department.casefold() or "~", r.name.casefold()))
