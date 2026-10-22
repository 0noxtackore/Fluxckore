"""
Recopilación de estadísticas del sistema: archivos temporales, CPU, RAM
y datos de tendencia (sparkline) del dashboard.
"""

import os
import tempfile

import psutil


def count_temp_files() -> tuple:
    """Cuenta archivos temporales."""
    temp_paths = [
        tempfile.gettempdir(),
        os.path.expandvars(r"C:\Windows\Temp"),
        os.path.expandvars(r"C:\Windows\Prefetch"),
    ]
    
    chrome_cache = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache")
    edge_cache = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache")
    
    if os.path.exists(chrome_cache):
        temp_paths.append(chrome_cache)
    if os.path.exists(edge_cache):
        temp_paths.append(edge_cache)
    
    count = 0
    size_mb = 0
    
    for path in temp_paths:
        if os.path.exists(path):
            try:
                for root, dirs, files in os.walk(path):
                    for file in files:
                        try:
                            filepath = os.path.join(root, file)
                            count += 1
                            size_mb += os.path.getsize(filepath) / (1024 * 1024)
                        except (OSError, PermissionError):
                            pass
                    if count > 10000:
                        break
            except PermissionError:
                pass
    
    return count, size_mb


def collect_cpu_ram(interval=None):
    """Recopila el uso actual de CPU y RAM (misma secuencia del monitoreo original).

    ``interval=None`` devuelve el uso desde la llamada anterior sin bloquear
    el hilo: esperar 0.5 s en cada tick retrasaba el refresco de la interfaz
    sin aportar precisión útil.
    """
    cpu_percent = psutil.cpu_percent(interval=interval)
    ram = psutil.virtual_memory()
    return cpu_percent, ram


def push_trend_point(trend_data, value):
    """Agrega un punto a la ventana deslizante de datos de tendencia."""
    trend_data.pop(0)
    trend_data.append(value)
    return trend_data
