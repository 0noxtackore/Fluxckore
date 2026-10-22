"""Fluxop backend: HTML/CSS interface (pywebview) + maintenance runner.

The Python side keeps every maintenance/monitoring/i18n function; only the
presentation layer changed from CustomTkinter to a self-contained HTML/CSS/JS
interface rendered by pywebview (Edge WebView2 on Windows 10/11).
"""
import inspect
import json
import os
import sys
import threading
import time
from datetime import datetime

try:
    import webview
except ImportError as exc:
    raise SystemExit(
        f"Missing dependency: {exc.name}\n"
        "Install the requirements with: pip install -r requirements.txt"
    )

from . import __version__
from .core import maintenance, monitoring, startup_log
from .core.sounds import SoundPlayer
from .core.splash import Splash
from .core.system import (
    config_path,
    frontend_path,
    is_admin,
    project_root,
    resource_path,
    run_as_admin,
)
from .i18n import LANGUAGE_OPTIONS, TranslationManager, _

# Languages shown first in the selector.
_LANG_PRIORITY = ["en", "es", "fr", "de", "pt", "it", "ru", "ja", "zh", "ko", "ar"]


class Api:
    """API exposed to the JavaScript frontend as ``window.pywebview.api``."""

    def __init__(self):
        self.window = None
        self.is_optimizing = False
        self.total_space_freed = 0.0
        self.files_deleted = 0
        self.sounds = SoundPlayer(resource_path)

        self._trend = [0] * 20
        self._last_ram_warning = 0.0
        self._log_queue = []
        self._events = []
        self._lock = threading.Lock()

        # Startup handshake: the page calls ``frontend_ready`` after its first
        # paint, so the backend knows WebView2 really started rendering.
        self._ready = threading.Event()
        self._on_ready = None
        self._js_pending = False
        self._push_errors = 0

    # ------------------------------------------------------------------
    # Called from JavaScript
    # ------------------------------------------------------------------
    def frontend_ready(self):
        """Called by the UI after its first paint (startup diagnostics).

        Returning a value forces pywebview to run this on a worker thread, so
        revealing the window from here cannot block the webview thread.
        """
        startup_log.log("frontend: ready reported by the page")
        self._ready.set()

        callback = self._on_ready
        if callback is not None:
            try:
                callback()
            except Exception:
                startup_log.log_exception("frontend_ready: callback failed")
        return {"ok": True}

    def get_init_data(self):
        """Initial payload: version, language options and translations."""
        lang = TranslationManager.get_current_language()
        available = TranslationManager.get_available_languages()

        options = []
        for code, data in LANGUAGE_OPTIONS.items():
            if code in available:
                options.append({"code": code, "native": data["native"]})
        options.sort(
            key=lambda o: _LANG_PRIORITY.index(o["code"])
            if o["code"] in _LANG_PRIORITY
            else len(_LANG_PRIORITY)
        )

        return {
            "version": __version__,
            "lang": lang,
            "lang_options": options,
            "translations": TranslationManager.get_translations(),
            "categories": maintenance.file_categories(),
        }

    def set_language(self, code):
        """Switch UI language and return the new translations."""
        if TranslationManager.set_language(code):
            print(f"[i18n] Language changed to: {code}")
            return {"ok": True, "lang": code, "translations": TranslationManager.get_translations()}
        return {"ok": False}

    def start_optimization(self, categories=None):
        """Start a maintenance run in a worker thread.

        ``categories`` is the list of cleanup category ids chosen by the user
        in the options panel; empty/None falls back to the safe defaults.
        """
        if self.is_optimizing:
            return {"ok": False}

        known = {c["id"] for c in maintenance.file_categories()}
        if not isinstance(categories, (list, tuple)) or not categories:
            selected = maintenance.default_categories()
        else:
            selected = [c for c in categories if isinstance(c, str) and c in known]
        if not selected:
            return {"ok": False}

        self.is_optimizing = True
        threading.Thread(
            target=self._run_optimization, args=(selected,), daemon=True
        ).start()
        return {"ok": True}

    # ------------------------------------------------------------------
    # Backend -> frontend
    # ------------------------------------------------------------------
    def _log(self, message, message_type="info"):
        """Queue a log entry for the frontend."""
        entry = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": message,
            "type": message_type,
        }
        with self._lock:
            self._log_queue.append(entry)

    def _emit(self, event):
        """Queue a UI event (summary dialog, run finished...)."""
        with self._lock:
            self._events.append(event)

    def _check_memory_warning(self, ram_percent):
        """Alert when memory usage is critical (max once every 30 s)."""
        current_time = time.time()
        if ram_percent > 90 and (current_time - self._last_ram_warning) > 30:
            self._last_ram_warning = current_time
            self.sounds.play("danger")
            self._log(_("ram_warning").format(ram_percent), "warning")

    def _pusher(self):
        """Periodic loop: system stats + queued logs/events -> frontend."""
        startup_log.log("pusher: thread started")

        # Never touch the webview before its page exists: waiting here avoids
        # a burst of failed evaluate_js calls while WebView2 is starting.
        if not self._ready.wait(30):
            startup_log.log("pusher: page not ready after 30 s, pushing anyway")

        last_scan = 0.0
        temp_count = 0
        temp_size = 0.0

        while True:
            time.sleep(1)
            try:
                cpu_percent, ram = monitoring.collect_cpu_ram()
                self._check_memory_warning(ram.percent)

                # Walking the temp folders is disk-heavy: refresh every 10 s
                # instead of on every tick.
                now = time.time()
                if now - last_scan >= 10:
                    temp_count, temp_size = monitoring.count_temp_files()
                    last_scan = now
                monitoring.push_trend_point(self._trend, temp_size)

                with self._lock:
                    logs, self._log_queue = self._log_queue, []
                    events, self._events = self._events, []

                payload = {
                    "stats": {
                        "cpu": cpu_percent,
                        "ram": ram.percent,
                        "temp_count": temp_count,
                        "temp_mb": round(temp_size, 1),
                        "trend": list(self._trend),
                    },
                    "logs": logs,
                    "events": events,
                }

                self._push_js(f"window.UI && UI.onData({json.dumps(payload)})")
            except Exception:
                if self._push_errors < 3:
                    self._push_errors += 1
                    startup_log.log_exception("pusher: tick failed")

    def _push_js(self, script):
        """Send a script to the page without ever blocking the stats loop.

        ``evaluate_js`` waits for the webview to answer. If that never
        happens, calling it inline would freeze this thread forever; with the
        pending flag at most one call is in flight and the loop keeps running.
        """
        if self._js_pending:
            return
        self._js_pending = True

        def run():
            try:
                if self.window is not None:
                    self.window.evaluate_js(script)
            except Exception:
                if self._push_errors < 3:
                    self._push_errors += 1
                    startup_log.log_exception("pusher: evaluate_js failed")
            finally:
                self._js_pending = False

        threading.Thread(target=run, daemon=True).start()

    # ------------------------------------------------------------------
    # Maintenance run (same phases as the original suite)
    # ------------------------------------------------------------------
    def _run_optimization(self, selected):
        try:
            log = self._log
            stats = maintenance.MaintenanceStats()

            self._log("═══════════════════════════════════════", "info")
            self._log(f"     {_('starting_optimization')}      ", "success")
            self._log("═══════════════════════════════════════", "info")

            # Phase 1: memory.
            maintenance.optimize_ram(log)
            self._log("")

            # Phase 2: CPU.
            maintenance.optimize_cpu(log)
            self._log("")

            # Phase 3: selected file-cleanup categories (temp, browsers,
            # caches, recycle bin, registry... chosen by the user).
            maintenance.clean_selected(selected, log, stats)
            self._log("")

            # Phase 4: DNS / network.
            maintenance.flush_dns_cache(log)

            self.total_space_freed = stats.space_freed_mb
            self.files_deleted = stats.files_deleted

            self._log("═══════════════════════════════════════", "info")
            self._log(f"         {_('optimization_summary')}        ", "success")
            self._log("═══════════════════════════════════════", "info")
            self._log(f"[MB] {_('space_freed')}: {self.total_space_freed:.2f} MB", "success")
            self._log(f"[DEL] {_('files_deleted')}: {self.files_deleted}", "success")

            self.sounds.play("success")
            self._emit(
                {
                    "kind": "summary",
                    "freed": round(self.total_space_freed, 2),
                    "deleted": self.files_deleted,
                }
            )
        except Exception as e:
            self._log(f"Critical error: {e}", "error")
        finally:
            self.is_optimizing = False
            self._emit({"kind": "done"})


def _load_html() -> str:
    """Read the self-contained HTML/CSS/JS interface."""
    path = frontend_path()
    if not os.path.exists(path):
        raise FileNotFoundError(f"Interface not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _set_app_user_model_id() -> None:
    """Give the process its own AppUserModelID.

    Without an explicit AUMID, Windows groups windows under the host
    executable (``python.exe`` when running from source) and shows that
    executable's icon in the taskbar instead of the window icon. Setting a
    unique id makes the taskbar honor ``WM_SETICON``.
    """
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Fluxop.App"
        )
    except Exception:
        pass


def window_icon_path() -> str:
    """Icon shown in the window/taskbar (generated from the app logo)."""
    return os.path.join(project_root(), "fluxop", "frontend", "icon.ico")


def _webview2_available() -> bool:
    """True when the Edge WebView2 runtime is installed on this machine.

    pywebview renders the interface with WebView2. When the runtime is
    missing (stripped Windows images, some LTSC builds) WebView2 never
    initialises and the window stays blank, so we check first and explain
    the problem instead of failing silently.
    """
    if os.environ.get("FLUXOP_SKIP_WEBVIEW_CHECK") == "1":
        return True
    try:
        import winreg
    except Exception:
        return True

    guid = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
    keys = (
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\\" + guid),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\EdgeUpdate\Clients\\" + guid),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\EdgeUpdate\Clients\\" + guid),
    )
    for root, subkey in keys:
        try:
            with winreg.OpenKey(root, subkey) as handle:
                version, _ = winreg.QueryValueEx(handle, "pv")
            if version and version != "0.0.0.0":
                return True
        except OSError:
            continue

    # Fallback: the runtime may be installed without the EdgeUpdate key.
    for base in (
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("ProgramFiles"),
    ):
        if not base:
            continue
        application = os.path.join(base, "Microsoft", "EdgeWebView", "Application")
        try:
            for name in os.listdir(application):
                if os.path.exists(os.path.join(application, name, "msedgewebview2.exe")):
                    return True
        except OSError:
            continue
    return False


def _show_message(text: str, title: str = "Fluxop") -> None:
    """Show a native message box (the frozen build has no console).

    Uses its own window, so it also appears when the webview thread is stuck.
    """
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, text, title, 0x00000030)
    except Exception:
        pass


def _export_diagnostics() -> str:
    """Copy the startup log to the Desktop with a name users can find."""
    return startup_log.export_desktop_copy()



def _redirect_stderr_to_log() -> None:
    """Send stderr to a log file for the rest of the session.

    The WebView2 shutdown messages come from a CLR thread that writes straight
    to the stderr file descriptor (Python-level filters never see them).
    Rebinding fd 2 to a log file keeps the console clean and preserves the
    messages for troubleshooting.
    """
    if not getattr(sys, "stderr", None):
        return
    try:
        folder = os.path.dirname(startup_log.log_path())
        log_path = os.path.join(folder, "fluxop.log")
        fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND)
        os.dup2(fd, 2)
        os.close(fd)
    except Exception:
        pass


def main():
    """Entry point: elevation, language setup, window launch."""
    startup_log.log(f"=== Fluxop {__version__} ===")
    startup_log.log(
        f"env: frozen={bool(getattr(sys, 'frozen', False))} "
        f"exe={sys.executable} cwd={os.getcwd()}"
    )
    try:
        from importlib.metadata import version as _package_version

        try:
            webview_version = _package_version("pywebview")
        except Exception:
            webview_version = getattr(webview, "__version__", "?")
        startup_log.log(
            f"python={sys.version.split()[0]} webview={webview_version}"
        )
    except Exception:
        pass

    # Do this first: the WebView2 CLR thread that floods stderr on shutdown
    # can be alive from the very first webview call.
    _redirect_stderr_to_log()
    startup_log.log("stderr redirected")

    # Own taskbar identity so the window icon is used (not python.exe's).
    _set_app_user_model_id()

    if os.environ.get("FLUXOP_SKIP_ADMIN") != "1":
        startup_log.log("checking administrator privileges")
        run_as_admin()  # exits when it has to relaunch elevated
    startup_log.log(f"administrator={is_admin()}")

    if not _webview2_available():
        startup_log.log("WebView2 runtime NOT found: aborting with a clear message")
        _show_message(
            "Fluxop necesita el componente 'Microsoft Edge WebView2' y este "
            "equipo no lo tiene instalado.\n\n"
            "Instálalo gratis desde:\n"
            "https://developer.microsoft.com/microsoft-edge/webview2/\n\n"
            "Después vuelve a abrir Fluxop.",
            "Fluxop - falta un componente",
        )
        return
    startup_log.log("WebView2 runtime found")

    # Immediate feedback while WebView2 starts: the main window stays hidden
    # until the page is ready, so without this the user would see nothing for
    # several seconds and might think the app did not start.
    splash = Splash().start()
    startup_log.log("splash shown")

    TranslationManager()
    startup_log.log("translations loaded")

    # Language preference saved by the installer (optional).
    lang = None
    path = config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
                saved_lang = config.get("language")
                if saved_lang and saved_lang in TranslationManager.get_available_languages():
                    lang = saved_lang
                    print(f"[i18n] Using saved language: {lang}")
        except Exception:
            pass

    if lang is None:
        lang = TranslationManager.detect_system_language()
        print(f"[i18n] Auto-detected system language: {lang}")
    TranslationManager.set_language(lang)
    startup_log.log(f"language={lang}")

    api = Api()
    startup_log.log("api created")

    window = webview.create_window(
        "Fluxop",
        html=_load_html(),
        js_api=api,
        width=1000,
        height=820,
        min_size=(900, 740),
        background_color="#050508",
        # Revealed once the page paints. A cold start of an unsigned bundle
        # can take a while (antivirus scanning hundreds of DLLs) and a white,
        # unresponsive window is exactly what users reported.
        hidden=True,
    )
    api.window = window
    startup_log.log("window created (hidden until the UI is ready)")

    revealed = threading.Event()

    def _reveal(reason):
        if revealed.is_set():
            return
        revealed.set()
        startup_log.log(f"revealing window ({reason})")
        try:
            window.show()
        except Exception:
            startup_log.log_exception("window.show() failed")
        finally:
            splash.close()

    api._on_ready = lambda: _reveal("frontend ready")
    window.events.loaded += lambda *_: startup_log.log("window: loaded event")

    # Safety net: reveal the window even if the page never signals readiness
    # (the splash is replaced, so the user always ends up with the app).
    timer = threading.Timer(30.0, _reveal, args=("timeout",))
    timer.daemon = True
    timer.start()

    def _watchdog():
        if api._ready.wait(40):
            return
        startup_log.log("WATCHDOG: the page never reported ready")
        _show_message(
            "La interfaz de Fluxop está tardando demasiado.\n\n"
            "Causas habituales:\n"
            "  - El runtime 'Microsoft Edge WebView2' está dañado.\n"
            "  - Un antivirus está bloqueando la aplicación.\n\n"
            f"Se guardó un diagnóstico en:\n{_export_diagnostics()}\n\n"
            "Envíame ese archivo para poder diagnosticarlo.",
            "Fluxop - problema al iniciar",
        )

    threading.Thread(target=_watchdog, daemon=True).start()

    def _on_start():
        # pywebview runs this callback on its own thread; keep it tiny.
        startup_log.log("pywebview: start callback")
        threading.Thread(target=api._pusher, daemon=True).start()

    startup_log.log("entering pywebview.start()")
    try:
        if "icon" in inspect.signature(webview.start).parameters:
            # pywebview 6 sets the form icon natively on the UI thread; doing
            # it ourselves through pythonnet was the only cross-thread WinForms
            # manipulation we had and it is not worth the risk.
            webview.start(_on_start, icon=window_icon_path())
        else:  # pywebview < 6 has no icon parameter
            webview.start(_on_start)
    finally:
        splash.close()
        startup_log.log("pywebview.start() returned (app closed)")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        startup_log.log_exception("CRITICAL: unhandled exception")
        _show_message(
            "Fluxop no pudo iniciarse.\n\n"
            f"Detalle técnico guardado en:\n{startup_log.log_path()}",
            "Fluxop - error crítico",
        )
