"""Botón animado (AnimatedButton) de FluxOptimizer."""

import customtkinter as ctk


class AnimatedButton(ctk.CTkButton):
    """Botón con efectos de animación."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            height=55,
            corner_radius=12,
            border_width=0,
            **kwargs
        )
        
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
    
    def on_enter(self, event):
        """Efecto al pasar el mouse."""
        self.configure(
            border_width=2,
            border_color="#00d4ff"
        )
    
    def on_leave(self, event):
        """Efecto al quitar el mouse."""
        self.configure(border_width=0)

