import psutil
from src.collectors.base import BaseCollector
from typing import Dict, Any

class CPUCollector(BaseCollector):
    def collect(self) -> Dict[str, Any]:
        cpu_percent = psutil.cpu_percent(interval=None) # Non-blocking
        cpu_freq = psutil.cpu_freq()
        
        return {
            "usage": cpu_percent,
            "frequency": cpu_freq.current if cpu_freq else 0,
            "cores": psutil.cpu_count(logical=False),
            "threads": psutil.cpu_count(logical=True),
            # load average is not available on all Windows versions natively through psutil without some quirks, but we'll try
            "load_average": psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0.0, 0.0, 0.0)
        }
