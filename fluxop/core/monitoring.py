"""
Recopilación de estadísticas del sistema: archivos temporales, CPU, RAM
y datos de tendencia (sparkline) del dashboard.
"""

import os
import tempfile

import psutil


def count_temp_files(limit: int = 4000) -> tuple:
    """Count temporary files and their total size (in MB).

    ``os.walk`` + ``os.path.getsize`` per file is slow and holds the GIL for
    most of the walk, which made the interface stutter on machines with a big
    temp folder. ``os.scandir`` reuses the directory entry data (no extra stat
    per name) and the scan stops at ``limit`` entries, so a tick stays cheap.
    """
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
    total_bytes = 0

    for path in temp_paths:
        if count >= limit:
            break
        stack = [path]
        while stack and count < limit:
            current = stack.pop()
            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                stack.append(entry.path)
                            else:
                                total_bytes += entry.stat(follow_symlinks=False).st_size
                                count += 1
                        except OSError:
                            continue
                        if count >= limit:
                            break
            except OSError:
                continue

    return count, total_bytes / (1024 * 1024)


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
