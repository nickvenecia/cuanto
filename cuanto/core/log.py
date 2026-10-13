"""Troubleshooting log: a small rotating file in Cuánto's data folder.

Use ``log = get_logger(__name__)`` in any module. Nothing is ever sent anywhere.
Started from a terminal (`python -m cuanto`), the same lines also print there.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys

from cuanto.core.paths import log_dir

_configured = False


def setup_logging(level: int = logging.INFO, filename: str = "cuanto.log") -> None:
    """Write to <data dir>/logs/<filename> (1 MB x 3 files). Safe to call more than once."""
    global _configured
    if _configured:
        return
    _configured = True
    root = logging.getLogger("cuanto")
    root.setLevel(level)
    try:
        log_dir().mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = logging.handlers.RotatingFileHandler(
            log_dir() / filename, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
    except OSError:
        handler = logging.NullHandler()  # read-only home folder etc. — logging is optional
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)
    stream = sys.stderr
    if stream is not None and hasattr(stream, "isatty") and stream.isatty():
        console = logging.StreamHandler(stream)
        console.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%H:%M:%S")
        )
        root.addHandler(console)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name if name.startswith("cuanto") else f"cuanto.{name}")
