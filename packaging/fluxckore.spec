# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Fluxckore (single edition, onefile).
# Run from the repository root: 
#     pyinstaller packaging/fluxckore.spec --noconfirm
# Relative paths are resolved against this spec file's directory.

import subprocess
import sys
from pathlib import Path

SPEC_DIR = Path(SPECPATH).resolve()
ROOT = SPEC_DIR.parent

# Make sure the Windows version resource exists and matches fluxckore.__version__.
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
        "clr_loader",
        "System",
        "System.Windows.Forms",
        "System.Drawing",
        "System.Threading",
        "System.Collections",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # pygame is not used any more (sounds go through the Windows MCI API):
    # excluding it keeps the SDL DLLs (~21 MB) out of the portable bundle,
    # which makes the ZIP smaller and the first launch faster.
    # cryptography is only imported by pywebview when it is asked to generate
    # an HTTPS certificate (``webview.start(ssl=True)``), which this app never
    # does: excluding it removes another ~15 MB (Rust extension + OpenSSL).
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
    # The window must run unprivileged: elevated WebView2 is unreliable (it can
    # start but never paint) and it forces a UAC prompt on every launch. The
    # cleaning elevates only its own hidden worker, see core/headless.py.
    uac_admin=False,
    icon=[str(SPEC_DIR / "fluxckore.ico")],
)

# No COLLECT - onefile exe will include everything needed.