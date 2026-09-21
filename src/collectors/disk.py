import psutil
from src.collectors.base import BaseCollector
from typing import Dict, Any

class DiskCollector(BaseCollector):
    def collect(self) -> Dict[str, Any]:
        partitions = psutil.disk_partitions(all=False)
        disks_data = []
        
        # To calculate read/write speeds, we would need to store previous state.
        # For simplicity in collect(), we just return current counters.
        # The service layer or UI can compute the delta if needed.
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
