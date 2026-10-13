# Cuánto design rules

The rules for how Cuánto looks and reads. Follow them for every screen, dialog and control.
If a change needs something these rules don't cover, add a rule here in the same commit.

All numbers and colors live in **`cuanto/ui/style/tokens.py`**. The stylesheet (`cuanto/ui/style/theme.py`) and
every widget read from there. **Never type a size, spacing, font size or color anywhere else.** If you need a value
that doesn't exist, add a token with a comment, and add it to the tables below. A quick check that nothing slipped
through (1 px hairlines are the one allowed literal):

```bash
grep -nE '[^{_A-Z0-9][0-9]{2,}px|#[0-9A-Fa-f]{6}|rgba' -r cuanto/ui | grep -v tokens.py
```

---

## 1. Sizes

| Token | px | Used for |
|---|---|---|
| `CONTROL_H` | 34 | **Every** button, dropdown, text field, segmented control and round icon button |
| `SMALL_H` | 24 | Small round icon buttons inside rows and cards, chips |
| `SECTION_ADD` | 20 | A sidebar section's plain + |
| `TOGGLE_ROW_H` · `TOGGLE_W`×`TOGGLE_H` | 32 · 36×20 | An on/off row and its switch |
| `ICON` / `ICON_SM` / `ICON_LG` | 16 / 14 / 20 | Icons in buttons and menus / in small buttons / a hero icon |
| `TABLE_ROW_H` · `ROW_INSET` · `ROW_R` | 34 · 2 · 9 | A table row, its highlight's inset and corners |
| `FOLD_W` | 28 | The column a band's or an account's fold arrow sits in |
| `ROW_INDENT` | 18 | A line under its account, in the detail |
| `COL_W` | | Every table column's width |
| `NAME_MIN` | 240 | A table's name column never gets narrower; other columns step aside |

A button, a dropdown and a text field side by side line up exactly. Buttons size to their words; never a fixed width.

## 2. Spacing: a 4-point grid

| Token | px | Use it for |
|---|---|---|
| `SPACE_1` | 4 | A label and its control; an icon and its text |
| `SPACE_2` | 8 | Related items: buttons in a row, fields side by side |
| `SPACE_3` | 12 | Between sections inside a panel |
| `SPACE_4` | 16 | Padding of panels, bars and the main areas |
| `SPACE_5` | 24 | Padding of dialogs and empty states |

Margins are `SPACE_*` or 0. Layouts are built with `vbox()` / `hbox()`.

## 3. Type

**Inter** for everything (the app and its paper), loaded once from `cuanto/assets/fonts`. **IBM Plex Mono** only
for account codes on the paper. Sizes are `TEXT_XS` 11 · `TEXT_SM` 12 · `TEXT_MD` 13 (the default) · `TEXT_LG` 14 ·
`TEXT_XL` 18 · `TEXT_TITLE` 24 (a page's title, and a line's total in its panel) · `TEXT_BRAND` 21 (the wordmark).
Weights: 400 text · 500 controls · 600 titles and labels · 700 the wordmark, page titles and big totals.
Every font comes from `theme.font(size, weight)`.

## 4. Corners

`RADIUS_XS` 4 (checkbox) · `RADIUS_SM` 6 (chips) · `RADIUS` 8 (fields, dropdowns) · `RADIUS_LG` 12 (cards, alerts) ·
`GLASS_R` 18 (a floating panel) · `NAV_R` 8 (a sidebar row: `GLASS_R − NAV_INSET`, concentric with its panel).
Buttons and the search are capsules; icon buttons are circles.

**Every list of choices looks the same as the sidebar and Settings** (menus, dropdown lists, pickers, type-ahead):
`LIST_R`, `LIST_INSET`, `LIST_ROW_R`, `LIST_ROW_H`, `LIST_GAP`. Hover is `CARD_HOVER`; the highlighted row is
`ACCENT_TINT` with its words in `ACCENT_HOVER`.

## 5. Color

Every color token has a dark and a light value (`tokens.DARK`, `tokens.LIGHT`); `tokens.use(scheme, accent)` swaps
them and `theme.apply()` rebuilds the stylesheet. Read colors as `tokens.X` when drawing, never copy one into a
constant. Light and dark are equally finished; the app follows the system (View › Appearance pins one).

**Cuánto's accent is orange**, hand-set in `DARK` / `LIGHT` (dark `#F5893A`, light `#C2600E`). White doesn't read
on the dark look's orange, so `ON_ACCENT` there is near-black: never assume white on the accent. People can pick
another accent in Settings › General (`widgets.AccentPicker`; Orange first, then Blue, Purple, Pink, Yellow, Green,
Turquoise, Graphite; never red). `tokens.accent_set()` builds every shade of the others.

**Status colors are shared.** `BAD` (red) means over, a problem, or delete. Because the accent is orange, `WARN` is
shifted toward yellow (`#E0CB4A` dark, `#988000` light) so it never reads as the accent, and a status gets its own
shape where the accent's states are washes: the Locked chip is solid, Bid is a wash.

- The accent means "selected" or "do this". **One** primary button per view (New Line, Open Top Sheet, Save PDF…).
- A number that comes from a global (a formula) is drawn in the accent, so you can tell it follows something.
- A line that can't be worked out shows "—" in `BAD`, with what's wrong in its tooltip and in its panel.
- Status color comes from data: `widgets.set_tone(widget, tone, text)`; the stylesheet maps tones to colors.
- Never call `setStyleSheet()` on one widget; add a rule to `theme.py` under an object name.

## 6. Components

Use these; never build a control's look by hand. The object name picks the style.

| Kind | How | When |
|---|---|---|
| Primary | `setObjectName("Primary")` | The single main action in a view |
| Normal | (no name) | Everything else |
| Quiet | `Ghost` | Small helpers inside a card (Save to Library) |
| Add | `widgets.add_chip("Notes")` | "+ Notes": adding a part that isn't showing |
| Danger / Alert's yes | `Danger` / `DangerFill` | Destructive actions in a form / inside an Alert |
| Link | `LinkBtn` | Inline links (a line's "2700 Camera › 2701 Camera Crew", Open ↗) |
| Round icon button | `widgets.circle_button()` (`#Circle`, `#CirclePrimary` for New) | Toolbar and panel headers. Always a tooltip |
| Small round icon button | `widgets.icon_button()` | Inside a card (× to take notes off) |
| Section + | `SectionAdd` | The plain gray + beside a sidebar heading, faded in over its own section |
| Left panel | `panels.LeftPanel` + `NavRow` | The sidebar and Settings' sections |
| Right panel | `panels.SidePanel` → `panels/base.DetailsBase` | Every panel on the right: title, ⋯, ✕; Cards; one footer action |
| Card / Disclosure | `widgets.Card` / `Disclosure` | Every group inside a panel |
| Numbers | `panels/base.Numbers` | A card of figures: label left, value right |
| Formula field | `panels/base.formula_field()` | Amount, units, rate, a global's value: a number or a formula; offers the globals as you type |
| Dropdown | `widgets.combo()` | **Every** pick-one setting, however few choices |
| On/off | `widgets.ToggleRow` | Every on/off setting (a fringe on a line, Union Rate) |
| Segmented | `widgets.Segmented` | 2–3 views of one thing (Top Sheet / Detail / Both; Match System / Light / Dark) |
| Search | `widgets.SearchField` | The toolbar's capsule |
| Big name | `widgets.TitleEdit` | The name at the top of a panel: wraps, editable in place |
| Long one-line text | `widgets.ElidedLabel` | Cut with "…", whole in its tooltip (budget names in the sidebar) |
| Toast | `MainWindow.toast(text, tone)` | A short message: "done", "problem" or news |
| Alert | `dialogs/common.confirm` / `notice` | Every "are you sure", every error that needs more than a toast |
| Empty page | `components/empty.EmptyPage` | Where a table would be with nothing in it: start tiles |

## 7. Words

Cuánto talks like a helpful person, not like software.

- **No explaining on screen.** No hint sentences under fields, no paragraphs in empty states. If a label needs
  explaining, change the label; if it still does, a short tooltip.
- **Few words.** Labels 1–4 words: "Before Fringes", not "Subtotal excluding fringe benefits".
- **Title Case for labels** (buttons, menus, sections, dropdown choices, dialog titles): "New Fee or Markup",
  "Fringes on Every Line". Small words stay lowercase inside. No ALL CAPS in the app (the paper's small labels are
  part of the paper's design).
- **Sentences stay sentences**: tooltips, placeholders, toasts, errors.
- Buttons are verbs. "…" when they open a window or a file picker.
- Errors say what happened and what to do: "Cuánto couldn't find the column titles. Put Description and Rate (or
  Total) in one row."
- **Words are never cut off.** Text that might not fit wraps onto another line (`setWordWrap(True)`, the usual fix
  inside anything of a fixed width: cards, tiles, the sidebar) or ends in "…" with the whole text in its tooltip
  (`ElidedLabel`); fonts are wider on a Mac. Only if neither suits, give it more room or fewer words; never a
  smaller font. `tests/cut_off.py` checks every screen (from `tests/test_cut_off.py`, also with fonts a tenth
  wider); a new screen gets a line in that test.
- No exclamation marks except a greeting, no emoji, no jargon. Industry words are plain words here: Above the
  Line, fringes, top sheet.

## 8. The window

```
╭ cuánto. ─────────────╮  Production $763,843.33 (⌕ Search      ) (≡)   (⇪)(+)  ╭ Line          (⋯)(✕) ╮
│ Budgets ˅        (+) │  Acct #  Description          Amount Units Unit  Total │ 2700 Camera › 2701 … │
│ ▾ All Budgets      2 │  ▾ 2700  Camera                               $99,972  │ Director of Photo…   │
│     The Long Night   │  ▾ 2701  Camera Crew                          $68,772  │ $35,925.75           │
│   Rate Library    17 │          Director of Photography  1   35  Days $35,925 │ ╭ Cost ───────────╮  │
│ The Long Night ˅ (+) │          1st Assistant Camera     1   22  Days $12,545 │ ╭ Fringes ────────╮  │
│   Top Sheet    $1.6M │                                                         │ ╭ Rate Library ───╮  │
│   Production   $764K │  Above the Line  Below the Line  Fringes  Fees  Total   │ [     New Line    ]  │
╰──────────────────────╯                                                         ╰──────────────────────╯
```

Three columns: **where you are → a big table of it → the thing you picked, editable.**

- **The sidebar** (`ui/window/sidebar.py`): Budgets (All Budgets with each budget under it; the Rate Library), then
  a section named after the open budget: Top Sheet, Above the Line, Production, Post Production, Other, Globals,
  Fringes, each with its total or count. Each heading folds its section and has its own + (faded in over that
  section). The profile card sits at the bottom.
- **The toolbar**: the page's title and its total (or count); the search, centred, giving way before anything
  touches (then a money total shows short: "$764K"); the filter on pages that have one; the share button (the
  top sheet & detail, Excel, JSON, imports); the primary +, which makes the page's thing (a menu where it could be
  more than one).
- **The tables** (`ui/window/tables.py`): one delegate paints every row (its rounded highlight; the accent bands
  for sections, categories and departments; fold arrows). Bands and accounts fold, remembered. The top sheet and
  the detail keep the budget's order; the other tables sort by any column. A totals bar sits under a budget's tables.
- **Typing in the table**: double-click (or Return on) a line's Description, Amount, Units, Unit or Rate to type
  over it. It's the same text the line's panel shows (a number or a formula) and saves itself.
- **The right panel** floats on glass and only shows when something is picked. It slides in (`DOCK_MS`) and out on
  Esc, a click on empty space, or its ✕. Header: the title, ⋯, ✕. Body: Cards. Footer: the one main action.
- **Smaller windows**: the right panel narrows to `INSPECTOR_MIN`, table columns step aside in a set order
  (`GIVE_WAY`), the search shrinks to `SEARCH_MIN`.
- **Only show what applies**: an empty section isn't on the top sheet; Notes appear when they hold something or you
  add them; a fringe's cap only for a percent; a fee's "Of" only for a percent.
- **Nothing to save by hand.** Edits save `SAVE_DELAY_MS` after typing stops, on switching, and on quit. A new line,
  account, category, global, fringe, fee or rate you leave empty (Esc, or opening something else) isn't kept.
- **Removing goes through a menu or an alert**, never one click. The alert names what goes with it.
- **One popup at a time**: Settings edits in place; alerts are the only thing over another window.

## 9. The paper

Every page is laid out once in `doc/render.py` and painted on any device, so preview, PDF, PNG and print match.

- Sizes in points (Letter 612 × 792), `MARGIN` 44 all round, "Page N of M" in every footer.
- Reading order: who it's from (logo, name, tagline, contact) with **the grand total** large on the right in the
  paper's accent → a strip of four facts (production, type, shoot dates, prepared) → the blocks (client, company,
  location & format; the top sheet only) → the table → the totals → the notes → the profile's closing note.
- The **top sheet** lists categories by section (each section's name and total in the accent); the **detail** lists
  each category, its accounts and their lines, with each account's fringes. Lines, accounts and categories that
  come to nothing are left out of the detail.
- The paper has its own accent, picked per profile (`core/looks.py`, orange unless chosen): the app's accent never
  changes a page. Exports are always white; the Dark Page is for the preview only.
- Small labels are capitals with letter spacing; account codes are IBM Plex Mono. Headings stay with the row under
  them; table headers repeat on a new page; the totals stay together.

## 10. Checklist before you commit a UI change

1. No raw numbers or colors outside `tokens.py` (the grep above prints nothing).
2. New controls are `CONTROL_H` tall (or `SMALL_H`) and line up with their neighbours.
3. Every icon-only button has a tooltip.
4. Labels are short and in Title Case; sentences are plain sentences.
5. No words cut off: a new screen or state has a line in `tests/test_cut_off.py`, and it passes.
6. Screenshots look right in dark, light, and in Yellow:
   `QT_QPA_PLATFORM=offscreen python tests/screenshot.py OUT --look light --accent yellow`.
