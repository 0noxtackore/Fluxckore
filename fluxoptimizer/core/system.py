"""Windows helpers: administrator privileges and bundled-resource paths."""
import ctypes
import os
import sys


# Resource subfolders by file extension (mirrors the original layout).
_SUBFOLDERS = {
    "ico": ("assets", "images"),
    "png": ("assets", "images"),
    "jpg": ("assets", "images"),
    "jpeg": ("assets", "images"),
    "gif": ("assets", "images"),
    "mp3": ("assets", "sounds"),
    "wav": ("assets", "sounds"),
    "ogg": ("assets", "sounds"),
}


def project_root() -> str:
    """Root folder holding bundled resources (PyInstaller-aware)."""
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    # fluxoptimizer/core/system.py -> fluxoptimizer/ -> repository root
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resource_path(filename: str) -> str:
    """Resolve a resource path for both source runs and frozen executables."""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    subfolder = os.path.join(*_SUBFOLDERS[ext]) if ext in _SUBFOLDERS else ""
    return os.path.join(project_root(), subfolder, filename)


def config_path() -> str:
    """Path of the optional config.json (language preference)."""
    return os.path.join(project_root(), "config.json")


def is_admin() -> bool:
    """Check whether the process runs with administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_as_admin() -> None:
    """Relaunch the application elevated (UAC) if not already admin."""
    if not is_admin():
        try:
            script = sys.argv[0]
            params = " ".join(sys.argv[1:])
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                sys.executable,
                f'"{script}" {params}',
                None,
                1,
            )
            sys.exit(0)
        except Exception as e:
            print(f"Error requesting privilege elevation: {e}")
            sys.exit(1)
