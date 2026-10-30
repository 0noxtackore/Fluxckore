# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Fluxckore (single edition, onefile).
# Run from the repository root:
#     pyinstaller packaging/fluxckore.spec --noconfirm

import subprocess
import sys
from pathlib import Path

SPEC_DIR = Path(SPECPATH).resolve()
ROOT = SPEC_DIR.parent

version_file = SPEC_DIR / "version_info.txt"
subprocess.run([sys.executable, str(SPEC_DIR / "make_version_info.py")], check=True)

a = Analysis(
    [str(ROOT / "fluxckore" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "fluxckore" / "frontend"), "fluxckore/frontend"),
        (str(ROOT / "locales" / "translations.json"), "locales"),
        (str(ROOT / "assets" / "sounds" / "notification.mp3"), "assets/sounds"),
        (str(ROOT / "assets" / "sounds" / "danger.mp3"), "assets/sounds"),
    ],
    hiddenimports=[
        "psutil",
        "winreg",
        "webview",
        "webview.platforms.edgechromium",
        "clr",
        "pythonnet",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "numpy", "tkinter", "pygame", "PIL", "cryptography"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="Fluxckore",
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
    uac_admin=False,
    icon=[str(SPEC_DIR / "fluxckore.ico")],
)
