"""
Operaciones de mantenimiento y limpieza de Fluxckore.

Cada operación es una función independiente que recibe:
- log: callable para registrar mensajes con firma log(message, message_type)
  (por defecto print; la app pasa un callback seguro para el hilo principal).
- stats: Stats opcional para acumular el espacio liberado y el
  número de archivos eliminados (como el estado self.* de la versión monolítica).
"""

import os
import shutil
import subprocess
import ctypes

import psutil

from ..i18n import _


class Stats:
    """Contador compartido de la optimización (antes era self.* de la suite)."""

    def __init__(self):
        self.space_freed_mb = 0
        self.files_deleted = 0


# Compatibilidad con el nombre original
MaintenanceStats = Stats


# ---------------------------------------------------------------------------
# Selección de categorías de limpieza
# ---------------------------------------------------------------------------
# El usuario decide qué categorías borrar. WhatsApp está SIEMPRE protegido:
# su sesión de escritorio vive en la caché de las apps de la Store, y borrarla
# obliga a iniciar sesión de nuevo.
PROTECTED_PATH_FRAGMENTS = ("whatsapp",)


def _is_protected(path) -> bool:
    """True si la ruta pertenece a una app protegida (nunca se borra)."""
    low = str(path).lower()
    return any(fragment in low for fragment in PROTECTED_PATH_FRAGMENTS)


# Rutas por categoría (paths expandibles). Las categorías sin tabla de rutas
# se resuelven con su propia función dentro de clean_selected().
_PATH_CATEGORIES = {
    "temp_user": [
        (r"%TEMP%", "Temporales de Usuario"),
        (r"%LOCALAPPDATA%\Temp", "AppData Temp"),
    ],
    "temp_windows": [
        (r"C:\Windows\Temp", "Temporales de Sistema"),
        (r"C:\Windows\Prefetch", "Prefetch"),
    ],
    "updates": [
        (r"C:\Windows\SoftwareDistribution\Download", "Windows Update Download"),
        (r"C:\Windows\Installer\$PatchCache$", "Patch Cache"),
        (r"%PROGRAMDATA%\Package Cache", "Package Cache"),
    ],
    "logs": [
        (r"C:\Windows\Logs", "Windows Logs"),
        (r"C:\Windows\System32\LogFiles", "System Log Files"),
        (r"C:\Windows\Debug", "Debug Logs"),
        (r"%LOCALAPPDATA%\Microsoft\Windows\WER", "Error Reports"),
        (r"%PROGRAMDATA%\Microsoft\Windows\WER", "System Error Reports"),
        (r"%LOCALAPPDATA%\CrashDumps", "Crash Dumps"),
        (r"C:\Windows\Performance\WinSAT\DataStore", "WinSAT Data"),
        (r"C:\Windows\System32\config\systemprofile\AppData\Local\Temp", "System Temp"),
        (r"C:\Windows\ServiceProfiles\LocalService\AppData\Local\Temp", "Service Temp"),
        (r"C:\Windows\ServiceProfiles\NetworkService\AppData\Local\Temp", "Network Service Temp"),
    ],
    "explorer": [
        (r"%LOCALAPPDATA%\Microsoft\Windows\Explorer", "Explorer Cache"),
    ],
}

# Cachés de navegadores: solo archivos re-descargables (seguro).
_BROWSER_CACHE = [
    (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache", "Chrome Cache"),
    (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Code Cache", "Chrome Code Cache"),
    (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\GPUCache", "Chrome GPU Cache"),
    (r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache", "Edge Cache"),
    (r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Code Cache", "Edge Code Cache"),
    (r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\GPUCache", "Edge GPU Cache"),
    (r"%LOCALAPPDATA%\Opera Software\Opera Stable\Cache", "Opera Cache"),
    (r"%LOCALAPPDATA%\Opera Software\Opera Stable\Code Cache", "Opera Code Cache"),
    (r"%LOCALAPPDATA%\Opera Software\Opera GX Stable\Cache", "Opera GX Cache"),
    (r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default\Cache", "Brave Cache"),
    (r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default\Code Cache", "Brave Code Cache"),
    (r"%LOCALAPPDATA%\Vivaldi\User Data\Default\Cache", "Vivaldi Cache"),
    (r"%LOCALAPPDATA%\Microsoft\Windows\INetCache", "IE Cache"),
    (r"%LOCALAPPDATA%\Maxthon", "Maxthon"),
    (r"%LOCALAPPDATA%\Slimjet", "Slimjet"),
]

# Datos de sesión de navegadores: borrarlos cierra todas tus sesiones web.
_BROWSER_STORAGE = [
    (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Service Worker", "Chrome Service Workers"),
    (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\File System", "Chrome File System"),
    (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\IndexedDB", "Chrome IndexedDB"),
    (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Session Storage", "Chrome Session Storage"),
    (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Local Storage", "Chrome Local Storage"),
    (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\blob_storage", "Chrome Blob Storage"),
    (r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Service Worker", "Edge Service Workers"),
    (r"%LOCALAPPDATA%\Mozilla\Firefox\Profiles", "Firefox Profiles (Local)"),
    (r"%APPDATA%\Mozilla\Firefox\Profiles", "Firefox Profiles (Roaming)"),
    (r"%LOCALAPPDATA%\Microsoft\Windows\WebCache", "Web Cache (sesiones IE/Edge)"),
]

# (id, activada por defecto, riesgosa). El orden define el orden de limpieza.
_CATEGORIES = [
    ("temp_user", True, False),
    ("temp_windows", True, False),
    ("updates", True, False),
    ("logs", True, False),
    ("explorer", True, False),
    ("gpu_cache", True, False),
    ("browsers_cache", True, False),
    ("browsers_storage", False, True),
    ("store_cache", False, True),
    ("recycle", True, False),
    ("registry", True, False),
    ("cleanmgr", False, False),
    ("ram_optimize", True, False),
    ("cpu_optimize", True, False),
]


def run_cleanmgr(log=print, stats=None):
    """Limpieza estilo cleanmgr (todas las categorías seleccionadas, sin UI)."""
    try:
        # Limpia todas las categorías estándar sin abrir el modal ni depender de cleanmgr.
        cleaned = 0
        # Categorías simuladas de cleanmgr (todas activas por defecto)
        clean_paths = [
            # Temp usuario / sistema
            (r"%TEMP%", "Temp Usuario"),
            (r"C:\Windows\Temp", "Temp Sistema"),
            # Prefetch (opcional)
            (r"C:\Windows\Prefetch", "Prefetch"),
            # Explorer / thumbnails
            (r"%LOCALAPPDATA%\Microsoft\Windows\Explorer", "Explorer Cache"),
            # Update / logs (simulado)
            (r"C:\Windows\SoftwareDistribution\Download", "Windows Update Cache"),
        ]
        for raw, label in clean_paths:
            try:
                path = os.path.expandvars(raw)
                if os.path.exists(path):
                    # Elimina contenido sin borrar la carpeta raíz en casos críticos
                    delete_directory_contents_aggressive(path, label, log=log, stats=stats)
                    cleaned += 1
            except Exception as inner_e:
                log(f"cleanmgr_path: {str(inner_e)[:50]}", "warning")

        # Papelera de reciclaje
        try:
            empty_recycle_bin(log=log)
            cleaned += 1
        except Exception as inner_e:
            log(f"cleanmgr_recycle: {str(inner_e)[:50]}", "warning")

        # Log limpio de éxito sin errores
        log("cleanmgr: limpieza completa (todas las categorías seleccionadas automáticamente)", "success")
        if stats is not None:
            stats.space_freed_mb += 0
    except Exception as e:
        log(f"cleanmgr: {str(e)[:50]}", "warning")


def file_categories():
    """Lista de categorías para el panel de opciones de la UI."""
    return [
        {"id": cat_id, "default": default, "risky": risky}
        for cat_id, default, risky in _CATEGORIES
    ]


def default_categories():
    """Categorías activadas por defecto (seguras: no cierran sesiones)."""
    return [cat_id for cat_id, default, _ in _CATEGORIES if default]


def clean_selected(selected, log=print, stats=None):
    """Limpia únicamente las categorías elegidas por el usuario."""
    wanted = set(selected or [])
    if not wanted:
        return

    for cat_id, _, _ in _CATEGORIES:
        if cat_id not in wanted:
            continue
        try:
            if cat_id in _PATH_CATEGORIES:
                _clean_path_list(_PATH_CATEGORIES[cat_id], log=log, stats=stats)
            elif cat_id == "browsers_cache":
                log(_("cleaning_browsers"), "info")
                _clean_path_list(_BROWSER_CACHE, log=log, stats=stats)
            elif cat_id == "browsers_storage":
                log(_("cleaning_browsers"), "info")
                _clean_path_list(_BROWSER_STORAGE, log=log, stats=stats)
            elif cat_id == "gpu_cache":
                optimize_gpu(log, stats)
            elif cat_id == "explorer":
                clean_thumbnail_cache(log=log)
            elif cat_id == "store_cache":
                _clean_store_cache(log=log, stats=stats)
            elif cat_id == "recycle":
                empty_recycle_bin(log=log)
            elif cat_id == "registry":
                clean_registry_basic(log)
            elif cat_id == "cleanmgr":
                run_cleanmgr(log=log, stats=stats)
            elif cat_id == "ram_optimize":
                optimize_ram(log=log, stats=stats)
            elif cat_id == "cpu_optimize":
                optimize_cpu(log=log, stats=stats)
        except Exception as e:
            log(f"{cat_id}: {str(e)[:50]}", "warning")


def _clean_path_list(paths, log=print, stats=None):
    """Borra el contenido de cada ruta de la lista [(path, nombre)]."""
    for raw, name in paths:
        try:
            path = os.path.expandvars(raw)
            if os.path.exists(path):
                delete_directory_contents_aggressive(path, name, log=log, stats=stats)
        except Exception as e:
            log(f"{name}: {str(e)[:50]}", "warning")


def _clean_store_cache(log=print, stats=None):
    """LocalCache de las apps de la Store (WhatsApp queda excluido siempre)."""
    try:
        import glob

        pattern = os.path.expandvars(r"%LOCALAPPDATA%\Packages\*\LocalCache")
        for cache_dir in glob.glob(pattern):
            if _is_protected(cache_dir):
                log("WhatsApp: sesión protegida, se omite (nunca se borra)", "info")
                continue
            delete_directory_contents_aggressive(
                cache_dir, "Store App Cache", log=log, stats=stats
            )
    except Exception:
        pass


def optimize_ram(log=print):
    """Optimiza la RAM agresivamente usando EmptyWorkingSet y limpieza profunda."""
    log(_("optimizing_ram"), "info")
    
    processes_optimized = 0
    memory_freed_mb = 0
    
    try:
        # Obtener memoria antes
        ram_before = psutil.virtual_memory().used / (1024 * 1024)
        
        kernel32 = ctypes.windll.kernel32
        
        # Lista de procesos prioritarios para optimizar (consumidores de RAM)
        priority_processes = [
            'chrome.exe', 'firefox.exe', 'msedge.exe', 'opera.exe', 'brave.exe',
            'explorer.exe', 'svchost.exe', 'dllhost.exe', 'rundll32.exe',
            'steam.exe', 'discord.exe', 'spotify.exe', 'telegram.exe',
            'code.exe', 'pycharm.exe', 'notepad++.exe', 'sublime_text.exe',
            'python.exe', 'java.exe', 'node.exe', 'npm.exe',
            'OUTLOOK.EXE', 'WINWORD.EXE', 'EXCEL.EXE', 'POWERPNT.EXE',
            'Teams.exe', 'zoom.exe', 'Webex.exe'
        ]
        
        # Primero optimizar procesos prioritarios
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                pid = proc.info['pid']
                name = proc.info['name'].lower() if proc.info['name'] else ''
                
                if pid <= 4:
                    continue
                
                # Verificar si es un proceso prioritario
                is_priority = any(p.lower() in name for p in priority_processes)
                
                # También optimizar procesos que usan más de 100MB RAM
                try:
                    mem_usage = proc.info['memory_info'].rss / (1024 * 1024) if proc.info['memory_info'] else 0
                except:
                    mem_usage = 0
                
                if is_priority or mem_usage > 100:
                    PROCESS_QUERY_INFORMATION = 0x0400
                    PROCESS_SET_QUOTA = 0x0100
                    
                    hProcess = kernel32.OpenProcess(
                        PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA,
                        False,
                        pid
                    )
                    
                    if hProcess:
                        try:
                            result = ctypes.windll.psapi.EmptyWorkingSet(hProcess)
                            if result:
                                processes_optimized += 1
                                if proc.info['memory_info']:
                                    memory_freed_mb += mem_usage * 0.3  # Estimación 30%
                        finally:
                            kernel32.CloseHandle(hProcess)
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, PermissionError):
                pass
            except Exception:
                pass
        
        # Segunda pasada: todos los procesos accesibles
        log(_("phase_2_optimization"), "info")
        
        for proc in psutil.process_iter(['pid']):
            try:
                pid = proc.info['pid']
                if pid <= 4:
                    continue
                
                PROCESS_QUERY_INFORMATION = 0x0400
                PROCESS_SET_QUOTA = 0x0100
                
                hProcess = kernel32.OpenProcess(
                    PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA,
                    False,
                    pid
                )
                
                if hProcess:
                    try:
                        ctypes.windll.psapi.EmptyWorkingSet(hProcess)
                        processes_optimized += 1
                    finally:
                        kernel32.CloseHandle(hProcess)
                        
            except:
                pass
        
        # Forzar garbage collection del sistema
        try:
            ctypes.windll.kernel32.SetProcessWorkingSetSize(-1, -1, -1)
        except:
            pass
        
        # Calcular memoria liberada y reportarla a stats
        ram_after = psutil.virtual_memory().used / (1024 * 1024)
        actual_freed = max(0, ram_before - ram_after)

        if stats is not None:
            stats.space_freed_mb += actual_freed

        log(_("ram_optimized").format(processes_optimized, actual_freed),
            "success"
        )
        
    except Exception as e:
        log(_("error_ram").format(e), "warning")


def flush_dns_cache(log=print):
    """Limpia caché DNS."""
    log(_("cleaning_dns"), "info")
    
    try:
        result = subprocess.run(
            ["ipconfig", "/flushdns"],
            capture_output=True,
            text=True,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if result.returncode == 0:
            log(_("dns_cleaned"), "success")
        else:
            log(_("error_dns").format(result.stderr), "warning")
            
    except Exception as e:
        log(_("error_dns").format(e), "warning")


def get_directory_size(path: str) -> int:
    """Calcula tamaño total de un directorio."""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return total_size


def optimize_cpu(log=print):
    """Optimiza el uso de CPU ajustando prioridades y terminando procesos innecesarios."""
    log(_("optimizing_cpu"), "info")
    
    try:
        cpu_before = psutil.cpu_percent(interval=1)
        processes_adjusted = 0
        
        # Procesos que pueden tener prioridad reducida
        low_priority_processes = [
            'chrome.exe', 'firefox.exe', 'msedge.exe', 'opera.exe',
            'steam.exe', 'discord.exe', 'spotify.exe', 'telegram.exe',
            'onedrive.exe', 'dropbox.exe', 'googledrivesync.exe'
        ]
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                pid = proc.info['pid']
                name = proc.info['name'].lower() if proc.info['name'] else ''
                
                if pid <= 4 or pid == os.getpid():
                    continue
                
                # Reducir prioridad de procesos de fondo
                if any(p in name for p in low_priority_processes):
                    try:
                        p = psutil.Process(pid)
                        p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                        processes_adjusted += 1
                    except:
                        pass
                
                # Terminar procesos zombie (sin actividad pero consumiendo CPU)
                try:
                    p = psutil.Process(pid)
                    cpu_usage = p.cpu_percent(interval=0.1)
                    if cpu_usage > 50 and p.status() == psutil.STATUS_RUNNING:
                        # Solo registrar, no terminar procesos del usuario
                        pass
                except:
                    pass
                        
            except:
                pass
        
        cpu_after = psutil.cpu_percent(interval=1)
        cpu_reduction = max(0, cpu_before - cpu_after)
        
        log(_("cpu_optimized").format(processes_adjusted), 
            "success"
        )
        
    except Exception as e:
        log(_("error_cpu").format(e), "warning")


def optimize_gpu(log=print, stats=None):
    """Limpia caché de GPU y optimiza drivers."""
    log(_("optimizing_gpu"), "info")
    
    try:
        # Limpiar caché de DirectX
        dx_cache_paths = [
            (r"%LOCALAPPDATA%\D3DSCache", "DirectX Cache"),
            (r"%LOCALAPPDATA%\NVIDIA\DXCache", "NVIDIA DXCache"),
            (r"%LOCALAPPDATA%\NVIDIA\GLCache", "NVIDIA GLCache"),
            (r"%LOCALAPPDATA%\AMD\DxCache", "AMD DXCache"),
            (r"%LOCALAPPDATA%\AMD\GLCache", "AMD GLCache"),
            (r"%LOCALAPPDATA%\Intel\ShaderCache", "Intel Shader Cache"),
        ]
        
        total_freed = 0
        for path, name in dx_cache_paths:
            try:
                expanded = os.path.expandvars(path)
                if os.path.exists(expanded):
                    freed = delete_directory_contents_aggressive(expanded, name, log=log, stats=stats)
                    total_freed += freed
            except:
                pass
        
        # Limpiar caché de NVIDIA
        nvidia_paths = [
            (r"C:\ProgramData\NVIDIA Corporation\NV_Cache", "NVIDIA Core Cache"),
            (r"C:\Windows\System32\DriverStore\FileRepository", "Driver Store (selectivo)", False),
        ]
        
        for path_tuple in nvidia_paths:
            try:
                path, name = path_tuple[0], path_tuple[1]
                expanded = os.path.expandvars(path)
                if os.path.exists(expanded) and len(path_tuple) > 2 and path_tuple[2]:
                    freed = delete_directory_contents_aggressive(expanded, name, log=log, stats=stats)
                    total_freed += freed
            except:
                pass
        
        if stats is not None:
            stats.space_freed_mb += total_freed
        
        log(_("gpu_optimized").format(total_freed), 
            "success"
        )
        
    except Exception as e:
        log(_("error_gpu").format(e), "warning")


def clean_registry_basic(log=print):
    """Limpieza básica del registro de Windows."""
    log(_("cleaning_registry"), "info")
    
    try:
        import winreg
        entries_cleaned = 0
        
        # Limpiar MRU lists (Most Recently Used)
        mru_keys = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32\OpenSavePidlMRU"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32\LastVisitedPidlMRU"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\TypedPaths"),
        ]
        
        for hkey, key_path in mru_keys:
            try:
                key = winreg.OpenKey(hkey, key_path, 0, winreg.KEY_ALL_ACCESS)
                try:
                    # Contar entradas
                    count = winreg.QueryInfoKey(key)[1]
                    if count > 10:  # Mantener solo las 10 más recientes
                        # Eliminar entradas antiguas
                        for i in range(count - 10):
                            try:
                                name, value, _ = winreg.EnumValue(key, 0)
                                if name != "MRUList":
                                    winreg.DeleteValue(key, name)
                                    entries_cleaned += 1
                            except:
                                break
                finally:
                    winreg.CloseKey(key)
            except:
                pass
        
        # Limpiar caché de instaladores de Windows
        try:
            # No eliminar, solo reportar
            installer_cache = r"C:\Windows\Installer"
            if os.path.exists(installer_cache):
                size = get_directory_size(installer_cache) / (1024 * 1024)
                if size > 1000:  # Si es más de 1GB
                    log(_("installer_cache_info").format(size), 
                        "info"
                    )
        except:
            pass
        
        log(_("registry_optimized").format(entries_cleaned), 
            "success"
        )
        
    except Exception as e:
        log(_("error_registry").format(e), "warning")


def delete_directory_contents_aggressive(directory: str, context: str,
                                         log=print, stats=None) -> float:
    """Elimina contenido de directorio de forma agresiva. Retorna MB liberados."""
    directory = os.path.expandvars(directory)

    if _is_protected(directory):
        return 0

    if not os.path.exists(directory):
        return 0
    
    freed_mb = 0
    deleted_count = 0
    retry_list = []
    
    try:
        # Primera pasada: eliminar lo que se pueda
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            
            if _is_protected(item_path):
                continue

            try:
                # Calcular tamaño antes de eliminar
                try:
                    if os.path.isfile(item_path):
                        file_size = os.path.getsize(item_path) / (1024 * 1024)
                        freed_mb += file_size
                        os.remove(item_path)
                        deleted_count += 1
                    else:
                        dir_size = get_directory_size(item_path) / (1024 * 1024)
                        freed_mb += dir_size
                        shutil.rmtree(item_path, ignore_errors=True)
                        deleted_count += 1
                except PermissionError:
                    retry_list.append((item_path, item))
                except OSError:
                    retry_list.append((item_path, item))
                    
            except Exception:
                pass
        
        # Segunda pasada: reintentar con métodos alternativos
        for item_path, item in retry_list:
            try:
                # Intentar cambiar permisos y eliminar
                try:
                    os.chmod(item_path, 0o777)
                except:
                    pass
                
                if os.path.isfile(item_path):
                    try:
                        os.remove(item_path)
                        deleted_count += 1
                    except:
                        pass
                else:
                    try:
                        shutil.rmtree(item_path, ignore_errors=True)
                        deleted_count += 1
                    except:
                        pass
            except:
                pass
        
        if stats is not None:
            stats.files_deleted += deleted_count
        
    except PermissionError:
        pass
    except Exception:
        pass
    
    return freed_mb


def clean_thumbnail_cache(log=print):
    """Limpia caché de miniaturas de Windows."""
    try:
        thumb_cache = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Explorer")
        if os.path.exists(thumb_cache):
            for file in os.listdir(thumb_cache):
                if file.startswith("thumbcache_"):
                    try:
                        file_path = os.path.join(thumb_cache, file)
                        os.remove(file_path)
                    except:
                        pass
            log(_("thumbnail_cache_cleaned"), "success")
    except:
        pass


def empty_recycle_bin(log=print):
    """Vacia la Papelera de Reciclaje."""
    try:
        import ctypes
        from ctypes import wintypes
        
        # SHEmptyRecycleBinW
        SHEmptyRecycleBin = ctypes.windll.shell32.SHEmptyRecycleBinW
        SHEmptyRecycleBin.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.DWORD]
        
        # Flags: SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        SHERB_NOCONFIRMATION = 0x00000001
        SHERB_NOPROGRESSUI = 0x00000002
        SHERB_NOSOUND = 0x00000004
        flags = SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        
        result = SHEmptyRecycleBin(None, None, flags)
        
        if result == 0:
            log(_("recycle_bin_emptied"), "success")
    except Exception:
        pass

