"""Gráfico circular moderno (ModernChart) de FluxOptimizer."""

import math

import customtkinter as ctk


class ModernChart(ctk.CTkFrame):
    """Gráfico circular moderno con indicador de progreso."""
    
    def __init__(self, parent, title, color, size=150, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        self.size = size
        self.color = color
        self.percentage = 0
        self.title = title
        
        # Canvas para el gráfico circular
        self.canvas = ctk.CTkCanvas(
            self, 
            width=size, 
            height=size, 
            bg="#0a0a0a",
            highlightthickness=0
        )
        self.canvas.pack(pady=10)
        
        # Label del título
        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#888888"
        )
        self.title_label.pack()
        
        # Label del porcentaje
        self.percent_label = ctk.CTkLabel(
            self,
            text="0%",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=color
        )
        self.percent_label.pack()
        
        # Dibujar gráfico inicial
        self.draw_chart(0)
    
    def draw_chart(self, percentage):
        """Dibuja el gráfico circular con el porcentaje dado."""
        self.canvas.delete("all")
        
        # Centro y radio
        center = self.size // 2
        radius = (self.size // 2) - 15
        
        # Color de fondo del círculo (track)
        self.canvas.create_oval(
            center - radius, center - radius,
            center + radius, center + radius,
            outline="#1a1a2e", width=12
        )
        
        # Calcular ángulo
        angle = (percentage / 100) * 360
        
        # Dibujar arco de progreso
        if percentage > 0:
            start_angle = 90
            
            self.canvas.create_arc(
                center - radius, center - radius,
                center + radius, center + radius,
                start=start_angle, extent=-angle,
                outline=self.color, width=12,
                style="arc"
            )
        
        # Brillo/glow effect en el punto final
        if percentage > 0:
            rad_angle = math.radians(90 - angle)
            glow_x = center + radius * math.cos(rad_angle)
            glow_y = center - radius * math.sin(rad_angle)
            
            # Círculo de brillo pequeño
            glow_radius = 6
            self.canvas.create_oval(
                glow_x - glow_radius, glow_y - glow_radius,
                glow_x + glow_radius, glow_y + glow_radius,
                fill=self.color, outline=""
            )
        
        self.percentage = percentage
        self.percent_label.configure(text=f"{percentage:.1f}%")
    
    def update_value(self, percentage):
        """Actualiza el valor del gráfico con animación."""
        self.draw_chart(percentage)

