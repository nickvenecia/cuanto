"""Formulas: what a line's amount, units or rate can be. A number, or arithmetic over the budget's globals:

    25        1,250.50        $900        10%        shoot_days        prep_weeks + 1        2 × (shoot_days + 3)

Read by a small parser written for this (never Python's eval): numbers (commas and a leading currency sign
are fine; a trailing % divides by 100), + − × ÷ (or * and /), parentheses and names. A name is a global,
whatever its capitals. Anything else is a FormulaError whose words say what to fix. No Qt here.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from decimal import Decimal, DivisionByZero, InvalidOperation
from functools import lru_cache

MAX_LEN = 300  # a formula longer than this is something pasted by mistake
MAX_DEPTH = 40  # parentheses inside parentheses
LIMIT = Decimal("1e12")  # bigger is a typo (and too big to round to the cent)
ZERO = Decimal(0)


class FormulaError(ValueError):
    """A formula that can't be worked out; the message says why, in plain words."""


_TOKEN = re.compile(
    r"\s*(?:"
    r"(?P<num>[$€£]?\s*(?:\d[\d,]*(?:\.\d*)?|\.\d+)\s*%?)"
    r"|(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"|(?P<op>[-+*/×÷−()])"
    r")"
)
_OPS = {"×": "*", "÷": "/", "−": "-"}


def _tokens(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    pos = 0
    text = text.strip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if m is None or m.end() == pos:
            bad = text[pos:].strip()[:1]
            raise FormulaError(f"Cuánto can't read “{bad}” here. Use numbers, globals and + − × ÷.")
        pos = m.end()
        if m.group("num") is not None:
            out.append(("num", m.group("num")))
        elif m.group("name") is not None:
            out.append(("name", m.group("name")))
        else:
            op = m.group("op")
            out.append(("op", _OPS.get(op, op)))
    return out


def _number(raw: str) -> Decimal:
    s = raw.replace(",", "").replace(" ", "").lstrip("$€£")
    pct = s.endswith("%")
    s = s.rstrip("%")
    try:
        d = Decimal(s)
    except InvalidOperation as e:
        raise FormulaError(f"“{raw.strip()}” isn't a number.") from e
    if not d.is_finite() or abs(d) >= LIMIT:
        raise FormulaError(f"“{raw.strip()}” is too big.")
    return d / 100 if pct else d


# a parsed formula: ("num", Decimal) | ("name", str) | ("neg", node) | (op, left, right)
Node = tuple


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]]):
        self.t = tokens
        self.i = 0
        self.depth = 0

    def peek(self) -> tuple[str, str] | None:
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self) -> tuple[str, str]:
        tok = self.t[self.i]
        self.i += 1
        return tok

    def expr(self) -> Node:
        node = self.term()
        while (tok := self.peek()) is not None and tok in (("op", "+"), ("op", "-")):
            self.take()
            node = (tok[1], node, self.term())
        return node

    def term(self) -> Node:
        node = self.unary()
        while (tok := self.peek()) is not None and tok in (("op", "*"), ("op", "/")):
            self.take()
            node = (tok[1], node, self.unary())
        return node

    def unary(self) -> Node:
        tok = self.peek()
        if tok in (("op", "-"), ("op", "+")):
            self.take()
            inner = self.unary()
            return ("neg", inner) if tok[1] == "-" else inner
        return self.atom()

    def atom(self) -> Node:
        tok = self.peek()
        if tok is None:
            raise FormulaError("The formula stops too soon.")
        self.take()
        kind, text = tok
        if kind == "num":
            return ("num", _number(text))
        if kind == "name":
            return ("name", text.casefold())
        if text == "(":
            self.depth += 1
            if self.depth > MAX_DEPTH:
                raise FormulaError("Too many parentheses.")
            node = self.expr()
            if self.peek() != ("op", ")"):
                raise FormulaError("A “(” is missing its “)”.")
            self.take()
            self.depth -= 1
            return node
        raise FormulaError(f"“{text}” is in the wrong place.")


@lru_cache(maxsize=4096)
def parse(text: str) -> Node | None:
    """The formula as a tree, or None for a blank one. Raises FormulaError."""
    text = (text or "").strip()
    if not text:
        return None
    if len(text) > MAX_LEN:
        raise FormulaError("That formula is too long.")
    p = _Parser(_tokens(text))
    node = p.expr()
    if p.peek() is not None:
        tok = p.peek()
        raise FormulaError(
            "A “)” has no “(”." if tok == ("op", ")") else f"“{tok[1]}” is in the wrong place."
        )
    return node


def _calc(node: Node, lookup: Callable[[str], Decimal]) -> Decimal:
    kind = node[0]
    if kind == "num":
        return node[1]
    if kind == "name":
        return lookup(node[1])
    if kind == "neg":
        return -_calc(node[1], lookup)
    a, b = _calc(node[1], lookup), _calc(node[2], lookup)
    try:
        if kind == "+":
            out = a + b
        elif kind == "-":
            out = a - b
        elif kind == "*":
            out = a * b
        else:
            out = a / b
    except (DivisionByZero, InvalidOperation) as e:
        raise FormulaError("That divides by zero.") from e
    if not out.is_finite() or abs(out) >= LIMIT:
        raise FormulaError("That comes out too big.")
    return out


def evaluate(text: str, lookup: Callable[[str], Decimal], blank: Decimal = ZERO) -> Decimal:
    """Work a formula out. `lookup(name)` gives a global's value (names come casefolded) and raises
    FormulaError for one it doesn't know. A blank formula is `blank`."""
    node = parse(text)
    if node is None:
        return blank
    return _calc(node, lookup)


def names(text: str) -> set[str]:
    """The globals a formula uses (casefolded); empty for a broken one."""
    try:
        node = parse(text)
    except FormulaError:
        return set()
    found: set[str] = set()

    def walk(n) -> None:
        if n is None:
            return
        if n[0] == "name":
            found.add(n[1])
        elif n[0] == "neg":
            walk(n[1])
        elif n[0] != "num":
            walk(n[1])
            walk(n[2])

    walk(node)
    return found


def is_plain(text: str) -> bool:
    """A plain number (or blank), not a formula with a name in it."""
    return not names(text) and not re.search(r"[A-Za-z_]", text or "")


def rename(text: str, old: str, new: str) -> str:
    """The formula with every use of the global `old` called `new` instead (a renamed global)."""
    if not text or not old or old.casefold() == new.casefold():
        return text
    pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(old)}(?![A-Za-z0-9_])", re.IGNORECASE)
    return pattern.sub(new, text)


def clean_name(text: str) -> str:
    """What a global can be called: "Shoot Days" -> "shoot_days" (letters, digits and _, not starting
    with a digit)."""
    s = re.sub(r"[^A-Za-z0-9_]+", "_", (text or "").strip()).strip("_").lower()
    if s and s[0].isdigit():
        s = "g_" + s
    return s[:40]
