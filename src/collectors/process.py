import psutil
from src.collectors.base import BaseCollector
from typing import Dict, Any, List

class ProcessCollector(BaseCollector):
    def collect(self) -> Dict[str, Any]:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            try:
                pinfo = proc.info
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'cpu': pinfo['cpu_percent'],
                    'memory': pinfo['memory_info'].rss if pinfo['memory_info'] else 0
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
        # Sort by CPU usage by default
        processes = sorted(processes, key=lambda p: p['cpu'], reverse=True)
        return {"processes": processes[:100]} # Limit to top 100 for performance
