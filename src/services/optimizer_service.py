import psutil
import os
import ctypes
import time
from src.core.logger import logger

class OptimizerService:
    def __init__(self):
        self.whitelist = [
            'svchost.exe', 'explorer.exe', 'csrss.exe', 'smss.exe', 
            'system idle process', 'system', 'wininit.exe', 'services.exe', 
            'lsass.exe', 'taskmgr.exe', 'python.exe', 'pycharm.exe', 'code.exe'
        ]
        
    def free_memory(self) -> dict:
        """Attempt to free memory by clearing the working set of all accessible processes on Windows."""
        freed = 0
        processes_optimized = 0
        
        try:
            # We can use ctypes on Windows to empty the working set
            if os.name == 'nt':
                psapi = ctypes.WinDLL('psapi.dll')
                
                # Get memory before
                mem_before = psutil.virtual_memory().used
                
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        # Skip our own process or critical ones
                        if proc.info['name'] and proc.info['name'].lower() in self.whitelist:
                            continue
                            
                        handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, proc.info['pid'])
                        if handle:
                            if psapi.EmptyWorkingSet(handle):
                                processes_optimized += 1
                            ctypes.windll.kernel32.CloseHandle(handle)
                    except Exception:
                        pass
                        
                # Small delay to let the OS reclaim
                time.sleep(0.5)
                mem_after = psutil.virtual_memory().used
                
                if mem_before > mem_after:
                    freed = mem_before - mem_after
                else:
                    freed = 0 # No actual gain or system compensated
            else:
                logger.info("Free memory is only fully supported on Windows.")
                
            return {
                "success": True, 
                "freed_bytes": freed, 
                "processes": processes_optimized,
                "message": f"Successfully optimized {processes_optimized} processes."
            }
        except Exception as e:
            logger.error(f"Error freeing memory: {e}")
            return {"success": False, "message": str(e), "freed_bytes": 0, "processes": 0}

    def kill_heavy_processes(self, cpu_threshold: float = 20.0, mem_threshold_mb: float = 500.0) -> dict:
        """Kills processes exceeding the given thresholds (excluding whitelist)."""
        killed = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                try:
                    pinfo = proc.info
                    name = pinfo['name']
                    if not name or name.lower() in self.whitelist:
                        continue
                        
                    mem_mb = pinfo['memory_info'].rss / (1024**2) if pinfo['memory_info'] else 0
                    cpu = pinfo['cpu_percent']
                    
                    if cpu > cpu_threshold or mem_mb > mem_threshold_mb:
                        # Attempt to terminate
                        proc.terminate()
                        killed.append({
                            "name": name,
                            "pid": pinfo['pid'],
                            "cpu": cpu,
                            "mem_mb": mem_mb
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            return {
                "success": True,
                "killed_processes": killed,
                "count": len(killed),
                "message": f"Killed {len(killed)} heavy processes."
            }
        except Exception as e:
            logger.error(f"Error killing heavy processes: {e}")
            return {"success": False, "message": str(e), "count": 0, "killed_processes": []}
            
    def cleanup_temp_files(self) -> dict:
        """Cleans up the Windows temporary files directory."""
        if os.name != 'nt':
            return {"success": False, "message": "Only supported on Windows.", "freed_bytes": 0}
            
        temp_dir = os.environ.get('TEMP')
        if not temp_dir or not os.path.exists(temp_dir):
            return {"success": False, "message": "TEMP directory not found.", "freed_bytes": 0}
            
        freed = 0
        deleted_count = 0
        for root, dirs, files in os.walk(temp_dir, topdown=False):
            for name in files:
                filepath = os.path.join(root, name)
                try:
                    size = os.path.getsize(filepath)
                    os.remove(filepath)
                    freed += size
                    deleted_count += 1
                except Exception:
                    pass
            for name in dirs:
                dirpath = os.path.join(root, name)
                try:
                    os.rmdir(dirpath)
                except Exception:
                    pass
                    
        return {
            "success": True,
            "message": f"Deleted {deleted_count} temp files.",
            "freed_bytes": freed
        }
        
    def set_power_plan(self, high_performance: bool) -> dict:
        """Sets the Windows power plan."""
        if os.name != 'nt':
            return {"success": False, "message": "Only supported on Windows."}
            
        import subprocess
        # High performance: 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
        # Balanced: 381b4222-f694-41f0-9685-ff5bb260df2e
        guid = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c" if high_performance else "381b4222-f694-41f0-9685-ff5bb260df2e"
        
        try:
            subprocess.run(['powercfg', '/setactive', guid], check=True, capture_output=True)
            plan = "High Performance" if high_performance else "Balanced"
            return {"success": True, "message": f"Power plan set to {plan}."}
        except Exception as e:
            logger.error(f"Failed to set power plan: {e}")
            return {"success": False, "message": str(e)}
