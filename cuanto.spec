# PyInstaller recipe for Cuánto.   Build with:  pyinstaller cuanto.spec --noconfirm
import sys
from pathlib import Path

sys.path.insert(0, str(Path(SPECPATH)))
from cuanto import __version__  # noqa: E402

ROOT = Path(SPECPATH)
IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

datas = [(str(ROOT / "cuanto" / "assets"), "cuanto/assets")]
hiddenimports = [
    "PySide6.QtSvg", "PySide6.QtPrintSupport", "PySide6.QtNetwork", "openpyxl", "defusedxml",
    # the system keychain (the account sign-in): keyring finds its backends by name at run time
    "keyring.backends.macOS", "keyring.backends.Windows", "keyring.backends.SecretService",
    "keyring.backends.libsecret", "keyring.backends.chainer", "keyring.backends.fail",
]
from PyInstaller.utils.hooks import copy_metadata  # noqa: E402

datas += copy_metadata("keyring")  # its backends are listed in its package metadata

excludes = [
    "tkinter", "unittest", "pydoc_data", "numpy", "PIL", "fontTools",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtWebEngineCore", "PySide6.Qt3DCore", "PySide6.QtCharts",
    "PySide6.QtPdf", "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtDBus", "PySide6.QtOpenGL",
    "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtXml", "PySide6.QtConcurrent", "PySide6.QtMultimedia",
]

icon_png = ROOT / "cuanto" / "assets" / "icon.png"
icon = None
if IS_WIN:
    icon = str(ROOT / "build" / "icon.ico")
    Path(icon).parent.mkdir(exist_ok=True)
    from PIL import Image

    Image.open(icon_png).save(icon, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
elif IS_MAC:
    icon = str(icon_png)  # PyInstaller converts PNG -> icns via Pillow

a = Analysis(
    [str(ROOT / "launcher.py")],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=excludes,
    noarchive=False,
)


# ---- trim things Cuánto never uses (keeps the download smaller)
def _keep(entry) -> bool:
    d = entry[0].replace("\\", "/").lower()
    if "/qt/translations/" in d or d.endswith(".qm"):
        return False  # Qt's own UI translations (Cuánto's text is its own)
    if "opengl32sw" in d:
        return False  # Windows software-OpenGL fallback; Cuánto draws plain widgets
    for plug in ("/plugins/networkinformation/", "/plugins/qmltooling/", "/plugins/sqldrivers/", "/plugins/multimedia/"):
        if plug in d:
            return False
    return True


a.datas = [x for x in a.datas if _keep(x)]
a.binaries = [x for x in a.binaries if _keep(x)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Cuanto",
    console=False,
    icon=icon,
    upx=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
)

coll = COLLECT(exe, a.binaries, a.datas, name="Cuanto", upx=False)

if IS_MAC:
    app = BUNDLE(
        coll,
        name="Cuanto.app",
        icon=icon,
        bundle_identifier="io.github.nickvenecia.cuanto",
        version=__version__,
        info_plist={
            "CFBundleName": "Cuanto",
            "CFBundleDisplayName": "Cuánto",
            "CFBundleShortVersionString": __version__,
            "CFBundleVersion": __version__,
            "LSMinimumSystemVersion": "11.0",
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
            "LSApplicationCategoryType": "public.app-category.business",
        },
    )
