"""Making, copying, moving, deleting and editing what's in a budget (categories, accounts, lines, globals,
fringes, fees), the budgets themselves, and the rate library.

A part of MainWindow (see main_window.py); it uses the window's widgets and the library."""

from __future__ import annotations

import re

from cuanto.core import calc, rates, templates
from cuanto.core.log import get_logger
from cuanto.core.model import (
    SECTIONS,
    Account,
    Adjustment,
    Category,
    Fringe,
    Global,
    Line,
    Rate,
    new_id,
    now_iso,
)
from cuanto.ui.dialogs.common import confirm
from cuanto.ui.window.common import kind_of, section_of

log = get_logger(__name__)


def _next_code(codes: list[str], step: int) -> str:
    """The next code after the highest number in `codes` ("2700" + 100 -> "2800"); "" when none are numbers."""
    nums = [int(c) for c in codes if re.fullmatch(r"\d{1,9}", c.strip() or "x")]
    if not nums:
        return ""
    top = max(nums)
    return str((top // step + 1) * step if step > 1 else top + 1)


def _plural(n: int, word: str) -> str:
    return f"{n:,} {word}{'s' if n != 1 else ''}"


class EditingMixin:
    # ------------------------------------------------------------------ saving
    def _edited(self) -> None:
        """A panel changed something: save in a moment, refresh the table in a moment."""
        if self.open_kind == "rate":
            self._dirty_rates = True
        elif self.open_kind == "budget" and self.budget_panel.budget is not None:
            self._dirty.add(self.budget_panel.budget.id)
        elif self.budget is not None:
            self._dirty.add(self.budget.id)
        self._save_timer.start()
        self._table_timer.start()

    def flush(self) -> None:
        """Save whatever is waiting to be saved."""
        self._save_timer.stop()
        for bid in list(self._dirty):
            b = self.lib.budgets.get(bid)
            if b is not None:
                try:
                    self.lib.save_budget(b)
                except OSError:
                    log.warning("couldn't save a budget", exc_info=True)
                    self.toast("Couldn't save. Check that there's free space on this computer.", "problem")
                    return
        self._dirty.clear()
        if self._dirty_rates:
            self._dirty_rates = False
            try:
                self.lib.save_rates()
            except OSError:
                log.warning("couldn't save the rate library", exc_info=True)

    def _changed_budget(self, select: tuple[str, str] | None = None) -> None:
        """The open budget changed (a new, moved or deleted part): save it now and show it."""
        if self.budget is not None:
            self._dirty.add(self.budget.id)
        self.flush()
        self.refresh()
        if select is not None:
            self.open(*select)

    def cell_edited(self, line_id: str, key: str, text: str) -> None:
        """Typed over a line right in the table."""
        b = self.budget
        got = b.find_line(line_id) if b is not None else None
        if got is None:
            return
        ln = got[2]
        if key == "unit":
            ln.unit = text
        elif key in ("description", "amount", "units", "rate"):
            setattr(ln, key, text.strip())
        self._dirty.add(b.id)
        self.flush()
        self.refresh()
        if self.open_kind == "line" and self.open_id == line_id:
            self._load_budget_thing("line", line_id)

    # ------------------------------------------------------------------ a new thing left empty
    def _fresh_state(self, kind: str, obj_id: str):
        b = self.budget
        if kind == "rate":
            r = self.lib.rates.get(obj_id)
            return r.to_dict() if r is not None else None
        if b is None:
            return None
        if kind == "line":
            got = b.find_line(obj_id)
            return got[2].to_dict() if got else None
        if kind == "account":
            got = b.find_account(obj_id)
            return got[1].to_dict() if got else None
        if kind == "category":
            c = b.find_category(obj_id)
            return c.to_dict() if c else None
        if kind == "global":
            g = next((x for x in b.globals if x.id == obj_id), None)
            return g.to_dict() if g else None
        if kind == "fringe":
            f = b.fringe(obj_id)
            return f.to_dict() if f else None
        if kind == "adjustment":
            a = next((x for x in b.adjustments if x.id == obj_id), None)
            return a.to_dict() if a else None
        return None

    def _mark_fresh(self, kind: str, obj_id: str) -> None:
        self._fresh = (kind, obj_id, self._fresh_state(kind, obj_id))

    def _drop_fresh(self, keep: str = "") -> None:
        """A new line, account, category, global, fringe, fee or rate you left without filling anything in
        (Esc, or opening something else) isn't kept."""
        fresh, self._fresh = self._fresh, None
        if fresh is None:
            return
        kind, obj_id, before = fresh
        if obj_id == keep:
            self._fresh = fresh
            return
        if before is None or self._fresh_state(kind, obj_id) != before:
            return
        self._remove(kind, obj_id)
        if self.open_id == obj_id:
            self._close_panel()
        if kind == "rate":
            self.lib.save_rates()
        elif self.budget is not None:
            self.lib.save_budget(self.budget)
        self.refresh()

    # ------------------------------------------------------------------ new
    def new_here(self) -> None:
        """The toolbar's +, where it makes one thing at once (its menu covers the rest)."""
        kind = kind_of(self.view_key)
        {
            "budgets": self.new_budget,
            "globals": self.new_global,
            "fringes": self.new_fringe,
            "rates": lambda: self.new_rate("crew"),
            "top": lambda: self.new_category("production"),
            "section": lambda: self.new_line(),
        }[kind]()

    def new_budget(self, kind: str | None = None) -> None:
        from cuanto.ui.dialogs.pickers import NewBudgetDialog

        self.flush()
        last = self.lib.settings.get("new_from")  # where the last new budget started
        d = NewBudgetDialog(
            self, kind or (last if isinstance(last, str) else "feature"), self.lib.ordered_templates()
        )
        if d.exec() != NewBudgetDialog.DialogCode.Accepted:
            return
        b = templates.start(d.kind, d.name, self.lib.templates)
        self.lib.add_budget(b)
        log.info("new budget from %s", "a template of yours" if d.kind.startswith(templates.MINE) else d.kind)
        self.lib.settings["new_from"] = d.kind
        self.lib.save_settings()
        self.go(f"budget:{b.id}")
        self.toast(f"Made {b.name or 'a new budget'}.", "done")

    def save_as_template(self, budget_id: str = "") -> None:
        """Keep a budget as a template of yours, to start new budgets from."""
        from cuanto.ui.dialogs.pickers import SaveTemplateDialog

        if not budget_id:
            picked = self.open_kind == "budget" and self.budget_panel.budget is not None
            budget_id = self.budget_panel.budget.id if picked else (self.budget.id if self.budget else "")
        src = self.lib.budgets.get(budget_id)
        if src is None:
            return
        self.flush()
        d = SaveTemplateDialog(self, src.name)
        if d.exec() != SaveTemplateDialog.DialogCode.Accepted:
            return
        old = self.lib.template_named(d.name)
        if old is not None and not confirm(
            self, f"Replace {old.name}?", "Budgets started from it stay as they are.", "Replace"
        ):
            return
        try:
            t = self.lib.add_template(templates.from_budget(src, d.name, d.keep_rates))
        except OSError:
            log.warning("couldn't save a template", exc_info=True)
            self.toast("Couldn't save. Check that there's free space on this computer.", "problem")
            return
        self.refresh()
        self.toast(f"Saved {t.name} as a template.", "done")

    def _target_account(self) -> Account | None:
        """Where a new line goes: the account that's open or picked, else the first one on this page."""
        b = self.budget
        if b is None:
            return None
        if self.open_kind == "line":
            got = b.find_line(self.open_id)
            if got:
                return got[1]
        if self.open_kind == "account":
            got = b.find_account(self.open_id)
            if got:
                return got[1]
        if self.open_kind == "category":
            c = b.find_category(self.open_id)
            if c is not None and c.accounts:
                return c.accounts[-1]
        s = section_of(self.view_key)
        return next((a for c, a in b.accounts() if not s or c.section == s), None)

    def new_line(self, account_id: str = "", after: str = "") -> None:
        b = self.budget
        if b is None:
            return
        self.flush()
        acc = None
        at = None
        if after:
            got = b.find_line(after)
            if got:
                acc = got[1]
                at = acc.lines.index(got[2]) + 1
        if acc is None and account_id:
            got = b.find_account(account_id)
            acc = got[1] if got else None
        acc = acc or self._target_account()
        if acc is None:
            self.toast("Make an account first.")
            self.new_account()
            return
        ln = Line(units="1", unit="allow")
        acc.lines.insert(len(acc.lines) if at is None else at, ln)
        self._changed_budget(("line", ln.id))
        self._mark_fresh("line", ln.id)
        self.line_panel.name.setFocus()

    def new_account(self, category_id: str = "") -> None:
        b = self.budget
        if b is None:
            return
        self.flush()
        c = b.find_category(category_id) if category_id else None
        if c is None and self.open_kind in ("account", "line"):
            got = b.find_account(self.open_id) if self.open_kind == "account" else b.find_line(self.open_id)
            c = got[0] if got else None
        if c is None and self.open_kind == "category":
            c = b.find_category(self.open_id)
        s = section_of(self.view_key)
        if c is None:
            c = next((x for x in reversed(b.categories) if not s or x.section == s), None)
        if c is None:
            self.new_category(s or "production")
            return
        a = Account(code=_next_code([x.code for x in c.accounts] or [c.code], 1))
        c.accounts.append(a)
        self._changed_budget(("account", a.id))
        self._mark_fresh("account", a.id)
        self.account_panel.name.setFocus()

    def new_category(self, section: str = "") -> None:
        b = self.budget
        if b is None:
            return
        self.flush()
        section = section if section in SECTIONS else (section_of(self.view_key) or "production")
        same = [c for c in b.categories if c.section == section]
        c = Category(section=section, code=_next_code([x.code for x in b.categories], 100))
        at = b.categories.index(same[-1]) + 1 if same else len(b.categories)
        if not same:  # the first in its section: after the sections that come before it
            order = SECTIONS.index(section)
            at = sum(1 for x in b.categories if SECTIONS.index(x.section) <= order)
        b.categories.insert(at, c)
        if self.view_key != "top":
            self.go(f"sec:{section}")
        self._changed_budget(("category", c.id))
        self._mark_fresh("category", c.id)
        self.category_panel.name.setFocus()

    def new_global(self) -> None:
        b = self.budget
        if b is None:
            return
        self.flush()
        g = Global()
        b.globals.append(g)
        if self.view_key != "globals":
            self.go("globals")
        self._changed_budget(("global", g.id))
        self._mark_fresh("global", g.id)
        self.global_panel.label.setFocus()

    def new_fringe(self) -> None:
        b = self.budget
        if b is None:
            return
        self.flush()
        f = Fringe()
        b.fringes.append(f)
        if self.view_key != "fringes":
            self.go("fringes")
        self._changed_budget(("fringe", f.id))
        self._mark_fresh("fringe", f.id)
        self.fringe_panel.name.setFocus()

    def new_adjustment(self) -> None:
        b = self.budget
        if b is None:
            return
        self.flush()
        a = Adjustment(base="running" if b.adjustments else "atl_btl")
        b.adjustments.append(a)
        if self.view_key != "top":
            self.go("top")
        self._changed_budget(("adjustment", a.id))
        self._mark_fresh("adjustment", a.id)
        self.adjustment_panel.name.setFocus()

    def new_rate(self, kind: str = "crew") -> None:
        self.flush()
        r = Rate(kind=kind, unit="days")
        self.lib.rates[r.id] = r
        self.lib.save_rates()
        if self.view_key != "rates":
            self.go("rates")
        self.refresh()
        self.open("rate", r.id)
        self._mark_fresh("rate", r.id)
        self.rate_panel.name.setFocus()

    # ------------------------------------------------------------------ duplicate
    def duplicate_current(self) -> None:
        if self.open_kind and self.open_kind not in ("global", "fringe", "adjustment", "category"):
            self.duplicate(self.open_kind, self.open_id)

    def duplicate(self, kind: str, obj_id: str) -> None:
        self.flush()
        if kind == "budget":
            src = self.lib.budgets.get(obj_id)
            if src is None:
                return
            b = self.lib.duplicate_budget(src)
            self.refresh()
            self.open("budget", b.id)
            self.toast(f"Made {b.name}.", "done")
            return
        if kind == "rate":
            src = self.lib.rates.get(obj_id)
            if src is None:
                return
            r = Rate.from_dict(src.to_dict())
            r.id, r.updated = new_id(), now_iso()
            r.name = f"{src.name} (Copy)" if src.name else ""
            self.lib.rates[r.id] = r
            self.lib.save_rates()
            self.refresh()
            self.open("rate", r.id)
            return
        b = self.budget
        if b is None:
            return
        if kind == "line":
            got = b.find_line(obj_id)
            if got is None:
                return
            _c, a, src = got
            ln = Line.from_dict(src.to_dict())
            ln.id = new_id()
            a.lines.insert(a.lines.index(src) + 1, ln)
            self._changed_budget(("line", ln.id))
            self.toast("Copied.", "done")
        elif kind == "account":
            got = b.find_account(obj_id)
            if got is None:
                return
            c, src = got
            acc = Account.from_dict(src.to_dict())
            acc.id = new_id()
            for ln in acc.lines:
                ln.id = new_id()
            acc.name = f"{src.name} (Copy)" if src.name else ""
            c.accounts.insert(c.accounts.index(src) + 1, acc)
            self._changed_budget(("account", acc.id))

    # ------------------------------------------------------------------ delete
    def delete_current(self) -> None:
        """⌘⌫: what's picked in the table, else what's open on the right."""
        t = self.current_table()
        got = t.chosen() if t is not None else []
        if not got and self.open_kind:
            got = [(self.open_kind, self.open_id)]
        if got:
            self.delete_many(got)

    def _describe(self, kind: str, obj_id: str) -> tuple[str, str]:
        """(its name, what else goes with it) for the alert."""
        b = self.budget
        if kind == "budget":
            x = self.lib.budgets.get(obj_id)
            return (x.name or "this budget") if x else "", "Its PDFs and exports stay where they are."
        if kind == "rate":
            r = self.lib.rates.get(obj_id)
            return (r.name or "this rate") if r else "", "Budgets that used it keep their numbers."
        if b is None:
            return "", ""
        if kind == "category":
            c = b.find_category(obj_id)
            if c is None:
                return "", ""
            n = sum(len(a.lines) for a in c.accounts)
            what = (
                f"Its {_plural(len(c.accounts), 'account')} and {_plural(n, 'line')} go too."
                if c.accounts
                else ""
            )
            return f"{c.code} {c.name}".strip() or "this category", what
        if kind == "account":
            got = b.find_account(obj_id)
            if got is None:
                return "", ""
            a = got[1]
            return (
                f"{a.code} {a.name}".strip() or "this account",
                f"Its {_plural(len(a.lines), 'line')} go too." if a.lines else "",
            )
        if kind == "line":
            got = b.find_line(obj_id)
            return (got[2].description or "this line") if got else "", ""
        if kind == "global":
            g = next((x for x in b.globals if x.id == obj_id), None)
            if g is None:
                return "", ""
            n = calc.uses_of(b, g.name) if g.name else 0
            return g.name or g.label or "this global", (
                f"{_plural(n, 'formula')} use it; they'll show a problem until you change them." if n else ""
            )
        if kind == "fringe":
            f = b.fringe(obj_id)
            n = sum(1 for _c, _a, ln in b.lines() if obj_id in ln.fringes)
            return (
                f.name or "this fringe"
            ) if f else "", f"It comes off the {_plural(n, 'line')} it's on." if n else ""
        if kind == "adjustment":
            a = next((x for x in b.adjustments if x.id == obj_id), None)
            return (a.name or "this fee") if a else "", ""
        return "", ""

    def delete_many(self, items: list[tuple[str, str]]) -> None:
        """Delete one thing or several of a kind, after an alert that names them."""
        if not items:
            return
        self.flush()
        kind = items[0][0]
        ids = [i for k, i in items if k == kind]
        named = [self._describe(kind, i) for i in ids]
        named = [(n, w) for n, w in named if n]
        if not named:
            return
        if len(named) == 1:
            title, text = f"Delete {named[0][0]}?", named[0][1]
        else:
            words = {"line": "lines", "account": "accounts", "category": "categories", "budget": "budgets",
                     "rate": "rates", "global": "globals", "fringe": "fringes", "adjustment": "fees"}  # fmt: skip
            title = f"Delete {len(named)} {words.get(kind, 'things')}?"
            names = [n for n, _w in named]
            text = ", ".join(names[:3]) + (f" and {len(names) - 3} more." if len(names) > 3 else ".")
        if not confirm(self, title, text, "Delete"):
            return
        for i in ids:
            self._remove(kind, i)
        if kind == "budget":
            if self.budget is not None and self.budget.id in ids:
                self.set_budget(None)
        elif kind == "rate":
            self.lib.save_rates()
        elif self.budget is not None:
            self._dirty.add(self.budget.id)
        if self.open_id in ids:
            self._close_panel()
        self.flush()
        self.go(self.view_key)
        self.toast("Deleted it." if len(ids) == 1 else f"Deleted {len(ids)}.", "done")

    def _remove(self, kind: str, obj_id: str) -> None:
        """Take one thing out (the caller saves)."""
        b = self.budget
        if kind == "budget":
            self.lib.delete_budget(obj_id)
            return
        if kind == "rate":
            self.lib.rates.pop(obj_id, None)
            return
        if b is None:
            return
        if kind == "category":
            b.categories = [c for c in b.categories if c.id != obj_id]
        elif kind == "account":
            for c in b.categories:
                c.accounts = [a for a in c.accounts if a.id != obj_id]
        elif kind == "line":
            for _c, a in b.accounts():
                a.lines = [ln for ln in a.lines if ln.id != obj_id]
        elif kind == "global":
            b.globals = [g for g in b.globals if g.id != obj_id]
        elif kind == "fringe":
            b.fringes = [f for f in b.fringes if f.id != obj_id]
            for _c, _a, ln in b.lines():
                if obj_id in ln.fringes:
                    ln.fringes = [f for f in ln.fringes if f != obj_id]
        elif kind == "adjustment":
            b.adjustments = [a for a in b.adjustments if a.id != obj_id]

    # ------------------------------------------------------------------ moving
    def step(self, kind: str, obj_id: str, by: int) -> None:
        """Move up (-1) or down (+1) among its neighbours (a category among its section's)."""
        b = self.budget
        if b is None:
            return
        if kind == "line":
            got = b.find_line(obj_id)
            seq = got[1].lines if got else None
        elif kind == "account":
            got = b.find_account(obj_id)
            seq = got[0].accounts if got else None
        elif kind == "adjustment":
            seq = b.adjustments
        elif kind == "category":
            c = b.find_category(obj_id)
            if c is None:
                return
            same = [i for i, x in enumerate(b.categories) if x.section == c.section]
            here = b.categories.index(c)
            k = same.index(here)
            if 0 <= k + by < len(same):
                there = same[k + by]
                b.categories[here], b.categories[there] = b.categories[there], b.categories[here]
                self._changed_budget((kind, obj_id))
            return
        else:
            return
        if not seq:
            return
        i = next((n for n, x in enumerate(seq) if x.id == obj_id), -1)
        j = i + by
        if i < 0 or not 0 <= j < len(seq):
            return
        seq[i], seq[j] = seq[j], seq[i]
        self._changed_budget((kind, obj_id))

    def move_line(self, line_id: str) -> None:
        from cuanto.ui.dialogs.pickers import AccountPicker

        b = self.budget
        got = b.find_line(line_id) if b is not None else None
        if got is None:
            return
        d = AccountPicker(b, "Move to Account", "Move", got[1].id, self)
        if d.exec() != AccountPicker.DialogCode.Accepted or d.account_id == got[1].id:
            return
        to = b.find_account(d.account_id)
        if to is None:
            return
        got[1].lines.remove(got[2])
        to[1].lines.append(got[2])
        self._changed_budget(("line", line_id))
        self.toast(f"Moved to {to[1].name or 'the account'}.", "done")

    def move_account(self, account_id: str, category_id: str) -> None:
        b = self.budget
        got = b.find_account(account_id) if b is not None else None
        to = b.find_category(category_id) if b is not None else None
        if got is None or to is None:
            return
        got[0].accounts.remove(got[1])
        to.accounts.append(got[1])
        self._changed_budget(("account", account_id))

    def global_renamed(self, _gid: str, old: str, new: str) -> None:
        """A global's name changed: every formula that used the old name uses the new one."""
        if self.budget is not None and old:
            n = calc.rename_global(self.budget, old, new)
            if n:
                self.toast(f"Renamed it in {_plural(n, 'formula')}.", "done")

    # ------------------------------------------------------------------ the rate library
    def use_rate(self, line_id: str) -> None:
        from cuanto.ui.dialogs.pickers import RatePicker

        b = self.budget
        got = b.find_line(line_id) if b is not None else None
        if got is None:
            return
        if not self.lib.rates:
            self.toast("The rate library is empty. Save a line to it first.")
            return
        d = RatePicker(self.lib.ordered_rates(), self, got[2].description)
        if d.exec() != RatePicker.DialogCode.Accepted:
            return
        r = self.lib.rates.get(d.rate_id)
        if r is None:
            return
        rates.apply(r, got[2], b)
        self._changed_budget(("line", line_id))
        self.toast(f"Used the rate for {r.name}.", "done")

    def save_rate(self, line_id: str) -> None:
        b = self.budget
        got = b.find_line(line_id) if b is not None else None
        if got is None:
            return
        c, _a, ln = got
        if not ln.description.strip():
            self.toast("Give the line a name first.", "problem")
            return
        r = rates.rate_from(ln, b, c.name)
        added, _updated = rates.merge(self.lib.rates, [r])
        mine = next(x for x in self.lib.rates.values() if rates.same(x, r))
        ln.rate_id = mine.id
        self._dirty.add(b.id)
        self.lib.save_rates()
        self._changed_budget(("line", line_id))
        self.toast("Saved to the rate library." if added else "Updated it in the rate library.", "done")

    def add_rate_to_budget(self, rate_id: str) -> None:
        from cuanto.ui.dialogs.pickers import AccountPicker

        b, r = self.budget, self.lib.rates.get(rate_id)
        if b is None or r is None:
            return
        self.flush()
        guess = next(
            (
                a.id
                for c, a in b.accounts()
                if r.department and r.department.casefold() in (a.name + " " + c.name).casefold()
            ),
            "",
        )
        d = AccountPicker(b, f"Add {r.name or 'the Rate'} to {b.name or 'the Budget'}", "Add", guess, self)
        if d.exec() != AccountPicker.DialogCode.Accepted:
            return
        got = b.find_account(d.account_id)
        if got is None:
            return
        ln = rates.line_from(r, b)
        got[1].lines.append(ln)
        self._dirty.add(b.id)
        self.flush()
        self.go(f"sec:{got[0].section}")
        self.open("line", ln.id)
        self.toast(f"Added to {got[1].name or 'the account'}.", "done")

    # ------------------------------------------------------------------ menus on rows
    def _row_menu(self, kind: str, obj_id: str, pos) -> None:
        from cuanto.ui.window.tables import menu

        items: list[tuple[str, str, object]] = []
        if kind == "budget":
            items = [
                ("receipt", "Open Top Sheet", lambda: self.go(f"budget:{obj_id}")),
                ("copy", "Duplicate", lambda: self.duplicate("budget", obj_id)),
                ("file", "Save as Template…", lambda: self.save_as_template(obj_id)),
                ("share", "Export JSON…", lambda: self.export_json(obj_id)),
            ]
        elif kind == "line":
            items = [
                ("copy", "Duplicate", lambda: self.duplicate("line", obj_id)),
                ("plus", "New Line Below", lambda: self.new_line(after=obj_id)),
                ("tag", "Use a Rate…", lambda: self.use_rate(obj_id)),
                ("folder", "Move to Account…", lambda: self.move_line(obj_id)),
            ]
        elif kind == "account":
            items = [
                ("plus", "New Line", lambda: self.new_line(account_id=obj_id)),
                ("copy", "Duplicate", lambda: self.duplicate("account", obj_id)),
            ]
        elif kind == "category":
            items = [("plus", "New Account", lambda: self.new_account(obj_id))]
        elif kind == "rate":
            items = [("copy", "Duplicate", lambda: self.duplicate("rate", obj_id))]
            if self.budget is not None:
                items.append(("plus", "Add to Budget…", lambda: self.add_rate_to_budget(obj_id)))
        t = self.current_table()
        chosen = t.chosen() if t is not None else []
        many = len(chosen) > 1 and (kind, obj_id) in chosen
        delete = (lambda: self.delete_many(chosen)) if many else (lambda: self.delete_many([(kind, obj_id)]))
        items += [("", "-", None), ("trash", f"Delete {len(chosen)}…" if many else "Delete…", delete)]
        if items[0][1] == "-":
            items = items[1:]
        menu(self, items).exec(pos)

    def _sidebar_menu(self, key: str, pos) -> None:
        from cuanto.ui.window.tables import menu

        if not key.startswith("budget:"):
            return
        bid = key[7:]
        menu(self, [
            ("receipt", "Open Top Sheet", lambda: self.go(key)),
            ("edit", "Budget Details…", lambda: self.budget_details(bid)),
            ("copy", "Duplicate", lambda: self.duplicate("budget", bid)),
            ("file", "Save as Template…", lambda: self.save_as_template(bid)),
            ("", "-", None),
            ("trash", "Delete…", lambda: self.delete_many([("budget", bid)])),
        ]).exec(pos)  # fmt: skip

    def budget_details(self, budget_id: str = "") -> None:
        """The budget's own details (name, client, profile…) on the right, from All Budgets."""
        bid = budget_id or (self.budget.id if self.budget is not None else "")
        if bid not in self.lib.budgets:
            return
        if self.view_key != "budgets":
            self.go("budgets")
        self.open("budget", bid)
