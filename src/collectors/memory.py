import psutil
from src.collectors.base import BaseCollector
from typing import Dict, Any

class MemoryCollector(BaseCollector):
    def collect(self) -> Dict[str, Any]:
        mem = psutil.virtual_memory()
        
        return {
            "total": mem.total,
            "used": mem.used,
            "available": mem.available,
            "percent": mem.percent,
            "cached": getattr(mem, 'cached', 0) # 'cached' is not always available on Windows
        }
