"""Where Cuánto keeps its own files on each operating system."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_override: Path | None = None

ASSETS = Path(__file__).resolve().parent.parent / "assets"  # fonts, icon: shipped inside the app


def use_data_dir(path: Path | None) -> None:
    """Point Cuánto at another data folder (tests, the smoke test). None goes back to the normal one."""
    global _override
    _override = path


def data_dir() -> Path:
    """Per-user folder for budgets, rates, profiles, logos and logs (never inside the app bundle)."""
    if _override is not None:
        return _override
    env = os.environ.get("CUANTO_DATA_DIR")
    if env:
        return Path(env)
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "Cuanto"
    if sys.platform.startswith("win"):
        return Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local")) / "Cuanto"
    return Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share")) / "cuanto"


def budgets_dir() -> Path:
    return data_dir() / "budgets"


def logos_dir() -> Path:
    return data_dir() / "logos"


def log_dir() -> Path:
    return data_dir() / "logs"


def documents_dir() -> Path:
    """Where exports go by default: Documents/Cuanto."""
    docs = Path.home() / "Documents"
    return (docs if docs.is_dir() else Path.home()) / "Cuanto"
