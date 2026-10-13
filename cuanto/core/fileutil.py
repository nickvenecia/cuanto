"""Showing a file in Finder / Explorer / the Linux file manager."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from cuanto.core.log import get_logger

log = get_logger(__name__)


def popen_kwargs() -> dict:
    """Keeps Windows from flashing a console window."""
    if sys.platform == "win32":
        return {"creationflags": 0x08000000}  # CREATE_NO_WINDOW
    return {}


def reveal(path: str | Path) -> None:
    """Open the folder with this file selected (Linux: just the folder)."""
    path = str(path)
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path])
        elif sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)], **popen_kwargs())
        else:
            target = path if os.path.isdir(path) else os.path.dirname(path)
            subprocess.Popen(["xdg-open", target])
    except OSError:
        log.warning("couldn't show %s", path, exc_info=True)


def zip_folder(folder: Path, dest: Path, skip: tuple[str, ...] = ()) -> int:
    """Copy everything in `folder` into the zip file `dest` (written beside it first, then swapped in).
    Top-level names in `skip` are left out. Returns how many files went in."""
    import zipfile

    folder, dest = Path(folder), Path(dest)
    tmp = dest.with_name(dest.name + ".part")
    n = 0
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(folder.rglob("*")):
            rel = path.relative_to(folder)
            if not path.is_file() or rel.parts[0] in skip or path in (tmp, dest):
                continue
            z.write(path, Path(folder.name) / rel)
            n += 1
    os.replace(tmp, dest)
    return n
