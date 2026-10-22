"""Reproducción de sonidos de la aplicación (pygame.mixer, si está disponible)."""

import os
import threading

from ..core.system import resource_path


class SoundPlayer:
    """Reproductor de sonidos de la aplicación (pygame.mixer, si está disponible).

    ``pygame.mixer.init()`` puede tardar (o quedarse esperando) en equipos sin
    tarjeta de sonido, máquinas virtuales o sesiones RDP. Por eso la
    inicialización ocurre en un hilo aparte: la ventana nunca debe esperar al
    audio para abrirse.
    """

    def __init__(self, resource_path_fn=resource_path):
        self.notification_sound = None
        self.danger_sound = None
        self.available = False
        self._resource_path = resource_path_fn
        self._init_lock = threading.Lock()

        threading.Thread(target=self._init_audio, daemon=True).start()

    def _init_audio(self):
        try:
            import pygame

            pygame.mixer.init()

            # Usar rutas correctas para recursos
            notification_path = self._resource_path("notification.mp3")
            danger_path = self._resource_path("danger.mp3")

            with self._init_lock:
                if os.path.exists(notification_path):
                    self.notification_sound = notification_path
                if os.path.exists(danger_path):
                    self.danger_sound = danger_path
                self.available = True
        except Exception as e:
            print(f"Error inicializando sonidos: {e}")

    def play(self, sound_type):
        """Reproduce un sonido."""
        if not self.available:
            return
        with self._init_lock:
            try:
                import pygame
                if sound_type == "success" and self.notification_sound:
                    pygame.mixer.music.load(self.notification_sound)
                    pygame.mixer.music.play()
                elif sound_type == "danger" and self.danger_sound:
                    pygame.mixer.music.load(self.danger_sound)
                    pygame.mixer.music.play()
            except Exception:
                pass
