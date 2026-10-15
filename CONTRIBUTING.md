# Cuánto code rules

How Cuánto's code is organized and the rules every change follows. The look of the app has its own rulebook:
**[DESIGN.md](DESIGN.md)**. Read both before changing anything.

Python 3.12 + PySide6 (Qt Widgets). Pages are drawn with QPainter (one layout for preview, PDF, PNG and print).
Shipped as a PyInstaller app; GitHub Actions builds the downloads.

---

## 1. Where things go

Layers only ever call downward: `ui/` uses `core/`, `doc/` and `services/`; those never import `ui/`.

```
cuanto/
  core/            Budgets, their numbers and their files. No Qt imports, ever. Testable without a screen.
    model.py       Budget > Category (a top-sheet row, in a section) > Account > Line; Global, Fringe, Adjustment
                   (a top-sheet fee), BudgetInfo; Template (yours); Rate (the library); Profile. to_dict()/
                   from_dict() tolerate old, new and broken files. Room already for versions (family, stage,
                   Line.actual) and currencies (Line.currency, Budget.fx)
    formula.py     what an amount, units or rate can be: a number or arithmetic over globals. A small parser of
                   its own: never eval
    calc.py        THE numbers: lines (amount × units × rate), fringes (percent with a cap, or flat per unit),
                   accounts, categories, sections, above/below the line, fees, the grand total; globals resolved
                   (loops and typos are problems in words, counted as 0); renaming a global everywhere
    templates.py   indie feature, short film, commercial (AICP-style), music video, blank; yours (a budget kept
                   without what's only about its production, copied with new ids for each budget started from it)
    rates.py       the rate library: a line from a rate (fringes matched by name), a rate from a line, merging
    exchange.py    the JSON exchange format both ways (docs/exchange.md)
    sheets.py      CSV in (columns found by their titles), Excel out (values only; text never a formula)
    document.py    every string on the top sheet and the detail (DocView), before anything is drawn
    store.py       Library: budgets/<id>.json, rates.json, profiles.json, templates.json, settings.json;
                   atomic writes, unreadable files set aside, snapshots before an import
    history.py     undo/redo: mark() after saves and refreshes keeps the state before each change
    sample.py      the made-up Mesa Alta Pictures (tests, smoke test, screenshots)
    looks.py       the paper's colors
    web.py         the ONLY way anything reaches a link: https only, public addresses only (checked on every
                   redirect, connecting to the checked address), size caps; web_link() is THE test of a link
    update.py, paths.py, log.py, net.py, fileutil.py, dates.py, money.py   shared helpers
  doc/             render.py: layout(DocView, Palette, logo) -> [Page]; paint(). fonts.py, export.py
  services/        Outside Cuánto, no Qt; each with a "not connected yet" default: secrets.py (the keychain),
                   account.py, feedback.py
  ui/
    style/         tokens.py (every size, color, timing; DARK/LIGHT, ACCENTS, accent_set(), use()), theme.py
                   (the stylesheet, icons, theme.font(), theme.qcolor(), plain_tip())
    components/    widgets.py, panels.py (LeftPanel, SidePanel), glass.py (the backdrop, the sliding dock),
                   empty.py (start tiles), titlebar.py (Mac), worker.py (background jobs)
    window/        main_window.py (building, places, refresh, opening) made of parts: menus.py, editing.py
                   (new, duplicate, move, delete, the rate library, typing in the table), transfer.py (import,
                   export, back up), pages.py (the page window), services.py (settings, profiles, updates,
                   light/dark); sidebar.py; tables.py (one delegate paints every row); filters.py; common.py
    panels/        base.py (DetailsBase, form pieces), budget, category, account, line, globals, fringe,
                   adjustment, rate
    dialogs/       common.py (Alert, ask_name, about), settings.py, profile.py, pickers.py (new budget, rate,
                   account), preview.py (the page window), shortcuts.py, feedback.py, account.py, update.py
  app.py           QApplication, fonts, stylesheet, rounded popups, every QLabel plain text, one window at a
                   time, --smoke-test
  cli.py           `python -m cuanto cli …`: pages, totals, templates and CSV without a window
tests/             one file per area; conftest.py gives every test its own empty data folder; screenshot.py;
                   cut_off.py (finds words cut off in a window)
scripts/           make_icon.py (the "c." icon), release_notes.py
packaging/         macos/, windows/ (Inno Setup), linux/ (AppImage, .desktop, install.sh)
docs/              exchange.md (the JSON format), screenshot.png
```

Running it:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m cuanto
CUANTO_DATA_DIR=/tmp/x python -m cuanto   # a throwaway data folder
python -m pytest -q
QT_QPA_PLATFORM=offscreen python tests/screenshot.py OUTDIR [--look light] [--accent yellow]
pyinstaller cuanto.spec --noconfirm
```

---

## 2. Style

- `from __future__ import annotations` at the top of every module; every module starts with a one-line docstring
  saying what it's for. Type hints on every function. `X | None`, `list[str]`.
- **Ruff** formats and lints (line length 110). Before every commit:
  ```bash
  ruff format . && ruff check . && python -m pytest -q
  ```
  CI fails if any of them fails.
- Imports are absolute (`from cuanto.core import calc`). One module per job. No circular imports.
- Comments explain **why**. No dead code, no commented-out code, no `print()` in the app (use the logger).
- No `except: pass` around real work: catch the narrowest error, `log.warning(..., exc_info=True)`. Errors shown to
  people are plain sentences that say what to do; details go to the log.

---

## 3. Rules that matter

- **Money is computed in core/calc.py only.** The tables, panels, paper, exports and the exchange format ask it.
  Decimals, never floats; rounded to the cent per line.
- **Formulas go through core/formula.py.** Never `eval`, `exec` or `pickle` anything. A formula that can't be
  worked out is a problem in plain words, never an exception that reaches the window.
- **Never lose a budget.** Every write is atomic (`store.write_json`); unreadable files are renamed aside, never
  deleted; a budget with broken parts keeps the rest (and the file is kept as it was). A copy is kept before an
  import changes a budget.
- **Line ids never change** (a duplicated budget keeps them), so versions can be compared later.
- New model fields need defaults that mean "off" or "empty": old files are read through `from_dict()`.
- Everything a person changes saves itself (`SAVE_DELAY_MS`), and every change to budgets, rates or profiles ends
  in `flush()` and `refresh()` (that's where undo marks it). New commands go in the menus with their key.
- **Act once the click is over.** Anything a refresh can rebuild (start tiles, the sidebar's rows) acts once its
  click is over (`QTimer.singleShot(0, self, …)`, `DetailsBase.later`), never inside it. Its click may open a window
  or a menu, and whatever that window throws away is gone before the click is over: if it's the very thing that
  was clicked, Cuánto crashes. `still_there_after` in `tests/test_window.py` catches it.
- **Hide it before throwing it away.** A part of a window replaced while it shows (a Settings pane) is hidden,
  then `deleteLater()`: an embedded dialog hides itself as it goes, and the typing inside it then jumps into
  half-gone widgets and crashes Cuánto. A window test that types makes its window the active one first
  (offscreen, nothing has the typing otherwise, and the crash never shows).
- Every left list is a `LeftPanel`, every right panel a `SidePanel` (through `DetailsBase`).
- Every number in the UI is a token; every font comes from `theme.font()`; dialogs end with `button_row()`.
- Anything from outside (a CSV, a JSON file, a name) is data: shown as plain text (labels are plain app-wide;
  tooltips through `theme.plain_tip`), checked through `from_dict()`, never run.
- Sample data is made up (`core/sample.py`). Real budgets, people and rates never go in the code or the repo.

---

## 4. Safety rules (never break these)

1. Exports (PDF, PNG, Excel, JSON, backups) are written to a temp file beside the target and moved into place: a
   failed export never leaves a broken file or replaces a good one.
2. Logos are read and saved again into the data folder (`dialogs/profile.import_logo`); the original is never touched.
3. Running programs: arguments as a list, never `shell=True`; only the system's own openers and the updater's helper.
4. HTTPS only, certificate checks on (`net.ssl_context()`). Links only through `core/web.py`.
5. Keys and sign-ins only in the system keychain (`services/secrets.py`); never in a file, setting or log.
6. Updates only from this repository's releases, checked against the SHA-256 GitHub publishes.
7. Spreadsheets out carry values only: text that starts like a formula stays text.

---

## 5. Tests

- Every change to `core/` or `doc/` comes with a test named after the behavior
  (`test_a_broken_file_is_set_aside_not_lost`).
- Tests never touch real data: `tests/conftest.py` gives every test its own empty data folder.
- Window tests run offscreen. After any UI change, look at the screenshots in dark, light and Yellow.
- No words cut off: `tests/test_cut_off.py` opens every screen, state, panel, dialog and Settings pane (with the
  fonts as drawn and a tenth wider) and asks `tests/cut_off.py` for text that doesn't fit. A new screen gets a line
  there.
- `python -m cuanto --smoke-test` opens the window, makes the pages and an Excel file, and quits; CI runs it on the
  packaged app on every system.

---

## 6. Commits and releases

- One topic per commit, a short plain summary in the present tense ("Add A4 paper"), nothing added after it.
- Anything a user would notice goes in `CHANGELOG.md` under the next version, and the same pull request bumps
  `__version__` in `cuanto/__init__.py` (the last number for fixes, the middle one for a new feature).
- Merging is releasing: when main has a version with no tag yet, CI builds, tags it `vX.Y.Z` and publishes the
  downloads. A pushed tag must match `__version__` (an app reporting an older number offers itself as an update).
- The downloads are named `Cuanto-mac-apple-silicon.dmg`, `Cuanto-mac-intel.dmg`, `Cuanto-windows-setup.exe`,
  `Cuanto-windows-portable.zip`, `Cuanto-linux-x64.AppImage`, `Cuanto-linux-x64.tar.gz`. **These names are a
  contract** (the README's links and the updater use them).
- Never commit `build/`, `dist/`, real budgets, personal details, or anything with a password or key in it.
