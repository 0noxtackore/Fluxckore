"""FluxOptimizer backend: HTML/CSS interface (pywebview) + maintenance runner.

The Python side keeps every maintenance/monitoring/i18n function; only the
presentation layer changed from CustomTkinter to a self-contained HTML/CSS/JS
interface rendered by pywebview (Edge WebView2 on Windows 10/11).
"""
import json
import os
import sys
import threading
import time
import traceback
from datetime import datetime

try:
    import webview
except ImportError as exc:
    raise SystemExit(
        f"Missing dependency: {exc.name}\n"
        "Install the requirements with: pip install -r requirements.txt"
    )

from . import __version__
from .core import maintenance, monitoring
from .core.sounds import SoundPlayer
from .core.system import config_path, frontend_path, resource_path, run_as_admin
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

    # ------------------------------------------------------------------
    # Called from JavaScript
    # ------------------------------------------------------------------
    def get_init_data(self):
        """Initial payload: version, language options and translations."""
        lang = TranslationManager.get_current_language()
        available = TranslationManager.get_available_languages()

        options = []
        for code, data in LANGUAGE_OPTIONS.items():
            if code in available:
                options.append(
                    {"code": code, "flag": data["flag"], "native": data["native"]}
                )
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
        }

    def set_language(self, code):
        """Switch UI language and return the new translations."""
        if TranslationManager.set_language(code):
            print(f"[i18n] Language changed to: {code}")
            return {"ok": True, "lang": code, "translations": TranslationManager.get_translations()}
        return {"ok": False}

    def start_optimization(self):
        """Start a maintenance run in a worker thread."""
        if self.is_optimizing:
            return {"ok": False}
        self.is_optimizing = True
        threading.Thread(target=self._run_optimization, daemon=True).start()
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
        while True:
            time.sleep(1)
            try:
                cpu_percent, ram = monitoring.collect_cpu_ram(0.5)
                self._check_memory_warning(ram.percent)

                temp_count, temp_size = monitoring.count_temp_files()
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

                if self.window is not None:
                    self.window.evaluate_js(
                        f"window.UI && UI.onData({json.dumps(payload)})"
                    )
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Maintenance run (same phases as the original suite)
    # ------------------------------------------------------------------
    def _run_optimization(self):
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

            # Phase 3: GPU.
            maintenance.optimize_gpu(log, stats)
            self._log("")

            # Phase 4: temporary files (deep).
            maintenance.clean_temp_files(log, stats)
            self._log("")

            # Phase 5: browsers.
            maintenance.clean_browser_cache(log, stats)
            self._log("")

            # Phase 6: DNS / network.
            maintenance.flush_dns_cache(log)
            self._log("")

            # Phase 7: system caches.
            maintenance.clean_system_cache(log, stats)
            self._log("")

            # Phase 8: registry (basic).
            maintenance.clean_registry_basic(log)

            self.total_space_freed = stats.space_freed_mb
            self.files_deleted = stats.files_deleted

            self._log("═══════════════════════════════════════", "info")
            self._log(f"         {_('optimization_summary')}        ", "success")
            self._log("═══════════════════════════════════════", "info")
            self._log(f"\U0001f4be {_('space_freed')}: {self.total_space_freed:.2f} MB", "success")
            self._log(f"\U0001f5d1\ufe0f {_('files_deleted')}: {self.files_deleted}", "success")

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


def main():
    """Entry point: elevation, language setup, window launch."""
    if os.environ.get("FLUXOPTIMIZER_SKIP_ADMIN") != "1":
        run_as_admin()

    TranslationManager()

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

    api = Api()
    window = webview.create_window(
        "FluxOptimizer",
        html=_load_html(),
        js_api=api,
        width=1000,
        height=750,
        min_size=(900, 700),
        background_color="#050508",
    )
    api.window = window

    def _on_start():
        threading.Thread(target=api._pusher, daemon=True).start()

    webview.start(_on_start)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("\n" + "=" * 50)
        print("CRITICAL ERROR - The application has crashed:")
        print("=" * 50)
        traceback.print_exc()
        print("\n" + "=" * 50)
        input("\nPress ENTER to close...")
