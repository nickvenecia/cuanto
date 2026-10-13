"""Design tokens: the ONLY place sizes, spacing, type and colors are defined.

Every widget, layout and stylesheet rule uses these names. If something needs a value
that isn't here, add a token (and document it in DESIGN.md) instead of typing a number.
"""

from __future__ import annotations

# ---------------------------------------------------------------- spacing (4-pt grid)
SPACE_1 = 4  # tight: a label and its control, an icon and its text
SPACE_2 = 8  # related items: buttons in a row, cards in the list, options in a stack
SPACE_3 = 12  # between groups (sections) inside a panel
SPACE_4 = 16  # padding of panels, bars and the main areas
SPACE_5 = 24  # padding of dialogs and the empty-state drop zone

# ---------------------------------------------------------------- control sizes
CONTROL_H = 34  # EVERY button, dropdown, text field and segmented control
SMALL_H = 24  # chips, small icon buttons inside rows and cards
SECTION_ADD = 20  # a sidebar section's plain + (a gray glyph, the Mac's size)
INDICATOR = 16  # standard icon size
TOGGLE_ROW_H = 32  # an on/off setting: label left, switch right
TOGGLE_W, TOGGLE_H = 36, 20  # the switch
TOGGLE_INSET = 3  # gap between the switch's track and its knob
ICON = 16
ICON_SM = 14
ICON_LG = 20  # a hero icon that must fill its circle
BAR_H = 6  # progress bars
TRACK_H = 4  # slider groove
HANDLE = 14  # slider handle
SCROLL_W = 10  # scrollbar width
SCROLL_GUTTER = SCROLL_W  # space always kept for it (see widgets.FitScroll)
SCROLL_MIN = 30  # shortest scrollbar handle

# ---------------------------------------------------------------- corner radius
RADIUS_XS = 4  # checkbox box
RADIUS_SM = 6  # chips, menu/list rows, small buttons
RADIUS = 8  # controls: buttons, fields, dropdowns, segmented controls
RADIUS_LG = 12  # cards, popups, panels inside dialogs

# ---------------------------------------------------------------- type scale (px)
TEXT_XS = 11  # chips
TEXT_SM = 12  # secondary text: file details, hints, tooltips
TEXT_MD = 13  # body text and every control (the default)
TEXT_LG = 14  # emphasized text: names in lists, alert titles, totals
TEXT_XL = 18  # dialog titles, empty-state headline
TEXT_TITLE = 24  # the page's large title (Top Sheet, Production)
TEXT_BRAND = 21  # the "cuánto." wordmark only
TEXT_TITLEBAR = 15  # the wordmark in the Mac title bar

WEIGHT_REGULAR = 400
WEIGHT_MEDIUM = 500  # controls
WEIGHT_SEMIBOLD = 600  # titles, labels, primary button
WEIGHT_BOLD = 700  # wordmark, dialog titles

# ---------------------------------------------------------------- layout
SIDEBAR_W = 232  # the sidebar: your budgets, the rate library, the open budget's places
INSPECTOR_W = 420  # the panel on the right where the picked thing is edited
INSPECTOR_MIN = 360  # …on a smaller window
INSPECTOR_SHARE = 0.27  # of the window's width, between those two
HEADER_H = 52  # a panel header that isn't level with a toolbar
TITLEBAR_H = 32  # Cuánto's own Mac title bar (fitted to the real one once the window shows)
SEG_INSET = 2  # gap between a segmented control's frame and its buttons
ROW_INDENT = 18  # lines under their account in the detail table
TEXT_BOX_H = 2 * CONTROL_H - SPACE_2  # a two-line text box (addresses)
CHIP_SM_H = SMALL_H - 6  # the small status chip
SCROLL_INSET = 2  # a scrollbar's handle sits this far inside its track
TEXT_BOX_TALL = 4 * CONTROL_H - SPACE_3  # notes
NUM_FIELD_W = 96  # amount / units / rate fields
QTY_FIELD_W = 64  # a quantity on its own
LOGO_THUMB = 40  # the logo preview in the profile form
LOGO_THUMB_MAX_W = 160
PAGE_GAP = 24  # space between preview pages
PAGE_SHADOW = 18  # blur of the paper's shadow in the preview
DIALOG_W = 480
DIALOG_W_WIDE = DIALOG_W + 2 * SPACE_5  # dialogs with a two-column form (profile)
DIALOG_W_XWIDE = DIALOG_W + 6 * SPACE_5  # the update window, the import window
SETTINGS_SIZE = (820, 620)  # the Settings window
SETTINGS_MIN = (680, 480)
SETTINGS_SIDE_W = 210  # its sidebar
ALERT_W = 300  # an alert (Delete …?), narrow like a Mac's
ALERT_ICON = 56  # the app icon at the top of it
PROFILE_DIALOG_H = 680  # the profile form: name, logo and contact show without scrolling
IMPORT_LIST_H = 320  # the list of what's coming in, in the Import window
PICKER_SIZE = (560, 620)  # picking from the rate library
WINDOW_SIZE = (1600, 1000)
WINDOW_MIN = (1280, 700)  # the toolbar, table and inspector all fit
TABLE_ROW_H = 34  # one row in every table
NAME_MIN = 240  # a table's name column never gets narrower; other columns step aside
FOLD_W = 28  # the column a row's fold arrow sits in
CHEVRON = 9  # a divider's open/closed chevron
GLASS_R = 18  # a floating glass panel's corners
GLASS_GAP = 10  # between the window's edge and its floating panels, and between panels
GLASS_SHADOW_STEPS = 16  # layers of a panel's shadow (soft, like the Mac's)
GLASS_SHADOW_SPREAD = 24  # how far it reaches: wide and faint, never a dark smudge
GLASS_SHADOW_DROP = 3  # how far below the panel it sits: barely
GLASS_EDGE_FADE = 60  # the hairline is brightest along the top, settling over this many px
DOCK_MS = 240  # the inspector sliding in or out
FADE_MS = 150  # small things appearing or going (a sidebar section's +): a quick fade, never a pop
LIFT_STEP_MS = 16  # dragging a row: how often the other rows move (about 60 a second)
LIFT_EASE = 0.3  # …and how far towards their new place each step (smaller is slower)
QUIT_WAIT_MS = 1500  # how long quitting waits for an update check to finish
SAVE_DELAY_MS = 400  # save this long after the last keystroke
TABLE_DELAY_MS = 350  # refresh the table this long after an edit
UPDATE_CHECK_DELAY_MS = 1500  # the automatic update check, just after the window is up (every launch)
UPDATE_WAIT_MS = 1500  # a found update waits this long between looks while another window is open
TOAST_MS = 3500  # how long a toast stays up
TOAST_MS_PER_CHAR = 60  # …or longer, for a long one: time to read it
TOAST_MAX_W = 520
TOAST_IN_MS = 220  # it rises and fades in…
TOAST_OUT_MS = 180  # …and fades away
TOAST_RISE = 10  # how far it rises as it comes in
TOAST_LIFT = SPACE_4  # its gap above the bottom of the page
NAV_GAP = 2  # between rows in the sidebar
ROW_INSET = 2  # a table row's rounded highlight sits this far inside the row
LINE_STROKE = 1.8  # drawn chevrons
ICON_STROKE = 2.0  # the icon set's line width
NOTES_H = 320  # what's new, in the update window: as tall as its words, up to this (then it scrolls)
NOTES_LINE = 140  # what's new: the line height, in % of the font size
PAGE_DIALOG_INSET = 80  # the page window stays this far inside the main window
PAGE_DIALOG_MIN_H = 600
PAGE_DIALOG_SIZE = (1100, 1000)  # the top sheet & detail window
PREVIEW_REFIT_MS = 120  # redraw the preview's pages this long after its window stops changing size
TRACK_BRAND = -0.5  # letter spacing (px): the wordmark
TRACK_TITLEBAR = -0.3
TRACK_TITLE = -0.4  # page titles
# the tables' fixed column widths
COL_W = {
    "code": 72, "kind": 130, "stage": 90, "updated": 120, "money": 120, "total": 130, "amount": 84,
    "units": 84, "unit": 80, "rate": 110, "fringes": 104, "value": 150, "result": 110, "used": 80,
    "cap": 110, "department": 150, "union": 150, "lines": 72,
}  # fmt: skip
ROW_R = 9  # a table row's rounded highlight
CHIP_H = 28  # a tinted capsule button
SORT_ARROW = 10  # the sort arrow in a column title
NAV_H = 30  # one row in the sidebar
NAV_INSET = SCROLL_GUTTER  # a sidebar row's gap from the glass edge (the scroll bar's room on the right)
NAV_R = GLASS_R - NAV_INSET  # its corners: concentric with the glass (the curves run parallel)
MENU_GAP = 6  # between a button and the menu it opens
# ---- every list of choices looks like the sidebar and Settings: menus, dropdown lists, pickers, suggestions.
# Rows sit LIST_INSET inside a list whose corners are LIST_R, so their corners (LIST_ROW_R) run parallel to it.
LIST_R = GLASS_R
LIST_INSET = NAV_INSET
LIST_ROW_R = NAV_R
LIST_ROW_H = NAV_H
LIST_GAP = NAV_GAP
AVATAR = 32  # your profile's initials, bottom of the sidebar
START_TILE_W = (
    184  # one way to start on an empty page (three fit beside the inspector on the smallest window)
)
START_BADGE = 40  # the circle behind a start tile's icon
PROFILE_CARD_H = 48
TOOLBAR_H = 64  # the bar above a table: title, search, New
SEARCH_W = 440  # the search capsule asks for this…
SEARCH_MIN = 160  # …and gives way down to this

# ---------------------------------------------------------------- colors: a dark and a light set
# The app follows the system (or View → Appearance). Read colors as tokens.X when drawing, never copy them
# into a constant at import: use() swaps them.
DARK = {
    "BG": "#1E1E1E",  # window background: the Mac's dark charcoal, not black
    "PANEL": "#1E1E1E",  # dialogs, footers
    "CARD": "#1F1E20",  # cards, fields
    "CARD_HOVER": "#262527",
    "CARD_SELECTED": "#392B23",  # a selected card (a hint of the accent)
    "RAISED": "#2B2A2C",  # buttons, popups
    "RAISED_HOVER": "#343335",
    "RAISED_PRESS": "#272628",
    "BORDER": "#2D2C2E",
    "BORDER_STRONG": "#3B3A3D",
    "BORDER_HOVER": "#4D4B4F",
    "BORDER_CHECK": "#5C5A5F",  # unchecked checkbox outline
    "TEXT": "#F4F2F1",
    "MUTED": "#A8A5A6",  # secondary text
    "FAINT": "#737072",  # hints, disabled, section labels
    "WELL": "#0C0B0C",  # sunken areas: thumbnails, previews, logs
    "ACCENT": "#F5893A",  # orange: selection, the one primary action, focus
    "ACCENT_HOVER": "#F69B58",
    "ACCENT_PRESS": "#D87933",
    "ON_ACCENT": "#141314",  # text/icons on the accent (white doesn't read on this orange)
    "ACCENT_OFF": "#463125",  # disabled primary button
    "ACCENT_OFF_TEXT": "#7F4E2C",
    "ACCENT_TINT": "rgba(245, 137, 58, 0.15)",  # an orange wash
    "ACCENT_EDGE": "rgba(246, 155, 88, 0.55)",
    "GOOD": "#4CC38A",
    "BAD": "#F0616D",  # late, failed, delete
    "BAD_TINT": "#2A1A1D",  # danger button hover
    "BAD_EDGE": "#5A2A30",  # failed card border
    "WARN": "#E0CB4A",  # amber shifted toward yellow, so it never reads as the orange accent
    "PAPER": "#FFFFFF",  # the paper (and logo thumbnails) in the preview
    "SHADOW": "rgba(0, 0, 0, 0.55)",  # the paper's shadow on the dark preview
    "DIVIDER": "#3E2E22",  # a category or section band in a table: an orange band
    "DIVIDER_TEXT": "#FABE93",  # its name and totals
    "DIVIDER_HOVER": "#493324",  # a band under the mouse: the same orange, a step brighter
    "ROW_HOVER": "rgba(255, 255, 255, 0.05)",  # a table row under the mouse
    "WINDOW_TOP": "#1E1E1E",  # the window's backdrop: flat, darker than the panels (as on the Mac)
    "WINDOW_BOTTOM": "#1E1E1E",
    "GLASS": "rgba(48, 47, 50, 0.92)",  # a floating panel (sidebar, inspector): one even tone, lighter than the page
    "GLASS_STROKE": "rgba(255, 255, 255, 0.10)",  # its one hairline: faintly lighter than the panel
    "GLASS_EDGE": "rgba(255, 255, 255, 0.18)",  # …a little brighter along the top, where light catches it
    "GLASS_SHADOW": "rgba(0, 0, 0, 0.35)",  # soft and wide
    "TOAST": "#3A393C",  # a toast: a step lighter than the panels, so it stands out over anything
    "TOAST_TEXT": "#F4F2F1",
    "TOAST_EDGE": "rgba(255, 255, 255, 0.12)",
    "TOAST_SHADOW": "rgba(0, 0, 0, 0.60)",  # …lifted by a deeper shadow than the panels'
    "TOAST_DONE": "#4CC38A",  # its icon: it worked
    "TOAST_PROBLEM": "#E0CB4A",  # …it didn't (amber: red means late or delete)
    "TOAST_PROBLEM_FILL": "#46411F",  # a problem's toast is tinted amber, so it's never missed
    "TOAST_PROBLEM_EDGE": "rgba(224, 203, 74, 0.45)",
    "CHIP": "rgba(245, 137, 58, 0.16)",  # a tinted capsule (+ Notes, + Line)
    "CHIP_HOVER": "rgba(245, 137, 58, 0.26)",
    "FIELD": "rgba(255, 255, 255, 0.07)",  # a text field or dropdown: lightly frosted
    "FIELD_BORDER": "rgba(255, 255, 255, 0.08)",
    "BLOCK": "rgba(255, 255, 255, 0.045)",  # a card inside a glass panel: a soft tint, no outline
    "FILL": "rgba(255, 255, 255, 0.045)",  # a soft fill on the page: a switch's track, weekends, a placeholder
}
LIGHT = {
    "BG": "#FFFFFF",
    "PANEL": "#FFFFFF",
    "CARD": "#FFFFFF",
    "CARD_HOVER": "#F2F2F4",
    "CARD_SELECTED": "#F9EFE7",
    "RAISED": "#FFFFFF",
    "RAISED_HOVER": "#F5F5F7",
    "RAISED_PRESS": "#E8E8EC",
    "BORDER": "#E5E5EA",
    "BORDER_STRONG": "#D8D8DD",
    "BORDER_HOVER": "#B8B8BF",
    "BORDER_CHECK": "#A2A2AA",
    "TEXT": "#1D1D1F",
    "MUTED": "#6E6E73",
    "FAINT": "#A1A1A6",
    "WELL": "#EDEDF0",
    "ACCENT": "#C2600E",
    "ACCENT_HOVER": "#C87026",
    "ACCENT_PRESS": "#A5520C",
    "ON_ACCENT": "#FFFFFE",
    "ACCENT_OFF": "#F3DFCF",
    "ACCENT_OFF_TEXT": "#E0B086",
    "ACCENT_TINT": "rgba(194, 96, 14, 0.09)",
    "ACCENT_EDGE": "rgba(194, 96, 14, 0.45)",
    "GOOD": "#1E9A5E",
    "BAD": "#D3374A",
    "BAD_TINT": "#FBEAEC",
    "BAD_EDGE": "#EFB7BF",
    "WARN": "#988000",
    "PAPER": "#FFFFFF",
    "SHADOW": "rgba(0, 0, 0, 0.16)",
    "DIVIDER": "#F6E7DB",
    "DIVIDER_TEXT": "#A5520C",
    "DIVIDER_HOVER": "#F2DCCA",
    "ROW_HOVER": "rgba(0, 0, 0, 0.04)",
    "WINDOW_TOP": "#FFFFFF",
    "WINDOW_BOTTOM": "#FFFFFF",
    "GLASS": "rgba(242, 242, 245, 0.94)",
    "GLASS_STROKE": "rgba(0, 0, 0, 0.06)",  # a very faint gray hairline
    "GLASS_EDGE": "rgba(0, 0, 0, 0.04)",  # (fainter still along the top)
    "GLASS_SHADOW": "rgba(0, 0, 0, 0.08)",  # soft and wide
    "TOAST": "#2C2C2E",  # dark on the white page: easy to spot
    "TOAST_TEXT": "#FFFFFF",
    "TOAST_EDGE": "rgba(255, 255, 255, 0.10)",
    "TOAST_SHADOW": "rgba(0, 0, 0, 0.30)",
    "TOAST_DONE": "#4CC38A",  # (the dark look's: these sit on the dark toast)
    "TOAST_PROBLEM": "#E0CB4A",
    "TOAST_PROBLEM_FILL": "#46411F",
    "TOAST_PROBLEM_EDGE": "rgba(224, 203, 74, 0.45)",
    "CHIP": "rgba(194, 96, 14, 0.10)",
    "CHIP_HOVER": "rgba(194, 96, 14, 0.18)",
    "FIELD": "rgba(255, 255, 255, 1.0)",
    "FIELD_BORDER": "rgba(0, 0, 0, 0.10)",
    "BLOCK": "rgba(255, 255, 255, 0.85)",  # white cards on the gray glass
    "FILL": "rgba(0, 0, 0, 0.045)",  # light gray on white
}
# ---------------------------------------------------------------- the accent you pick (Settings › General)
# Cuánto's own is orange, hand-set in DARK / LIGHT above. The others are built from one color by accent_set().
# Never red: red means over, failed or delete.
APP_ACCENT = "orange"
ACCENTS = {  # key -> (name, on dark, on light); the app's own first, then the shared choices in order
    "orange": ("Orange", "#F5893A", "#C2600E"),
    "blue": ("Blue", "#4A90F7", "#2F6FDB"),
    "purple": ("Purple", "#8069F7", "#6A52E8"),
    "pink": ("Pink", "#F25FA6", "#C9387F"),
    "yellow": ("Yellow", "#EDBA3A", "#9C7104"),
    "green": ("Green", "#3DBE6E", "#1B8747"),
    "turquoise": ("Turquoise", "#2EBFB0", "#0D8178"),
    "graphite": ("Graphite", "#9B999F", "#68666D"),
}
SWATCH = 22  # a color circle in Settings
SWATCH_RING = 2  # the ring around the chosen one (and the gap inside it)
DARK_ON_ACCENT = "#141314"  # words on a light accent (yellow, green…), where white wouldn't read


def _rgb(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, round(v))):02X}" for v in rgb)


def _mix(c: str, into: str, amount: float) -> str:
    """`amount` of color c mixed into `into`."""
    a, b = _rgb(c), _rgb(into)
    return _hex(x * amount + y * (1 - amount) for x, y in zip(a, b, strict=True))


def _rgba(c: str, alpha: float) -> str:
    r, g, b = _rgb(c)
    return f"rgba({r}, {g}, {b}, {alpha:g})"


def luminance(c: str) -> float:
    """Relative luminance (WCAG), 0 black … 1 white."""

    def ch(v: int) -> float:
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = _rgb(c)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def accent_set(base: str, scheme: str) -> dict[str, str]:
    """Every accent token for one color, in the dark or light look (the same steps as the hand-set orange)."""
    light = scheme == "light"
    on = "#FFFFFF" if contrast("#FFFFFF", base) >= 3 else DARK_ON_ACCENT
    if light:
        return {
            "ACCENT": base,
            "ACCENT_HOVER": _mix(base, "#FFFFFF", 0.9),
            "ACCENT_PRESS": _mix(base, "#000000", 0.85),
            "ON_ACCENT": "#FFFFFE" if on == "#FFFFFF" else on,
            "ACCENT_OFF": _mix(base, "#FFFFFF", 0.2),
            "ACCENT_OFF_TEXT": _mix(base, "#FFFFFF", 0.5),
            "ACCENT_TINT": _rgba(base, 0.09),
            "ACCENT_EDGE": _rgba(base, 0.45),
            "CARD_SELECTED": _mix(base, "#FFFFFF", 0.1),
            "DIVIDER": _mix(base, "#FFFFFF", 0.15),
            "DIVIDER_TEXT": _mix(base, "#000000", 0.85),
            "DIVIDER_HOVER": _mix(base, "#FFFFFF", 0.22),
            "CHIP": _rgba(base, 0.10),
            "CHIP_HOVER": _rgba(base, 0.18),
        }
    return {
        "ACCENT": base,
        "ACCENT_HOVER": _mix(base, "#FFFFFF", 0.85),
        "ACCENT_PRESS": _mix(base, "#000000", 0.88),
        "ON_ACCENT": on,
        "ACCENT_OFF": _mix(base, DARK["CARD"], 0.18),
        "ACCENT_OFF_TEXT": _mix(base, DARK["CARD"], 0.45),
        "ACCENT_TINT": _rgba(base, 0.15),
        "ACCENT_EDGE": _rgba(_mix(base, "#FFFFFF", 0.85), 0.55),
        "CARD_SELECTED": _mix(base, DARK["CARD"], 0.12),
        "DIVIDER": _mix(base, DARK["BG"], 0.15),
        "DIVIDER_TEXT": _mix(base, "#FFFFFF", 0.55),
        "DIVIDER_HOVER": _mix(base, DARK["BG"], 0.2),
        "CHIP": _rgba(base, 0.16),
        "CHIP_HOVER": _rgba(base, 0.26),
    }


SCHEME = "dark"
ACCENT_KEY = APP_ACCENT
globals().update(DARK)


def use(scheme: str, accent: str | None = None) -> None:
    """Switch every color token to the dark or light set, in the chosen accent (None keeps the current one;
    an unknown or empty one means Cuánto's own)."""
    global SCHEME, ACCENT_KEY
    SCHEME = "light" if scheme == "light" else "dark"
    if accent is not None:
        ACCENT_KEY = accent if accent in ACCENTS else APP_ACCENT
    globals().update(LIGHT if SCHEME == "light" else DARK)
    if ACCENT_KEY != APP_ACCENT:
        _name, dark, light = ACCENTS[ACCENT_KEY]
        globals().update(accent_set(light if SCHEME == "light" else dark, SCHEME))


def accent_of(key: str, scheme: str | None = None) -> str:
    """A choice's color in the dark or light look (the current one by default)."""
    _name, dark, light = ACCENTS.get(key, ACCENTS[APP_ACCENT])
    return light if (scheme or SCHEME) == "light" else dark
