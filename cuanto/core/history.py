"""Undo and redo for what you keep in Cuánto: your budgets, your rate library and your profiles.

The window calls mark() whenever things settle (after a save or a refresh). If anything changed since the last
mark, the state before it becomes one undo step. Undo puts that state back and saves it. A change that's taken
straight back (a new line dropped before you filled it in) leaves no step behind.

Window things (what's open, folded, the look) aren't undone; neither are app settings. No Qt here.
"""

from __future__ import annotations

from typing import Any

from cuanto.core.model import Budget, Profile, Rate

LIMIT = 100  # steps kept

State = dict[str, Any]


def state_of(lib) -> State:
    budgets = {}
    for bid, b in lib.budgets.items():
        d = b.to_dict()
        d.pop("updated", None)  # saving stamps the time; that alone isn't a change
        budgets[bid] = d
    rates = []
    for r in lib.rates.values():
        d = r.to_dict()
        d.pop("updated", None)
        rates.append(d)
    return {
        "budgets": budgets,
        "rates": rates,
        "profiles": [p.to_dict() for p in lib.profiles.values()],
    }


PARTS = [("budgets", "budgets"), ("rates", "the rate library"), ("profiles", "profiles")]


def describe(a: State, b: State) -> str:
    """What differs between two states, in a few words: "The Long Night", "the rate library"."""
    parts = []
    for key, words in PARTS:
        if a.get(key) == b.get(key):
            continue
        if key == "budgets":
            changed = [
                (b["budgets"].get(k) or a["budgets"].get(k) or {}).get("name", "")
                for k in set(a["budgets"]) | set(b["budgets"])
                if a["budgets"].get(k) != b["budgets"].get(k)
            ]
            names = [n for n in changed if n]
            words = (
                names[0] if len(changed) == 1 and names else ("budgets" if len(changed) > 1 else "a budget")
            )
        parts.append(words)
    if not parts:
        return "a change"
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


class History:
    def __init__(self, lib):
        self.lib = lib
        self.undos: list[State] = []
        self.redos: list[State] = []
        self.last = state_of(lib)

    def mark(self) -> bool:
        """Note where things stand. True if that made a new undo step."""
        now = state_of(self.lib)
        if now == self.last:
            return False
        if self.undos and self.undos[-1] == now:  # taken straight back: no step either way
            self.undos.pop()
            self.last = now
            return False
        self.undos.append(self.last)
        del self.undos[:-LIMIT]
        self.redos.clear()
        self.last = now
        return True

    def can_undo(self) -> bool:
        return bool(self.undos) or state_of(self.lib) != self.last

    def can_redo(self) -> bool:
        return bool(self.redos)

    def undo(self) -> str | None:
        """Go back one step; what changed back (for a toast), or None if there's nothing to undo."""
        self.mark()
        if not self.undos:
            return None
        before = self.undos.pop()
        self.redos.append(self.last)
        what = describe(self.last, before)
        self._put(before)
        return what

    def redo(self) -> str | None:
        if not self.redos:
            return None
        self.mark()  # (nothing new can have happened since an undo without clearing redos)
        if not self.redos:
            return None
        after = self.redos.pop()
        self.undos.append(self.last)
        what = describe(self.last, after)
        self._put(after)
        return what

    def _put(self, s: State) -> None:
        """Make the library this state, and save what differs."""
        lib = self.lib
        old = state_of(lib)["budgets"]
        for bid in list(lib.budgets):
            if bid not in s["budgets"]:
                lib.delete_budget(bid)
        for bid, d in s["budgets"].items():
            if old.get(bid) != d:
                lib.save_budget(Budget.from_dict(d))
        lib.rates = {d["id"]: Rate.from_dict(d) for d in s["rates"]}
        lib.profiles = {d["id"]: Profile.from_dict(d) for d in s["profiles"]}
        lib.save_rates()
        lib.save_profiles()
        self.last = state_of(lib)
