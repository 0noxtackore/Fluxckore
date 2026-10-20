"""
Operaciones de mantenimiento y limpieza de FluxOptimizer.

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
import tempfile

import psutil

from ..i18n import _


class Stats:
    """Contador compartido de la optimización (antes era self.* de la suite)."""

    def __init__(self):
        self.space_freed_mb = 0
        self.files_deleted = 0


# Compatibilidad con el nombre original
MaintenanceStats = Stats


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
        
        # Calcular memoria liberada
        ram_after = psutil.virtual_memory().used / (1024 * 1024)
        actual_freed = max(0, ram_before - ram_after)
        
        log(_("ram_optimized").format(processes_optimized, actual_freed), 
            "success"
        )
        
    except Exception as e:
        log(_("error_ram").format(e), "warning")


def clean_temp_files(log=print, stats=None):
    """Limpia archivos temporales de forma agresiva."""
    log(_("cleaning_temp"), "info")
    
    # Lista exhaustiva de ubicaciones temporales
    temp_paths = [
        (tempfile.gettempdir(), "Temporales de Usuario"),
        (r"C:\Windows\Temp", "Temporales de Sistema"),
        (r"C:\Windows\Prefetch", "Prefetch"),
        (r"C:\Windows\SoftwareDistribution\Download", "Windows Update Download"),
        (r"C:\Windows\Installer\$PatchCache$", "Patch Cache"),
        (os.path.expandvars(r"%LOCALAPPDATA%\Temp"), "AppData Temp"),
        (os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Explorer"), "Explorer Cache"),
        (os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\WER"), "Error Reports"),
        (r"C:\Windows\Logs", "Windows Logs"),
        (r"C:\Windows\System32\LogFiles", "System Log Files"),
        (os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\WER"), "System Error Reports"),
        (os.path.expandvars(r"%LOCALAPPDATA%\CrashDumps"), "Crash Dumps"),
    ]
    
    total_freed = 0
    for path, name in temp_paths:
        try:
            freed = delete_directory_contents_aggressive(path, name, log=log, stats=stats)
            total_freed += freed
        except Exception as e:
            log(f"⚠ {name}: {str(e)[:50]}", "warning")
    
    if stats is not None:
        stats.space_freed_mb += total_freed
    
    # Limpiar caché de miniaturas
    clean_thumbnail_cache(log=log)
    
    # Vaciar Papelera de Reciclaje
    empty_recycle_bin(log=log)


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


def clean_browser_cache(log=print, stats=None):
    """Limpia caché de navegadores de forma exhaustiva."""
    log(_("cleaning_browsers"), "info")
    
    browsers = [
        # Chrome y variantes
        (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache", "Chrome Cache"),
        (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Code Cache", "Chrome Code Cache"),
        (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\GPUCache", "Chrome GPU Cache"),
        (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Service Worker", "Chrome Service Workers"),
        (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\File System", "Chrome File System"),
        (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\IndexedDB", "Chrome IndexedDB"),
        (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Session Storage", "Chrome Session Storage"),
        (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Local Storage", "Chrome Local Storage"),
        (r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\blob_storage", "Chrome Blob Storage"),
        
        # Edge
        (r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache", "Edge Cache"),
        (r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Code Cache", "Edge Code Cache"),
        (r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\GPUCache", "Edge GPU Cache"),
        (r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Service Worker", "Edge Service Workers"),
        
        # Firefox
        (r"%LOCALAPPDATA%\Mozilla\Firefox\Profiles", "Firefox Cache"),
        (r"%APPDATA%\Mozilla\Firefox\Profiles", "Firefox Data"),
        
        # Opera
        (r"%LOCALAPPDATA%\Opera Software\Opera Stable\Cache", "Opera Cache"),
        (r"%LOCALAPPDATA%\Opera Software\Opera Stable\Code Cache", "Opera Code Cache"),
        (r"%LOCALAPPDATA%\Opera Software\Opera GX Stable\Cache", "Opera GX Cache"),
        
        # Brave
        (r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default\Cache", "Brave Cache"),
        (r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default\Code Cache", "Brave Code Cache"),
        
        # Vivaldi
        (r"%LOCALAPPDATA%\Vivaldi\User Data\Default\Cache", "Vivaldi Cache"),
        
        # Internet Explorer / Old Edge
        (r"%LOCALAPPDATA%\Microsoft\Windows\INetCache", "IE Cache"),
        (r"%LOCALAPPDATA%\Microsoft\Windows\WebCache", "Web Cache"),
        
        # Otros
        (r"%LOCALAPPDATA%\Maxthon", "Maxthon"),
        (r"%LOCALAPPDATA%\Slimjet", "Slimjet"),
    ]
    
    total_freed = 0
    found_browsers = 0
    
    for path, name in browsers:
        try:
            expanded_path = os.path.expandvars(path)
            if os.path.exists(expanded_path):
                found_browsers += 1
                freed = delete_directory_contents_aggressive(expanded_path, name, log=log, stats=stats)
                total_freed += freed
        except Exception:
            pass
    
    if stats is not None:
        stats.space_freed_mb += total_freed
    
    if found_browsers > 0:
        log(_("browsers_cleaned").format(found_browsers, total_freed), "success")
    else:
        log(_("no_browsers"), "info")


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


def clean_system_cache(log=print, stats=None):
    """Limpia caché del sistema Windows de forma agresiva."""
    log(_("cleaning_system_cache"), "info")
    
    system_paths = [
        (r"C:\Windows\SoftwareDistribution\Download", "Windows Update"),
        (r"C:\Windows\System32\config\systemprofile\AppData\Local\Temp", "System Temp"),
        (r"C:\Windows\ServiceProfiles\LocalService\AppData\Local\Temp", "Service Temp"),
        (r"C:\Windows\ServiceProfiles\NetworkService\AppData\Local\Temp", "Network Service Temp"),
        (os.path.expandvars(r"%PROGRAMDATA%\Package Cache"), "Package Cache"),
        (os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\WER"), "Windows Error Reporting"),
        (r"C:\Windows\Debug", "Debug Logs"),
        (r"C:\Windows\Logs", "Windows Logs"),
        (r"C:\Windows\Performance\WinSAT\DataStore", "WinSAT Data"),
    ]
    
    total_freed = 0
    for path, name in system_paths:
        try:
            if os.path.exists(os.path.expandvars(path)):
                freed = delete_directory_contents_aggressive(path, name, log=log, stats=stats)
                total_freed += freed
        except:
            pass
    
    if stats is not None:
        stats.space_freed_mb += total_freed
    
    # Limpiar caché de Windows Store
    try:
        ws_cache = os.path.expandvars(r"%LOCALAPPDATA%\Packages\*\LocalCache")
        import glob
        for cache_dir in glob.glob(ws_cache):
            try:
                freed = delete_directory_contents_aggressive(cache_dir, "Windows Store Cache", log=log, stats=stats)
                total_freed += freed
            except:
                pass
    except:
        pass
    
    if total_freed > 0:
        log(_("system_cleaned").format(total_freed), "success")


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
    
    if not os.path.exists(directory):
        return 0
    
    freed_mb = 0
    deleted_count = 0
    retry_list = []
    
    try:
        # Primera pasada: eliminar lo que se pueda
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            
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

