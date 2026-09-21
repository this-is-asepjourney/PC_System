from src.core.events import event_bus
from src.core.config import config
from src.database.models import Alert
from src.database.repository import Repository
from src.core.logger import logger

class AlertService:
    def __init__(self):
        self.thresholds = config.get('alerts.thresholds', {
            'cpu': 90.0,
            'memory': 90.0,
            'disk': 90.0
        })
        
        self.active_alerts = {}
        
        # Subscribe to metrics to check thresholds
        event_bus.subscribe("metrics_cpu", self._check_cpu)
        event_bus.subscribe("metrics_memory", self._check_memory)
        event_bus.subscribe("metrics_disk", self._check_disk)
        
    def _check_cpu(self, data: dict):
        usage = data.get('usage', 0)
        threshold = self.thresholds.get('cpu', 90.0)
        self._evaluate_threshold("CPU", usage, threshold, "Critical")

    def _check_memory(self, data: dict):
        usage = data.get('percent', 0)
        threshold = self.thresholds.get('memory', 90.0)
        self._evaluate_threshold("Memory", usage, threshold, "Warning")
        
    def _check_disk(self, data: dict):
        partitions = data.get('partitions', [])
        if partitions:
            usage = partitions[0].get('percent', 0)
            threshold = self.thresholds.get('disk', 90.0)
            self._evaluate_threshold("Disk", usage, threshold, "Warning")

    def _evaluate_threshold(self, resource: str, current: float, threshold: float, severity: str):
        alert_key = f"{resource}_High"
        
        if current > threshold:
            if alert_key not in self.active_alerts:
                msg = f"{resource} usage is high: {current:.1f}% (Threshold: {threshold}%)"
                alert = Alert(type=alert_key, severity=severity, message=msg, resolved=False)
                Repository.save_alert(alert)
                self.active_alerts[alert_key] = alert
                event_bus.publish("alert_triggered", alert)
                logger.warning(f"Alert Triggered: {msg}")
        else:
            if alert_key in self.active_alerts:
                # Resolve alert
                alert = self.active_alerts.pop(alert_key)
                alert.resolved = True
                alert.message = f"{resource} usage returned to normal: {current:.1f}%"
                Repository.save_alert(alert)
                event_bus.publish("alert_resolved", alert)
                logger.info(f"Alert Resolved: {alert.message}")
