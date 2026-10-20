"""Tarjeta tecnológica (TechCard) de FluxOptimizer."""

import customtkinter as ctk


class TechCard(ctk.CTkFrame):
    """Tarjeta tecnológica con efectos de borde."""
    
    def __init__(self, parent, title, icon, color, **kwargs):
        super().__init__(
            parent,
            fg_color="#0f0f1a",
            border_color=color,
            border_width=2,
            corner_radius=15,
            **kwargs
        )
        
        self.color = color
        
        # Header con icono y título
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=15, pady=(15, 10))
        
        self.icon_label = ctk.CTkLabel(
            self.header,
            text=icon,
            font=ctk.CTkFont(size=20)
        )
        self.icon_label.pack(side="left")
        
        self.title_label = ctk.CTkLabel(
            self.header,
            text=title,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=color
        )
        self.title_label.pack(side="left", padx=10)
        
        # Línea decorativa
        self.line = ctk.CTkFrame(self, fg_color=color, height=2)
        self.line.pack(fill="x", padx=15, pady=(0, 15))
        
        # Contenido
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

