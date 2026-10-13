"""Shared test setup: an offscreen Qt app and a throwaway data folder for every test.

Qt objects made during the UI tests can crash while Python tears itself down after the last test,
turning a green run red in CI. Once every test has finished, leave with pytest's own result.
"""

from __future__ import annotations

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_status = {"code": 0}


def pytest_sessionfinish(session, exitstatus):
    _status["code"] = int(exitstatus)


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config):
    if "PySide6.QtWidgets" in sys.modules:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(_status["code"])


@pytest.fixture(autouse=True)
def data_folder(tmp_path):
    """Never touch the real gear: every test gets its own empty data folder."""
    from cuanto.core.paths import use_data_dir

    use_data_dir(tmp_path / "data")
    yield tmp_path / "data"
    use_data_dir(None)


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv[:1])
    from cuanto.app import setup_app

    setup_app(app)
    return app


@pytest.fixture(autouse=True)
def _no_leftover_windows():
    """Windows a test made are gone before the next one (otherwise every later restyle redoes them all)."""
    yield
    if "PySide6.QtWidgets" not in sys.modules:
        return
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        return
    from PySide6.QtCore import Qt

    for w in app.topLevelWidgets():
        if w.windowType() in (Qt.WindowType.Popup, Qt.WindowType.ToolTip):
            continue  # a type-ahead list or a menu belongs to its owner, which deletes it (twice would crash)
        w.close()
        w.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
