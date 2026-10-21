"""Reproducción de sonidos de la aplicación (pygame.mixer, si está disponible)."""

import os

from ..core.system import resource_path


class SoundPlayer:
    """Reproductor de sonidos de la aplicación (pygame.mixer, si está disponible)."""

    def __init__(self, resource_path_fn=resource_path):
        self.notification_sound = None
        self.danger_sound = None
        self.available = False
        try:
            import pygame
            pygame.mixer.init()

            # Usar rutas correctas para recursos
            notification_path = resource_path_fn("notification.mp3")
            danger_path = resource_path_fn("danger.mp3")

            if os.path.exists(notification_path):
                self.notification_sound = notification_path
            if os.path.exists(danger_path):
                self.danger_sound = danger_path
            self.available = True
        except Exception as e:
            print(f"Error inicializando sonidos: {e}")
            pass

    def play(self, sound_type):
        """Reproduce un sonido."""
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

