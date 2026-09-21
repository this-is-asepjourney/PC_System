from typing import List
from src.database.connection import db
from src.database.models import SystemMetric, Alert, SystemLog
from src.core.logger import logger

class Repository:
    @staticmethod
    def save_metric(metric: SystemMetric):
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO metrics (cpu_usage, ram_usage, disk_usage, network_download, network_upload)
                    VALUES (?, ?, ?, ?, ?)
                ''', (metric.cpu_usage, metric.ram_usage, metric.disk_usage, metric.network_download, metric.network_upload))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save metric: {e}")

    @staticmethod
    def save_alert(alert: Alert):
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO alerts (type, severity, message, resolved)
                    VALUES (?, ?, ?, ?)
                ''', (alert.type, alert.severity, alert.message, 1 if alert.resolved else 0))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save alert: {e}")
            
    @staticmethod
    def get_recent_metrics(limit: int = 60) -> List[SystemMetric]:
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM metrics ORDER BY timestamp DESC LIMIT ?
                ''', (limit,))
                rows = cursor.fetchall()
                
                metrics = []
                for row in reversed(rows): # return chronological order
                    metrics.append(SystemMetric(
                        id=row['id'],
                        timestamp=row['timestamp'],
                        cpu_usage=row['cpu_usage'],
                        ram_usage=row['ram_usage'],
                        disk_usage=row['disk_usage'],
                        network_download=row['network_download'],
                        network_upload=row['network_upload']
                    ))
                return metrics
        except Exception as e:
            logger.error(f"Failed to fetch metrics: {e}")
            return []
