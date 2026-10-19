import psutil
from src.collectors.base import BaseCollector
from typing import Dict, Any, List

class ProcessCollector(BaseCollector):
    def collect(self, limit: int = 100, fast_mode: bool = False) -> Dict[str, Any]:
        processes = []
        attrs = ['pid', 'name', 'cpu_percent', 'memory_info']
        max_scan = 50 if fast_mode else None
        count = 0
        
        try:
            for proc in psutil.process_iter(attrs):
                try:
                    pinfo = proc.info
                    cpu_val = pinfo.get('cpu_percent') or 0.0
                    mem_val = pinfo['memory_info'].rss if pinfo.get('memory_info') else 0
                    
                    processes.append({
                        'pid': pinfo.get('pid', 0),
                        'name': pinfo.get('name') or "Process",
                        'cpu': cpu_val,
                        'memory': mem_val
                    })
                    count += 1
                    if max_scan and count >= max_scan:
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            pass
                
        # Sort by CPU usage by default
        processes.sort(key=lambda p: p['cpu'], reverse=True)
        return {"processes": processes[:limit]}

