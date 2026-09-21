import psutil

class VerifyService:
    def __init__(self):
        self.pre_metrics = None
        
    def take_snapshot(self):
        """Takes a snapshot of current system metrics."""
        return {
            "cpu": psutil.cpu_percent(interval=0.5),
            "ram": psutil.virtual_memory().used
        }
        
    def start_verification(self):
        self.pre_metrics = self.take_snapshot()
        
    def complete_verification(self) -> dict:
        """Compares current metrics to the pre-optimization snapshot."""
        if not self.pre_metrics:
            return {"success": False, "message": "Verification not started."}
            
        post_metrics = self.take_snapshot()
        
        cpu_diff = self.pre_metrics["cpu"] - post_metrics["cpu"]
        ram_diff = self.pre_metrics["ram"] - post_metrics["ram"]
        
        results = []
        if cpu_diff > 0:
            results.append(f"CPU usage decreased by {cpu_diff:.1f}%")
        elif cpu_diff < 0:
            results.append(f"CPU usage increased by {abs(cpu_diff):.1f}%")
        else:
            results.append("CPU usage unchanged.")
            
        if ram_diff > 0:
            results.append(f"RAM usage decreased by {ram_diff / (1024**2):.1f} MB")
        elif ram_diff < 0:
            results.append(f"RAM usage increased by {abs(ram_diff) / (1024**2):.1f} MB")
        else:
            results.append("RAM usage unchanged.")
            
        return {
            "success": True,
            "results": results
        }
