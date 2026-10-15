# Working on Cuánto

Read **[CONTRIBUTING.md](CONTRIBUTING.md)** (how the code is laid out, its rules, tests, commits) and
**[DESIGN.md](DESIGN.md)** (how every screen looks and reads) before changing anything. Before every commit:

```bash
ruff format . && ruff check . && python -m pytest -q
```

**Words are never cut off.** Text that might not fit wraps onto another line or ends in "…" with the whole text in
its tooltip; fonts are wider on a Mac. `tests/cut_off.py` checks every screen (from `tests/test_cut_off.py`); a new
screen gets a line in that test. Never fix it by shrinking the font.

**Nothing is thrown away while it's busy.** What a refresh can rebuild acts once its click is over, and a part of a
window that's replaced is hidden before `deleteLater()` (CONTRIBUTING §3). Either one, broken, crashes Cuánto.
