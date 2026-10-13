"""Cuánto without a window: the same pages and numbers, from a terminal or another tool.

python -m cuanto cli sample OUT.pdf [--budget feature|commercial] [--doc topsheet|detail|both] [--dark]
python -m cuanto cli pdf BUDGET.json OUT.pdf [--doc topsheet|detail|both]
python -m cuanto cli totals BUDGET.json                      every number, as exchange-format JSON
python -m cuanto cli template feature|short|commercial|music_video|blank OUT.json [--name NAME]
python -m cuanto cli csv LINES.csv OUT.pdf|OUT.xlsx|OUT.json [--name NAME]

BUDGET.json is a budget exported from Cuánto (File › Export JSON…) or one of its own saved files.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

DOCS = ("topsheet", "detail", "both")


def _budget(path: Path):
    from cuanto.core import exchange
    from cuanto.core.model import Budget

    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict) and data.get("format"):
        return exchange.budget_from(exchange.check(data, path.name), set())
    if isinstance(data, dict):
        return Budget.from_dict(data)
    raise ValueError(f"{path.name} isn't a budget.")


def _write(budget, out: Path, doc: str, dark: bool, profile=None) -> None:
    from cuanto.core import document, exchange, sheets
    from cuanto.core.looks import DEFAULT_COLOR, palette
    from cuanto.core.store import write_json
    from cuanto.doc import export, render

    suffix = out.suffix.lower()
    if suffix == ".json":
        write_json(out, exchange.export_budget(budget))
    elif suffix == ".xlsx":
        sheets.write_xlsx(budget, out, profile.name if profile else "")
    else:
        views = document.build(budget, profile, doc)
        pages = render.layout_all(views, palette(profile.color if profile else DEFAULT_COLOR, dark))
        if suffix == ".png":
            export.to_png(pages, out)
        else:
            export.to_pdf(pages, out, title=budget.name)
        print(f"wrote {out} ({len(pages)} page{'s' if len(pages) != 1 else ''})", flush=True)
        return
    print(f"wrote {out}", flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cuanto cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample", help="a made-up budget's pages as PDF or PNG")
    s.add_argument("out")
    s.add_argument("--budget", choices=("feature", "commercial"), default="feature")
    s.add_argument("--doc", choices=DOCS, default="both")
    s.add_argument("--dark", action="store_true", help="the preview's Dark Page colors")
    p = sub.add_parser("pdf", help="a budget file's pages as PDF or PNG")
    p.add_argument("budget")
    p.add_argument("out")
    p.add_argument("--doc", choices=DOCS, default="both")
    t = sub.add_parser("totals", help="every number in a budget file, as JSON")
    t.add_argument("budget")
    m = sub.add_parser("template", help="a new budget from a template, as JSON")
    m.add_argument("kind", choices=("feature", "short", "commercial", "music_video", "blank"))
    m.add_argument("out")
    m.add_argument("--name", default="")
    c = sub.add_parser("csv", help="budget lines from a CSV file, as PDF, Excel or JSON")
    c.add_argument("sheet")
    c.add_argument("out")
    c.add_argument("--name", default="")
    args = ap.parse_args(argv)

    from cuanto.core import exchange, sample, sheets, templates
    from cuanto.core.paths import use_data_dir
    from cuanto.core.store import Library

    if args.cmd == "totals":
        sys.stdout.write(
            json.dumps(exchange.export_budget(_budget(Path(args.budget))), ensure_ascii=False, indent=2)
        )
        sys.stdout.write("\n")
        return 0
    if args.cmd == "template":
        _write(templates.build(args.kind, args.name), Path(args.out), "both", False)
        return 0

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])  # noqa: F841 — fonts need an app
    from cuanto.doc import fonts

    fonts.load_bundled()
    if args.cmd == "sample":
        tmp = Path(tempfile.mkdtemp(prefix="cuanto-cli-"))
        use_data_dir(tmp)
        lib = sample.fill(Library(tmp).load())
        b = next(x for x in lib.budgets.values() if x.kind == args.budget)
        _write(b, Path(args.out), args.doc, args.dark, lib.profile(b))
    elif args.cmd == "pdf":
        _write(_budget(Path(args.budget)), Path(args.out), args.doc, False)
    else:
        sheet = Path(args.sheet)
        b = templates.build("blank", args.name or sheet.stem)
        got = sheets.read_csv(sheet)
        sheets.merge_into(b, got)
        print(f"read {got.lines} lines ({got.skipped} skipped)", flush=True)
        _write(b, Path(args.out), "both", False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
