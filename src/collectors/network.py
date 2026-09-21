import psutil
from src.collectors.base import BaseCollector
from typing import Dict, Any

class NetworkCollector(BaseCollector):
    def collect(self) -> Dict[str, Any]:
        net_io = psutil.net_io_counters()
        
        # Similar to disk, returning raw counters.
        # The service layer will compute speeds.
        return {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "errin": net_io.errin,
            "errout": net_io.errout,
            "dropin": net_io.dropin,
            "dropout": net_io.dropout
        }
