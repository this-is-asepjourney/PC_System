import psutil
from src.collectors.base import BaseCollector
from typing import Dict, Any

class HardwareCollector(BaseCollector):
    def collect(self) -> Dict[str, Any]:
        sensors = {}
        
        # CPU Temperatures (may not be available on Windows via psutil)
        if hasattr(psutil, "sensors_temperatures"):
            try:
                sensors["temperatures"] = psutil.sensors_temperatures()
            except Exception:
                sensors["temperatures"] = {}
                
        # Fans
        if hasattr(psutil, "sensors_fans"):
            try:
                sensors["fans"] = psutil.sensors_fans()
            except Exception:
                sensors["fans"] = {}
                
        # Battery
        if hasattr(psutil, "sensors_battery"):
            try:
                batt = psutil.sensors_battery()
                if batt:
                    sensors["battery"] = {
                        "percent": batt.percent,
                        "power_plugged": batt.power_plugged,
                        "secsleft": batt.secsleft
                    }
            except Exception:
                sensors["battery"] = None
                
        return sensors
