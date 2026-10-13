"""App entry point: fonts, stylesheet, rounded popups, one window at a time, and --smoke-test."""

from __future__ import annotations

import logging
import os
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractScrollArea,
    QAbstractSlider,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QLabel,
    QMenu,
    QScrollBar,
    QWidget,
)

from cuanto import APP_NAME, __version__
from cuanto.core.log import get_logger, setup_logging
from cuanto.core.paths import ASSETS, data_dir, log_dir, use_data_dir
from cuanto.ui.components.widgets import ComboItemDelegate
from cuanto.ui.style import theme, tokens

log = get_logger(__name__)


def _server_name() -> str:
    import getpass

    try:
        user = getpass.getuser()
    except Exception:
        user = "user"
    return f"cuanto-{user}"


def _wake_running() -> bool:
    """If Cuánto is already open, bring its window forward and return True (one window, one set of files)."""
    from PySide6.QtNetwork import QLocalSocket

    sock = QLocalSocket()
    sock.connectToServer(_server_name())
    if not sock.waitForConnected(1500):
        return False
    sock.write(b"show\n")
    sock.flush()
    sock.waitForBytesWritten(1500)
    sock.disconnectFromServer()
    return True


def _listen(window) -> object:
    from PySide6.QtNetwork import QLocalServer

    name = _server_name()
    QLocalServer.removeServer(name)  # clear a stale socket from a crash
    server = QLocalServer(window)
    server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)  # only this user's account
    if not server.listen(name):
        return None

    def on_conn() -> None:
        sock = server.nextPendingConnection()

        def read() -> None:
            sock.readAll()  # the message is always "show"; anything else is ignored
            if window.isMinimized():
                window.showNormal()
            window.raise_()
            window.activateWindow()
            sock.disconnectFromServer()

        sock.readyRead.connect(read)
        sock.disconnected.connect(sock.deleteLater)

    server.newConnection.connect(on_conn)
    return server


def place_menu(menu: QWidget, button: QWidget) -> None:
    """A button's menu opens just below it, with a little air between: lined up with its left edge, or, for a
    button on the right of the window, with its right edge (so it never runs off past the window)."""
    size = menu.size()
    top_left = button.mapToGlobal(QPoint(0, 0))
    win = button.window()
    on_right = button.mapTo(win, button.rect().center()).x() > win.width() / 2
    x = top_left.x() + button.width() - size.width() if on_right else top_left.x()
    y = top_left.y() + button.height() + tokens.MENU_GAP
    screen = button.screen().availableGeometry() if button.screen() else None
    if screen is not None:
        if y + size.height() > screen.bottom():  # no room below: above it instead
            y = top_left.y() - size.height() - tokens.MENU_GAP
        x = max(screen.left(), min(x, screen.right() - size.width()))
    menu.move(x, y)


class _RoundPopups(QObject):
    """Qt gives menus and dropdown lists square windows; make them see-through so the
    stylesheet's rounded corners are what you actually see. A button's menu opens just below it, with a
    little air (place_menu); so does a dropdown's list. Also: scrolling never changes a value
    (dropdowns, dates and sliders pass the wheel on to the panel, which scrolls instead)."""

    @staticmethod
    def _see_through(win: QWidget) -> None:
        if not win.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground):
            win.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
            win.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
            win.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def eventFilter(self, obj, ev):
        wheel_on_control = isinstance(obj, (QComboBox, QAbstractSlider, QAbstractSpinBox)) and not isinstance(
            obj, QScrollBar
        )
        if ev.type() == QEvent.Type.Wheel and wheel_on_control:
            area = obj.parent()
            while area is not None and not isinstance(area, QAbstractScrollArea):
                area = area.parent()
            if area is not None:
                QApplication.sendEvent(area.verticalScrollBar(), ev)
            return True
        if ev.type() == QEvent.Type.Show and isinstance(obj, QWidget) and obj.isWindow():
            owner = obj.parentWidget()
            if (
                isinstance(obj, QMenu)
                and isinstance(owner, QAbstractButton)
                and getattr(owner, "menu", lambda: None)() is obj
            ):
                place_menu(obj, owner)
            elif obj.inherits("QComboBoxPrivateContainer") and isinstance(owner, QComboBox):
                below = owner.mapToGlobal(QPoint(0, owner.height()))
                if obj.y() >= below.y() - 1:  # opened below the box: leave the same air
                    obj.move(obj.x(), below.y() + tokens.MENU_GAP)
        if ev.type() == QEvent.Type.Polish and isinstance(obj, QWidget):
            if (
                isinstance(obj, QLabel)
                and obj.textFormat() == Qt.TextFormat.AutoText
                and not obj.inherits("QTipLabel")
            ):  # names are shown as typed: a line called "<img …>" mustn't turn into a picture
                obj.setTextFormat(Qt.TextFormat.PlainText)
            if (isinstance(obj, QMenu) and obj.isWindow()) or obj.inherits("QTipLabel"):
                self._see_through(obj)
            elif isinstance(obj, QComboBox):
                if not isinstance(obj.itemDelegate(), ComboItemDelegate):
                    obj.setItemDelegate(ComboItemDelegate(obj))
                container = obj.view().window()
                if container is not obj.window():
                    self._see_through(container)  # its look is in theme.py (QComboBoxPrivateContainer)
        return False


_crash_file = None


def _log_uncaught() -> None:
    import threading

    previous = sys.excepthook

    def hook(kind, value, tb):
        log.error("unexpected error", exc_info=(kind, value, tb))
        if previous is not None:
            previous(kind, value, tb)

    sys.excepthook = hook
    threading.excepthook = lambda a: log.error(
        "unexpected error in %s", a.thread.name if a.thread else "a thread",
        exc_info=(a.exc_type, a.exc_value, a.exc_traceback),
    )  # fmt: skip


def _crash_log() -> None:
    global _crash_file
    import faulthandler

    try:
        log_dir().mkdir(parents=True, exist_ok=True)
        _crash_file = open(log_dir() / "crash.log", "a", encoding="utf-8")  # noqa: SIM115 — open for the app's life
        faulthandler.enable(_crash_file, all_threads=True)
    except OSError:
        log.debug("no crash log", exc_info=True)


def setup_app(app: QApplication) -> None:
    """Fonts, stylesheet and look (also used by the tests and screenshots)."""
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName("Cuanto")  # (the settings and data folder name: plain letters)
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")
    icon_path = ASSETS / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    family = theme.load_fonts()
    f = QFont(family or app.font().family())
    f.setPixelSize(tokens.TEXT_MD)  # every size is in pixels (the stylesheet's too), so they match
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app.setFont(f)
    from cuanto.core.store import read_json

    saved = read_json(data_dir() / "settings.json", {})
    saved = saved if isinstance(saved, dict) else {}
    appearance, accent = saved.get("appearance", "system"), saved.get("accent", "")
    set_appearance(
        app,
        appearance if isinstance(appearance, str) else "system",
        accent if isinstance(accent, str) else "",
    )
    hints = app.styleHints()
    if hasattr(hints, "colorSchemeChanged"):
        hints.colorSchemeChanged.connect(lambda _s: _system_changed(app))
    app._round = _RoundPopups(app)
    app.installEventFilter(app._round)


def set_appearance(app: QApplication, appearance: str, accent: str | None = None) -> str:
    """Light, dark, or "system" (follow the computer), and the accent ("" = Cuánto's own; None keeps it).
    Redraws open windows."""
    app._appearance = appearance
    app._applying = True  # asking the system can itself report a change
    try:
        look = theme.apply(app, appearance, data_dir() / "ui", accent)
    finally:
        app._applying = False
    for w in app.topLevelWidgets():
        if hasattr(w, "look_changed"):
            w.look_changed()
    return look


def _system_changed(app: QApplication) -> None:
    if getattr(app, "_appearance", "system") == "system" and not getattr(app, "_applying", False):
        set_appearance(app, "system")


def _smoke(app: QApplication) -> int:
    """Used by the build pipeline: open the window on a throwaway data folder with the sample budgets, save the
    open budget's top sheet and detail as a PDF and as Excel, check the files, quit."""
    from cuanto.core import sample, sheets
    from cuanto.core.store import Library
    from cuanto.doc import export
    from cuanto.ui.window.main_window import MainWindow

    tmp = Path(tempfile.mkdtemp(prefix="cuanto-smoke-"))
    use_data_dir(tmp)
    lib = sample.fill(Library(tmp).load())
    w = MainWindow(lib)
    w.show()
    first = lib.ordered_budgets()[0]
    w.go(f"budget:{first.id}")
    w.go("sec:production")
    out = tmp / "smoke.pdf"
    export.to_pdf(w.page_list(which="both"), out)
    ok = out.exists() and out.stat().st_size > 1000 and out.read_bytes().startswith(b"%PDF")
    xlsx = tmp / "smoke.xlsx"
    try:
        sheets.write_xlsx(first, xlsx)  # spreadsheets must work in the packaged app
        ok = ok and xlsx.stat().st_size > 1000
    except Exception:
        log.warning("smoke: Excel failed", exc_info=True)
        ok = False
    print(
        f"smoke: Cuanto {__version__}, PDF {'ok' if ok else 'MISSING'} ({out.stat().st_size if out.exists() else 0} bytes)",
        flush=True,
    )
    QTimer.singleShot(1200, app.quit)
    code = app.exec()
    return code if ok else 3


def _ask_to_sign_in(window) -> None:
    """Once accounts exist and are required (services/account.py REQUIRED), ask at launch."""
    from cuanto.services import account

    if account.REQUIRED and account.service().connected and account.current() is None:
        from cuanto.ui.dialogs.account import SignInDialog

        QTimer.singleShot(0, lambda: SignInDialog(window).exec())


def main() -> int:
    if sys.platform == "win32":
        try:  # own taskbar icon instead of python's
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Cuanto.Cuanto")
        except Exception:
            log.debug("couldn't set the Windows app id", exc_info=True)
    smoke = "--smoke-test" in sys.argv
    if smoke:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    setup_logging()
    log.info("Cuánto %s starting (%s)", __version__, sys.platform)
    _crash_log()
    _log_uncaught()
    app = QApplication(sys.argv)
    if not smoke and _wake_running():
        return 0  # Cuánto is already open: it came to the front
    setup_app(app)
    if smoke:
        return _smoke(app)

    from cuanto.ui.window.main_window import MainWindow

    w = MainWindow()
    app.aboutToQuit.connect(w.shutdown)
    app._server = _listen(w)
    w.show()
    w.raise_()
    _ask_to_sign_in(w)
    code = app.exec()
    if app.property("exit_now"):  # a download was still running: leave without waiting for it
        logging.shutdown()
        os._exit(code)
    return code


if __name__ == "__main__":
    sys.exit(main())
