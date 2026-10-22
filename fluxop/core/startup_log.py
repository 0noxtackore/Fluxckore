"""Timestamped startup log used to diagnose launch problems.

The frozen build is a windowed executable: it has no console, so ``print``
output is lost and a crash before the window appears leaves no trace at all.
Every phase of the startup writes to this plain-text log instead.

The file is stored next to the executable when that folder is writable and
in ``%LOCALAPPDATA%\\Fluxop`` otherwise, so a user can always find it and
send it back even when the window never shows up.

Nothing here may raise: logging must never be the reason the app fails.
"""
from __future__ import annotations

import os
import sys
import threading
import time
import traceback
from datetime import datetime

_LOCK = threading.Lock()
_PATH: str | None = None
_STARTED = time.monotonic()

# Rotate instead of growing forever (the stats loop can log for hours).
_MAX_BYTES = 512 * 1024


def _candidates():
    """Folders to try, in order of usefulness for troubleshooting."""
    if getattr(sys, "frozen", False):
        yield os.path.dirname(os.path.abspath(sys.executable))
    local = os.environ.get("LOCALAPPDATA")
    if local:
        yield os.path.join(local, "Fluxop")
    yield os.environ.get("TEMP") or os.getcwd()


def log_path() -> str:
    """Absolute path of the startup log (first writable candidate)."""
    global _PATH
    if _PATH is not None:
        return _PATH

    for folder in _candidates():
        try:
            os.makedirs(folder, exist_ok=True)
            candidate = os.path.join(folder, "fluxop-startup.log")
            with open(candidate, "a", encoding="utf-8"):
                pass
            _PATH = candidate
            return _PATH
        except OSError:
            continue

    _PATH = os.path.join(os.environ.get("TEMP", "."), "fluxop-startup.log")
    return _PATH


def log(message: str) -> None:
    """Append one timestamped line to the startup log. Never raises."""
    try:
        elapsed = time.monotonic() - _STARTED
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{stamp} (+{elapsed:6.2f}s) {message}\n"

        with _LOCK:
            path = log_path()
            try:
                if os.path.getsize(path) > _MAX_BYTES:
                    os.replace(path, path + ".old")
            except OSError:
                pass
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(line)
    except Exception:
        pass

    try:
        print(line, end="")
    except Exception:
        pass


def log_exception(prefix: str) -> None:
    """Log ``prefix`` plus the traceback of the exception being handled."""
    try:
        log(prefix + "\n" + traceback.format_exc().rstrip())
    except Exception:
        pass
