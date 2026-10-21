# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Fluxop (single edition, onedir).
# Run from the repository root:
#     pyinstaller packaging/fluxop.spec --noconfirm
# Relative paths are resolved against this spec file's directory.

import subprocess
import sys
from pathlib import Path

SPEC_DIR = Path(SPECPATH).resolve()
ROOT = SPEC_DIR.parent

# Make sure the Windows version resource exists and matches fluxop.__version__.
version_file = SPEC_DIR / "version_info.txt"
subprocess.run([sys.executable, str(SPEC_DIR / "make_version_info.py")], check=True)

a = Analysis(
    [str(ROOT / "fluxop" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "fluxop" / "frontend"), "fluxop/frontend"),
        (str(ROOT / "locales" / "translations.json"), "locales"),
        (str(ROOT / "assets" / "sounds" / "notification.mp3"), "assets/sounds"),
        (str(ROOT / "assets" / "sounds" / "danger.mp3"), "assets/sounds"),
    ],
    hiddenimports=[
        "psutil",
        "winreg",
        "pygame",
        "webview",
        "webview.platforms.edgechromium",
        "clr",
        "pythonnet",
        "System",
        "System.Windows.Forms",
        "System.Drawing",
        "System.Threading",
        "System.Collections",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "numpy", "tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Fluxop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(version_file),
    uac_admin=True,
    icon=[str(SPEC_DIR / "fluxop.ico")],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Fluxop",
)
