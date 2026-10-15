import time
import psutil
from src.collectors.base import BaseCollector
from typing import Dict, Any

class DiskCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self._cached_partitions = []
        self._last_partitions_time = 0.0

    def collect(self) -> Dict[str, Any]:
        now = time.time()
        if not self._cached_partitions or (now - self._last_partitions_time > 60.0):
            try:
                self._cached_partitions = psutil.disk_partitions(all=False)
            except Exception:
                self._cached_partitions = []
            self._last_partitions_time = now

        partitions = self._cached_partitions
        disks_data = []
        io_counters = psutil.disk_io_counters()
        
        for p in partitions:
            try:
                usage = psutil.disk_usage(p.mountpoint)
                disks_data.append({
                    "device": p.device,
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent
                })
            except PermissionError:
                # Some partitions (like system recovery) might not be accessible
                continue
                
        return {
            "partitions": disks_data,
            "io_read_bytes": io_counters.read_bytes if io_counters else 0,
            "io_write_bytes": io_counters.write_bytes if io_counters else 0
        }
