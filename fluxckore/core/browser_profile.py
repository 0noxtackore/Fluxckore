"""WebView2 profile handling.

Each run gets its own browser profile folder. Sharing a single folder between
runs proved fragile on real machines: when a previous Fluxckore was killed
(Task Manager, a crash, or the user clicking the icon again while it was still
starting) its Edge processes survive for a moment, the next launch attaches to
that dying browser, and the window stays hidden behind the splash forever
because the page never loads.

A private folder per run removes that coupling; folders from previous runs are
deleted at startup so the disk usage stays flat. Any WebView2 process still
pointing at one of our folders is terminated first: the app holds the
single-instance mutex at that point, so those processes cannot belong to a
live Fluxckore.
"""
from __future__ import annotations

import os
import shutil
import time

# Profile folders live under this directory, one sub-folder per run.
RUN_PREFIX = "run-"


def root() -> str:
    """Folder that holds every Fluxckore WebView2 profile."""
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        base = os.path.join(os.path.expanduser("~"), "AppData", "Local")
    return os.path.join(base, "Fluxckore", "browser")


def new_profile() -> str | None:
    """Create and return the private profile folder for this run."""
    path = os.path.join(root(), f"{RUN_PREFIX}{int(time.time() * 1000)}-{os.getpid()}")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        return None
    return path


def kill_stale_processes() -> int:
    """Terminate WebView2 processes that still use a Fluxckore profile."""
    try:
        import psutil
    except Exception:  # pragma: no cover - psutil is a hard dependency
        return 0

    needle = os.path.normcase(root())
    killed = 0
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            if (proc.info["name"] or "").lower() != "msedgewebview2.exe":
                continue
            command = os.path.normcase(" ".join(proc.info["cmdline"] or []))
            if needle not in command:
                continue
            proc.kill()
            killed += 1
        except (psutil.Error, OSError):
            continue
    if killed:
        # Give Windows a moment to release the files before they are deleted.
        time.sleep(0.3)
    return killed


def remove_old_profiles(current: str | None) -> int:
    """Delete profiles from previous runs (and the old flat profile)."""
    base = root()
    keep = os.path.basename(current) if current else ""
    try:
        entries = os.listdir(base)
    except OSError:
        return 0

    removed = 0
    for name in entries:
        if name == keep:
            continue
        path = os.path.join(base, name)
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            removed += 1
        except OSError:
            continue
    return removed
