"""Windows helpers: administrator privileges, settings and resource paths."""
import ctypes
import json
import os
import sys


# Resource subfolders by file extension (mirrors the original layout).
_SUBFOLDERS = {
    "mp3": ("assets", "sounds"),
    "wav": ("assets", "sounds"),
    "ogg": ("assets", "sounds"),
}


def project_root() -> str:
    """Root folder holding bundled resources (PyInstaller-aware)."""
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    # fluxckore/core/system.py -> fluxckore/ -> repository root
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resource_path(filename: str) -> str:
    """Resolve a resource path for both source runs and frozen executables."""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    subfolder = os.path.join(*_SUBFOLDERS[ext]) if ext in _SUBFOLDERS else ""
    return os.path.join(project_root(), subfolder, filename)


def config_path() -> str:
    """Path of the user settings file (language, selected categories).

    Stored under ``%LOCALAPPDATA%`` so it also works when the portable folder
    is read-only (Program Files, a share, a locked-down machine).
    """
    return os.path.join(_local_appdata(), "Fluxckore", "config.json")


def legacy_config_path() -> str:
    """Previous location (next to the app); only read, for migration."""
    return os.path.join(project_root(), "config.json")


def load_config() -> dict:
    """Read the settings file, falling back to the old location."""
    for path in (config_path(), legacy_config_path()):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                return data
        except (OSError, ValueError):
            continue
    return {}


def update_config(values: dict) -> None:
    """Merge ``values`` into the settings file. Never raises."""
    data = load_config()
    data.update(values)
    path = config_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
    except OSError:
        pass


def legacy_webview_data_path() -> str:
    """Profile folder used by v9.0.0 (kept only so it can be discarded).

    v9.0.0 could run both elevated and unprivileged against that folder;
    WebView2 does not support sharing one user data folder across integrity
    levels, which left it in a state where the window never painted.
    """
    return os.path.join(_local_appdata(), "Fluxckore", "WebView2")


def _local_appdata() -> str:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        base = os.path.join(os.path.expanduser("~"), "AppData", "Local")
    return base


def frontend_path() -> str:
    """Path of the self-contained HTML/CSS/JS interface (same relative path
    in source runs and in the frozen bundle)."""
    return os.path.join(project_root(), "fluxckore", "frontend", "index.html")


def is_admin() -> bool:
    """Check whether the process runs with administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False
