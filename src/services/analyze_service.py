import psutil
from typing import Dict, Any

class AnalyzeService:
    def __init__(self):
        pass
        
    def run_analysis(self) -> Dict[str, Any]:
        """Runs an analysis of the system to generate a health score and recommendations."""
        score = 100
        bottlenecks = []
        recommendations = []
        
        # CPU
        cpu_usage = psutil.cpu_percent(interval=1.0)
        if cpu_usage > 90:
            score -= 25
            bottlenecks.append(f"Critical CPU Usage ({cpu_usage}%)")
            recommendations.append("Kill heavy background processes using the Optimizer.")
        elif cpu_usage > 75:
            score -= 10
            bottlenecks.append(f"High CPU Usage ({cpu_usage}%)")
            
        # RAM
        mem = psutil.virtual_memory()
        if mem.percent > 90:
            score -= 25
            bottlenecks.append(f"Critical Memory Usage ({mem.percent}%)")
            recommendations.append("Free up memory using the Optimizer.")
        elif mem.percent > 75:
            score -= 10
            bottlenecks.append(f"High Memory Usage ({mem.percent}%)")
            
        # Disk
        try:
            disk = psutil.disk_usage('C:\\')
            if disk.percent > 90:
                score -= 15
                bottlenecks.append(f"Disk C: is almost full ({disk.percent}%)")
                recommendations.append("Clean Temporary Files using the Optimizer to free up space.")
        except:
            pass
            
        # Power / System state (Basic heuristic)
        if cpu_usage > 80 and mem.percent > 80:
            recommendations.append("Consider setting the Power Plan to High Performance if on a Desktop.")
            
        # Ensure score is within 0-100
        score = max(0, min(100, score))
        
        if score == 100:
            recommendations.append("System is running optimally!")
            
        return {
            "score": score,
            "bottlenecks": bottlenecks,
            "recommendations": recommendations,
            "metrics": {
                "cpu": cpu_usage,
                "ram": mem.percent
            }
        }
