"""FluxOptimizer main window and orchestration."""
import json
import os
import sys
import threading
import time
import traceback
from datetime import datetime

try:
    import psutil
    import customtkinter as ctk
    from PIL import Image, ImageTk
except ImportError as exc:
    raise SystemExit(
        f"Missing dependency: {exc.name}\n"
        "Install the requirements with: pip install -r requirements.txt"
    )

from . import __version__
from .core import maintenance, monitoring
from .core.system import config_path, resource_path, run_as_admin
from .i18n import LANGUAGE_OPTIONS, TranslationManager, _
from .ui import AnimatedButton, ModernChart, SoundPlayer, TechCard


class SystemMaintenanceSuite:
    """Main application window (dashboard, logs and maintenance runner)."""

    def __init__(self, selected_language=None):
        self.total_space_freed = 0.0
        self.files_deleted = 0
        self.errors_encountered = []
        self.is_optimizing = False
        self.animation_running = True

        # Initialize translations (104 languages).
        self.i18n = TranslationManager()
        if selected_language:
            TranslationManager.set_language(selected_language)
        else:
            detected = TranslationManager.detect_system_language()
            TranslationManager.set_language(detected)
            print(f"[i18n] Detected language: {detected}")

        self.sounds = SoundPlayer(resource_path)
        self._last_ram_warning = 0

        self.colors = {
            "bg_dark": "#050508",
            "bg_card": "#0a0a12",
            "primary": "#00d4ff",
            "secondary": "#ff00ff",
            "success": "#00ff88",
            "warning": "#ffaa00",
            "danger": "#ff3333",
            "text": "#e0e0e0",
            "text_dim": "#888888",
        }

        self.root = ctk.CTk()
        self.root.title("FluxOptimizer")

        self._set_window_icon()

        self.root.geometry("1000x750")
        self.root.minsize(900, 700)
        self.root.configure(fg_color=self.colors["bg_dark"])

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self._create_ui()
        self._start_monitoring()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_resource_path(self, filename):
        """Resolve a resource path (works from source and frozen builds)."""
        return resource_path(filename)

    def _set_window_icon(self):
        """Set the window icon."""
        try:
            icon_path = self._get_resource_path("favicon_pro.ico")
            if os.path.exists(icon_path):
                try:
                    self.root.iconbitmap(icon_path)
                except Exception:
                    icon_image = Image.open(icon_path)
                    if icon_image.size != (32, 32):
                        icon_image = icon_image.resize((32, 32), Image.Resampling.LANCZOS)
                    photo_icon = ImageTk.PhotoImage(icon_image)
                    self.root.iconphoto(False, photo_icon)
                    self._icon_ref = photo_icon
        except Exception as e:
            print(f"Could not load window icon: {e}")

    def _(self, text: str) -> str:
        """Translate a text to the current language."""
        return TranslationManager.translate(text)

    def _play_sound(self, sound_type):
        """Play a notification sound."""
        self.sounds.play(sound_type)

    def _check_memory_warning(self, ram_percent):
        """Alert when memory usage is critical."""
        current_time = time.time()
        if ram_percent > 90 and (current_time - self._last_ram_warning) > 30:
            self._play_sound("danger")
            self._last_ram_warning = current_time
            self._log(_("ram_warning").format(ram_percent), "warning")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _create_ui(self):
        """Build the interface."""
        self.main_frame = ctk.CTkFrame(
            self.root,
            fg_color=self.colors["bg_dark"],
            border_width=0,
        )
        self.main_frame.grid(row=0, column=0, padx=30, pady=30, sticky="nsew")
        self.main_frame.grid_rowconfigure(2, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self._create_header()
        self._create_dashboard()
        self._create_log_area()
        self._create_action_button()
        self._create_footer()

    def _create_header(self):
        """Header with logo, title and language selector."""
        self.header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        self.header.grid_columnconfigure(0, weight=1)
        self.header.grid_columnconfigure(1, weight=0)

        container = ctk.CTkFrame(self.header, fg_color="transparent")
        container.grid(row=0, column=0)

        self._create_language_selector()

        try:
            logo_path = self._get_resource_path("logo.png")
            if not os.path.exists(logo_path):
                logo_path = self._get_resource_path("favicon_pro.ico")

            if os.path.exists(logo_path):
                logo_image = Image.open(logo_path)
                logo_image = logo_image.resize((50, 50), Image.Resampling.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(logo_image)
                ctk.CTkLabel(container, image=self.logo_photo, text="").pack(side="left", padx=(0, 15))
        except Exception:
            ctk.CTkLabel(
                container,
                text="⚡",
                font=ctk.CTkFont(size=40),
                text_color=self.colors["primary"],
            ).pack(side="left", padx=(0, 15))

        text_frame = ctk.CTkFrame(container, fg_color="transparent")
        text_frame.pack(side="left")

        self.title_label = ctk.CTkLabel(
            text_frame,
            text="FluxOptimizer",
            font=ctk.CTkFont(size=24, weight="bold", family="Consolas"),
            text_color=self.colors["primary"],
        )
        self.title_label.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            text_frame,
            text=_("windows_maintenance"),
            font=ctk.CTkFont(size=11),
            text_color=self.colors["text_dim"],
        )
        subtitle.pack(anchor="w")

        line = ctk.CTkFrame(
            self.header,
            fg_color=self.colors["primary"],
            height=2,
        )
        line.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    def _create_language_selector(self):
        """Create the language dropdown in the header."""
        lang_container = ctk.CTkFrame(
            self.header,
            fg_color="#1a1a2e",
            corner_radius=20,
            border_width=1,
            border_color="#2a2a4e",
            width=140,
            height=36,
        )
        lang_container.grid(row=0, column=1, padx=(15, 0), sticky="e")
        lang_container.grid_propagate(False)

        available_langs = TranslationManager.get_available_languages()
        self.lang_choices = {}

        for code in available_langs:
            if code in LANGUAGE_OPTIONS:
                lang_data = LANGUAGE_OPTIONS[code]
                display = f"{lang_data['flag']} {lang_data['native']}"
                self.lang_choices[display] = code

        # Common languages first.
        priority_order = ["en", "es", "fr", "de", "pt", "it", "ru", "ja", "zh", "ko", "ar"]
        sorted_options = []

        for code in priority_order:
            if code in self.lang_choices.values():
                for display, c in self.lang_choices.items():
                    if c == code:
                        sorted_options.append(display)
                        break

        for display in self.lang_choices:
            if display not in sorted_options:
                sorted_options.append(display)

        current_lang = TranslationManager.get_current_language()
        current_display = None
        for display, code in self.lang_choices.items():
            if code == current_lang:
                current_display = display
                break

        if not current_display and sorted_options:
            current_display = sorted_options[0]

        self.lang_dropdown = ctk.CTkOptionMenu(
            lang_container,
            values=sorted_options,
            command=self._on_language_change,
            width=130,
            height=28,
            font=ctk.CTkFont(size=12),
            dropdown_font=ctk.CTkFont(size=11),
            fg_color="#1a1a2e",
            button_color="#2a2a4e",
            button_hover_color="#3a3a6e",
            dropdown_fg_color="#1a1a2e",
            dropdown_hover_color="#2a2a5e",
            dropdown_text_color="#e0e0e0",
            text_color="#e0e0e0",
            corner_radius=15,
            dynamic_resizing=False,
        )
        self.lang_dropdown.place(relx=0.5, rely=0.5, anchor="center")

        if current_display:
            self.lang_dropdown.set(current_display)

    def _on_language_change(self, choice):
        """Handle language changes."""
        lang_code = self.lang_choices.get(choice)
        if lang_code:
            TranslationManager.set_language(lang_code)
            print(f"[i18n] Language changed to: {lang_code}")

            self._update_ui_texts()

            self._log(f"🌐 Language changed to {LANGUAGE_OPTIONS.get(lang_code, {}).get('native', lang_code)}", "info")

    def _update_ui_texts(self):
        """Refresh every UI text after a language change."""
        for widget in self.header.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ctk.CTkFrame):
                        for label in child.winfo_children():
                            if isinstance(label, ctk.CTkLabel) and label.cget("text") != "FluxOptimizer":
                                label.configure(text=_("windows_maintenance"))

        if hasattr(self, "cpu_chart"):
            self.cpu_chart.title_label.configure(text=_("cpu_load"))
        if hasattr(self, "ram_chart"):
            self.ram_chart.title_label.configure(text=_("memory"))

        for widget in self.main_frame.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ctk.CTkFrame):
                        for subchild in child.winfo_children():
                            if isinstance(subchild, ctk.CTkLabel):
                                text = subchild.cget("text")
                                if text == "SYSTEM LOG" or text == "system_log":
                                    subchild.configure(text=_("system_log"))

        if hasattr(self, "optimize_button"):
            self.optimize_button.configure(text=f"🚀 {_('start_optimization')}")

        if hasattr(self, "status_label"):
            self.status_label.configure(text=_("system_ready"))

    def _create_dashboard(self):
        """Create the compact monitoring dashboard."""
        dashboard = ctk.CTkFrame(
            self.main_frame,
            fg_color=self.colors["bg_card"],
            corner_radius=15,
            border_width=1,
            border_color="#1a1a2e",
        )
        dashboard.grid(row=1, column=0, sticky="ew", pady=10)
        dashboard.grid_columnconfigure((0, 1, 2), weight=1)

        self.cpu_chart = ModernChart(
            dashboard,
            _("cpu_load"),
            self.colors["primary"],
            size=110,
        )
        self.cpu_chart.grid(row=0, column=0, padx=10, pady=10)

        self.ram_chart = ModernChart(
            dashboard,
            _("memory"),
            self.colors["secondary"],
            size=110,
        )
        self.ram_chart.grid(row=0, column=1, padx=10, pady=10)

        temp_card = TechCard(
            dashboard,
            _("temp_files"),
            "📁",
            self.colors["warning"],
        )
        temp_card.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

        self.temp_count_label = ctk.CTkLabel(
            temp_card.content_frame,
            text="0",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.colors["warning"],
        )
        self.temp_count_label.pack(pady=(5, 2))

        self.temp_size_label = ctk.CTkLabel(
            temp_card.content_frame,
            text="0 MB",
            font=ctk.CTkFont(size=11),
            text_color=self.colors["text_dim"],
        )
        self.temp_size_label.pack()

        self.trend_canvas = ctk.CTkCanvas(
            temp_card.content_frame,
            width=100,
            height=25,
            bg="#0f0f1a",
            highlightthickness=0,
        )
        self.trend_canvas.pack(pady=(5, 0))

        self.trend_data = [0] * 20
        self._draw_trend_line()

    def _create_log_area(self):
        """Create the terminal-style log area."""
        log_container = ctk.CTkFrame(
            self.main_frame,
            fg_color="#0d1117",
            corner_radius=10,
            border_width=2,
            border_color="#30363d",
        )
        log_container.grid(row=2, column=0, sticky="nsew", pady=10)
        log_container.grid_rowconfigure(1, weight=1)
        log_container.grid_columnconfigure(0, weight=1)

        log_header = ctk.CTkFrame(log_container, fg_color="#161b22", height=30, corner_radius=0)
        log_header.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        log_header.grid_propagate(False)

        btn_frame = ctk.CTkFrame(log_header, fg_color="transparent", width=45, height=12)
        btn_frame.place(relx=0.015, rely=0.5, anchor="w")

        ctk.CTkFrame(btn_frame, fg_color="#ff5f56", width=8, height=8, corner_radius=4).place(x=0, y=2)
        ctk.CTkFrame(btn_frame, fg_color="#ffbd2e", width=8, height=8, corner_radius=4).place(x=14, y=2)
        ctk.CTkFrame(btn_frame, fg_color="#27c93f", width=8, height=8, corner_radius=4).place(x=28, y=2)

        ctk.CTkLabel(
            log_header,
            text=_("system_log"),
            font=ctk.CTkFont(size=9, family="Consolas"),
            text_color="#8b949e",
        ).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkButton(
            log_header,
            text=_("clear"),
            width=50,
            height=20,
            font=ctk.CTkFont(size=8),
            fg_color="#21262d",
            hover_color="#30363d",
            command=self._clear_log,
        ).place(relx=0.99, rely=0.5, anchor="e")

        self.log_text = ctk.CTkTextbox(
            log_container,
            fg_color="#0d1117",
            text_color="#e6edf3",
            font=ctk.CTkFont(family="Consolas", size=10),
            wrap="word",
            corner_radius=0,
            border_width=0,
            scrollbar_button_color="#30363d",
            scrollbar_button_hover_color="#484f58",
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.log_text.configure(state="disabled")

    def _create_action_button(self):
        """Create the optimize button."""
        button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        button_frame.grid(row=3, column=0, pady=15)

        self.optimize_button = AnimatedButton(
            button_frame,
            text=f"🚀 {_('start_optimization')}",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#0066cc",
            hover_color="#0055aa",
            width=400,
            command=self._start_optimization,
        )
        self.optimize_button.pack()

    def _create_footer(self):
        """Create the footer with status and version."""
        self.footer_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.footer_frame.grid(row=4, column=0, sticky="ew", pady=(10, 0))

        self.status_indicator = ctk.CTkFrame(
            self.footer_frame,
            fg_color=self.colors["success"],
            width=10,
            height=10,
            corner_radius=5,
        )
        self.status_indicator.pack(side="left", padx=(0, 10))

        self.status_label = ctk.CTkLabel(
            self.footer_frame,
            text=_("system_ready"),
            font=ctk.CTkFont(size=11),
            text_color=self.colors["text_dim"],
        )
        self.status_label.pack(side="left")

        version_label = ctk.CTkLabel(
            self.footer_frame,
            text=f"FluxOptimizer v{__version__}",
            font=ctk.CTkFont(size=10),
            text_color=self.colors["text_dim"],
        )
        version_label.pack(side="right")

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    def _clear_log(self):
        """Clear the log area."""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _log(self, message: str, message_type: str = "info"):
        """Append a message to the log (must run on the UI thread)."""
        colors_map = {
            "info": self.colors["primary"],
            "warning": self.colors["warning"],
            "error": self.colors["danger"],
            "success": self.colors["success"],
        }

        prefixes = {
            "info": "[INFO]",
            "warning": "[WARN]",
            "error": "[ERR]",
            "success": "[OK]",
        }

        self.log_text.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = prefixes.get(message_type, "[INFO]")

        self.log_text.insert("end", f"[{timestamp}] ", "")
        self.log_text.insert("end", f"{prefix} ", message_type)
        self.log_text.insert("end", f"{message}\n", "")

        self.log_text.configure(state="disabled")
        self.log_text.see("end")

        for tag, color in colors_map.items():
            self.log_text.tag_config(tag, foreground=color)

    def _log_async(self, message: str, message_type: str = "info"):
        """Thread-safe logging for worker threads."""
        self.root.after(0, lambda: self._log(message, message_type))

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------
    def _start_monitoring(self):
        """Start real-time monitoring."""
        self._update_stats()

    def _update_stats(self):
        """Refresh dashboard statistics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            self.cpu_chart.update_value(cpu_percent)

            ram = psutil.virtual_memory()
            self.ram_chart.update_value(ram.percent)

            temp_count, temp_size = monitoring.count_temp_files()
            self.temp_count_label.configure(text=f"{temp_count}")
            self.temp_size_label.configure(text=f"{temp_size:.1f} MB")

            self.trend_data.pop(0)
            self.trend_data.append(temp_size)
            self._draw_trend_line()

            self._check_memory_warning(ram.percent)

        except Exception:
            pass

        if self.animation_running:
            self.root.after(1000, self._update_stats)

    def _draw_trend_line(self):
        """Draw the temp-size sparkline."""
        self.trend_canvas.delete("all")

        width = 100
        height = 25
        padding = 3

        data = self.trend_data
        if all(d == 0 for d in data):
            return

        max_val = max(data) if max(data) > 0 else 1
        min_val = min(data)

        points = []
        for i, val in enumerate(data):
            x = padding + (i / (len(data) - 1)) * (width - 2 * padding)
            if max_val == min_val:
                y = height / 2
            else:
                y = height - padding - ((val - min_val) / (max_val - min_val)) * (height - 2 * padding)
            points.extend([x, y])

        if len(points) >= 4:
            self.trend_canvas.create_line(
                points,
                fill=self.colors["warning"],
                width=2,
                smooth=True,
            )

            last_x, last_y = points[-2], points[-1]
            self.trend_canvas.create_oval(
                last_x - 4, last_y - 4,
                last_x + 4, last_y + 4,
                fill=self.colors["warning"],
                outline="",
            )

    # ------------------------------------------------------------------
    # Optimization
    # ------------------------------------------------------------------
    def _start_optimization(self):
        """Start the maintenance run."""
        if self.is_optimizing:
            return

        self.is_optimizing = True
        self.optimize_button.configure(
            state="disabled",
            text=f"⏳ {_('optimization_progress')}",
            fg_color="#444444",
        )
        self.total_space_freed = 0.0
        self.files_deleted = 0
        self.errors_encountered = []

        self.status_indicator.configure(fg_color=self.colors["warning"])
        self.status_label.configure(text=_("optimization_progress"))

        self._clear_log()

        self._log("═══════════════════════════════════════", "info")
        self._log(f"     {_('starting_optimization')}      ", "success")
        self._log("═══════════════════════════════════════", "info")

        thread = threading.Thread(target=self._run_optimization)
        thread.daemon = True
        thread.start()

    def _run_optimization(self):
        """Run every maintenance module in a worker thread."""
        try:
            log = self._log_async
            stats = maintenance.MaintenanceStats()

            # Phase 1: memory.
            maintenance.optimize_ram(log)
            self.root.after(0, lambda: self._log("", "info"))

            # Phase 2: CPU.
            maintenance.optimize_cpu(log)
            self.root.after(0, lambda: self._log("", "info"))

            # Phase 3: GPU.
            maintenance.optimize_gpu(log, stats)
            self.root.after(0, lambda: self._log("", "info"))

            # Phase 4: temporary files (deep).
            maintenance.clean_temp_files(log, stats)
            self.root.after(0, lambda: self._log("", "info"))

            # Phase 5: browsers.
            maintenance.clean_browser_cache(log, stats)
            self.root.after(0, lambda: self._log("", "info"))

            # Phase 6: DNS / network.
            maintenance.flush_dns_cache(log)
            self.root.after(0, lambda: self._log("", "info"))

            # Phase 7: system caches.
            maintenance.clean_system_cache(log, stats)
            self.root.after(0, lambda: self._log("", "info"))

            # Phase 8: registry (basic).
            maintenance.clean_registry_basic(log)

            self.total_space_freed = stats.space_freed_mb
            self.files_deleted = stats.files_deleted

            self.root.after(0, self._show_summary)

        except Exception as e:
            self.root.after(0, lambda: self._log(f"Critical error: {e}", "error"))
        finally:
            self.is_optimizing = False
            self.root.after(0, lambda: self.optimize_button.configure(
                state="normal",
                text=f"🚀 {_('start_optimization')}",
                fg_color="#0066cc",
            ))
            self.root.after(0, lambda: self.status_indicator.configure(fg_color=self.colors["success"]))
            self.root.after(0, lambda: self.status_label.configure(text=_("optimization_complete")))

    def _show_summary(self):
        """Show the completion dialog."""
        self._log("═══════════════════════════════════════", "info")
        self._log(f"         {_('optimization_summary')}        ", "success")
        self._log("═══════════════════════════════════════", "info")
        self._log(f"💾 {_('space_freed')}: {self.total_space_freed:.2f} MB", "success")
        self._log(f"🗑️ {_('files_deleted')}: {self.files_deleted}", "success")

        self._play_sound("success")

        dialog = ctk.CTkToplevel(self.root)
        dialog.title("FluxOptimizer")
        dialog.geometry("400x280")
        dialog.configure(fg_color=self.colors["bg_dark"])
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 280) // 2
        dialog.geometry(f"400x280+{x}+{y}")
        dialog.resizable(False, False)

        try:
            icon_path = self._get_resource_path("favicon_pro.ico")
            if os.path.exists(icon_path):
                try:
                    dialog.iconbitmap(icon_path)
                except Exception as e1:
                    print(f"[icon] iconbitmap failed: {e1}")
                    try:
                        icon_img = Image.open(icon_path)
                        icon_photo = ImageTk.PhotoImage(icon_img)
                        dialog.iconphoto(False, icon_photo)
                        dialog._icon_ref_window = icon_photo
                    except Exception as e2:
                        print(f"[icon] iconphoto also failed: {e2}")
            else:
                print(f"[icon] favicon_pro.ico not found at: {icon_path}")
        except Exception as e:
            print(f"[icon] Error setting dialog icon: {e}")

        frame = ctk.CTkFrame(dialog, fg_color=self.colors["bg_card"], corner_radius=15)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        try:
            icon_path = self._get_resource_path("favicon_pro.ico")
            if os.path.exists(icon_path):
                icon_img = Image.open(icon_path).resize((48, 48), Image.Resampling.LANCZOS)
                icon_photo = ImageTk.PhotoImage(icon_img)
                icon_label = ctk.CTkLabel(frame, image=icon_photo, text="")
                icon_label.pack(pady=(10, 5))
                dialog._icon_ref = icon_photo
            else:
                ctk.CTkLabel(
                    frame,
                    text="✓",
                    font=ctk.CTkFont(size=48, weight="bold"),
                    text_color=self.colors["success"],
                ).pack(pady=(15, 5))
        except Exception:
            ctk.CTkLabel(
                frame,
                text="✓",
                font=ctk.CTkFont(size=48, weight="bold"),
                text_color=self.colors["success"],
            ).pack(pady=(15, 5))

        ctk.CTkLabel(
            frame,
            text=_("optimization_done"),
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors["text"],
        ).pack()

        ctk.CTkLabel(
            frame,
            text=f"{self.total_space_freed:.2f} {_('mb_freed')}\n{self.files_deleted} {_('files_deleted_count')}",
            font=ctk.CTkFont(size=12),
            text_color=self.colors["text_dim"],
        ).pack(pady=8)

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=(20, 10), fill="x")

        ctk.CTkButton(
            btn_frame,
            text=_("accept"),
            width=200,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=dialog.destroy,
            fg_color=self.colors["success"],
            hover_color="#00cc6a",
            corner_radius=12,
            text_color="#000000",
        ).pack(expand=True)

    def run(self):
        """Start the application main loop."""
        self.root.mainloop()


def main():
    """Application entry point (elevation + language selection)."""
    run_as_admin()

    i18n = TranslationManager()

    # Language preference saved by the installer (optional).
    lang = None
    path = config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
                saved_lang = config.get("language")
                if saved_lang and saved_lang in i18n.get_available_languages():
                    lang = saved_lang
                    print(f"[i18n] Using saved language: {lang}")
        except Exception:
            pass

    if lang is None:
        lang = i18n.detect_system_language()
        print(f"[i18n] Auto-detected system language: {lang}")

    app = SystemMaintenanceSuite(selected_language=lang)
    app.run()


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
