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
                
        # Bluetooth / External Batteries
        try:
            import subprocess
            import json
            # PowerShell command to get Bluetooth battery levels
            # {104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2 is DEVPKEY_Bluetooth_BatteryLevel
            ps_script = """
            $devices = Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | Where-Object {$_.Status -eq 'OK'}
            $results = @()
            foreach ($dev in $devices) {
                $battProp = Get-PnpDeviceProperty -InstanceId $dev.InstanceId -KeyName '{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2' -ErrorAction SilentlyContinue
                if ($null -ne $battProp -and $null -ne $battProp.Data) {
                    $results += @{ Name = $dev.FriendlyName; Battery = $battProp.Data }
                }
            }
            $results | ConvertTo-Json -Compress
            """
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.stdout.strip():
                bt_data = json.loads(result.stdout.strip())
                if isinstance(bt_data, dict):
                    bt_data = [bt_data]
                sensors["bluetooth_batteries"] = bt_data
            else:
                sensors["bluetooth_batteries"] = []
        except Exception:
            sensors["bluetooth_batteries"] = []
                
        return sensors
