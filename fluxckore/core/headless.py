"""Hidden maintenance mode: ``Fluxckore.exe --clean=cat1,cat2 --lang=es``.

The window always runs as a normal user: WebView2 is much more reliable that
way and the user is not asked for administrator rights just to open the app.
Only the cleaning needs those rights, so when a run starts the GUI launches
this headless mode through ``ShellExecuteW("runas")`` and follows the shared
progress log. The elevated copy never creates a window, a splash or a WebView2
instance: it just runs the maintenance functions and writes their messages.

Protocol of ``clean-run.log``: one ``kind<TAB>message`` per line, where
``kind`` is a log level (``info``/``success``/``warning``/``error``) or one of
the control markers below. The file is truncated at the start of the run.
"""
from __future__ import annotations

import ctypes
import os
import sys
import traceback

from . import maintenance

DONE = "#done"
SUMMARY = "#summary"

LOG_KINDS = ("info", "success", "warning", "error")


def log_path() -> str:
    """Shared progress file, writable by both the GUI and the elevated copy."""
    base = os.environ.get("LOCALAPPDATA") or os.path.join(
        os.path.expanduser("~"), "AppData", "Local"
    )
    folder = os.path.join(base, "Fluxckore")
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        folder = os.environ.get("TEMP") or os.getcwd()
    return os.path.join(folder, "clean-run.log")


def launch_elevated(categories, lang: str = "") -> bool:
    """Start the headless cleaning elevated. False when the user declines."""
    if os.name != "nt":
        return False

    params = "--clean=" + ",".join(categories)
    if lang:
        params += " --lang=" + lang

    executable = sys.executable
    if not getattr(sys, "frozen", False):
        # Source checkout: the entry point is the module, not the interpreter.
        params = "-m fluxckore " + params

    try:
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", executable, params, None, 0  # 0 = SW_HIDE
        )
    except Exception:
        return False
    # ShellExecuteW returns a value > 32 when the operation started; 1223 means
    # the user cancelled the UAC prompt.
    return int(result) > 32


def run_clean(spec: str, lang: str = "") -> int:
    """Run the cleaning and write the progress log. Returns a process code."""
    path = log_path()
    try:
        with open(path, "w", encoding="utf-8"):
            pass
    except OSError:
        return 1

    def log(message, kind="info"):
        try:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(f"{kind}\t{message}\n")
        except OSError:
            pass

    try:
        if lang:
            from ..i18n import TranslationManager

            TranslationManager()
            TranslationManager.set_language(lang)

        known = {category["id"] for category in maintenance.file_categories()}
        selected = [
            item for item in str(spec or "").split(",") if item in known
        ] or maintenance.default_categories()

        stats = maintenance.MaintenanceStats()
        maintenance.optimize_ram(log)
        maintenance.optimize_cpu(log)
        maintenance.clean_selected(selected, log, stats)
        maintenance.flush_dns_cache(log)
        log(f"{stats.space_freed_mb:.2f}\t{stats.files_deleted}", SUMMARY)
    except Exception:
        log(traceback.format_exc(limit=4).replace("\n", " | ").strip(), "error")
    finally:
        log("ok", DONE)
    return 0
