import time
import threading
from typing import Dict, Any
from src.core.events import event_bus
from src.core.config import config
from src.core.logger import logger
from src.collectors.cpu import CPUCollector
from src.collectors.memory import MemoryCollector
from src.collectors.disk import DiskCollector
from src.collectors.network import NetworkCollector
from src.collectors.process import ProcessCollector
from src.collectors.hardware import HardwareCollector

class MonitoringService:
    def __init__(self):
        self._running = False
        self._thread: threading.Thread = None
        
        # Initialize collectors
        self.cpu_collector = CPUCollector()
        self.memory_collector = MemoryCollector()
        self.disk_collector = DiskCollector()
        self.network_collector = NetworkCollector()
        self.process_collector = ProcessCollector()
        self.hardware_collector = HardwareCollector()
        
        # Load intervals
        self.intervals = config.get('monitoring.intervals', {})
        self.interval_cpu = max(1.0, float(self.intervals.get('cpu', 1.0)))
        self.interval_memory = max(1.0, float(self.intervals.get('memory', 1.0)))
        self.interval_disk = max(1.5, float(self.intervals.get('disk', 2.0)))
        self.interval_network = max(1.0, float(self.intervals.get('network', 1.0)))
        self.interval_process = max(3.0, float(self.intervals.get('process', 5.0)))
        self.interval_hardware = max(2.5, float(self.intervals.get('hardware', 3.0)))
        self.interval_database = max(15.0, float(self.intervals.get('database', 30.0)))
        
        # Adaptive process collector flag
        self.process_page_active = False
        
        # State for computing speeds (network/disk)
        self._last_net_io = None
        self._last_net_time = None
        self._last_disk_io = None
        self._last_disk_time = None
        
        # Latest metrics cache for DB and hardware
        self._latest_metrics = {
            "cpu_usage": 0.0,
            "ram_usage": 0.0,
            "disk_usage": 0.0,
            "network_download": 0.0,
            "network_upload": 0.0
        }
        
    def set_process_monitoring_active(self, active: bool):
        self.process_page_active = active

    def start(self):
        if self._running:
            return
            
        self._running = True
        logger.info("Starting High-Efficiency Monitoring Service (Unified Engine)...")
        
        self._thread = threading.Thread(target=self._unified_worker_loop, name="Worker-Telemetry", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        logger.info("Stopping Monitoring Service...")
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

    def _unified_worker_loop(self):
        logger.debug("Unified telemetry engine started.")
        last_disk = 0.0
        last_hw = 0.0
        last_proc = 0.0
        last_db = 0.0
        last_cleanup = 0.0
        
        while self._running:
            start_loop = time.time()
            now = start_loop
            
            # 1. High-frequency fast metrics (CPU, RAM, Net) - all in-memory psutil calls (~1ms)
            try:
                self._collect_cpu()
            except Exception as e:
                logger.error(f"Error in CPU collector: {e}")
                
            try:
                self._collect_memory()
            except Exception as e:
                logger.error(f"Error in Memory collector: {e}")
                
            try:
                self._collect_network()
            except Exception as e:
                logger.error(f"Error in Network collector: {e}")

            # 2. Disk metrics (default every 2.0s)
            if now - last_disk >= self.interval_disk:
                try:
                    self._collect_disk()
                except Exception as e:
                    logger.error(f"Error in Disk collector: {e}")
                last_disk = now

            # 3. Hardware / thermals / battery (default every 3.0s)
            if now - last_hw >= self.interval_hardware:
                try:
                    self._collect_hardware()
                except Exception as e:
                    logger.error(f"Error in Hardware collector: {e}")
                last_hw = now

            # 4. Process metrics (adaptive: every 3s if active, 7s if background fast mode)
            proc_interval = 3.0 if self.process_page_active else max(7.0, self.interval_process)
            if now - last_proc >= proc_interval:
                try:
                    self._collect_process()
                except Exception as e:
                    logger.error(f"Error in Process collector: {e}")
                last_proc = now

            # 5. Database metric save (default every 30.0s)
            if now - last_db >= self.interval_database:
                try:
                    self._save_metrics()
                except Exception as e:
                    logger.error(f"Error in DB save worker: {e}")
                last_db = now

            # 6. Database retention cleanup (every 1 hour)
            if now - last_cleanup >= 3600.0:
                try:
                    from src.database.connection import db
                    retention = config.get('database.retention_days', 7)
                    db.clean_old_records(retention)
                except Exception:
                    pass
                last_cleanup = now

            # Sleep remaining time of the 1.0 second tick
            elapsed = time.time() - start_loop
            sleep_time = max(0.05, 1.0 - elapsed)
            time.sleep(sleep_time)

    def _save_metrics(self):
        from src.database.models import SystemMetric
        from src.database.repository import Repository
        
        metric = SystemMetric(
            cpu_usage=self._latest_metrics["cpu_usage"],
            ram_usage=self._latest_metrics["ram_usage"],
            disk_usage=self._latest_metrics["disk_usage"],
            network_download=self._latest_metrics["network_download"],
            network_upload=self._latest_metrics["network_upload"]
        )
        Repository.save_metric(metric)
        
    def _collect_cpu(self):
        data = self.cpu_collector.collect()
        self._latest_metrics["cpu_usage"] = data["usage"]
        event_bus.publish("metrics_cpu", data)
        
    def _collect_memory(self):
        data = self.memory_collector.collect()
        self._latest_metrics["ram_usage"] = data["percent"]
        event_bus.publish("metrics_memory", data)
        
    def _collect_disk(self):
        data = self.disk_collector.collect()
        current_time = time.time()
        
        if self._last_disk_io and self._last_disk_time:
            dt = current_time - self._last_disk_time
            if dt > 0:
                data["read_speed"] = max(0.0, (data["io_read_bytes"] - self._last_disk_io["io_read_bytes"]) / dt)
                data["write_speed"] = max(0.0, (data["io_write_bytes"] - self._last_disk_io["io_write_bytes"]) / dt)
            else:
                data["read_speed"] = 0.0
                data["write_speed"] = 0.0
        else:
            data["read_speed"] = 0.0
            data["write_speed"] = 0.0
            
        self._last_disk_io = {"io_read_bytes": data["io_read_bytes"], "io_write_bytes": data["io_write_bytes"]}
        self._last_disk_time = current_time

        if data["partitions"]:
            self._latest_metrics["disk_usage"] = data["partitions"][0]["percent"]
        event_bus.publish("metrics_disk", data)
        
    def _collect_network(self):
        data = self.network_collector.collect()
        current_time = time.time()
        
        if self._last_net_io and self._last_net_time:
            dt = current_time - self._last_net_time
            if dt > 0:
                data["download_speed"] = max(0.0, (data["bytes_recv"] - self._last_net_io["bytes_recv"]) / dt)
                data["upload_speed"] = max(0.0, (data["bytes_sent"] - self._last_net_io["bytes_sent"]) / dt)
            else:
                data["download_speed"] = 0.0
                data["upload_speed"] = 0.0
        else:
            data["download_speed"] = 0.0
            data["upload_speed"] = 0.0
            
        self._latest_metrics["network_download"] = data["download_speed"]
        self._latest_metrics["network_upload"] = data["upload_speed"]
        
        self._last_net_io = data.copy()
        self._last_net_time = current_time
        
        event_bus.publish("metrics_network", data)
        
    def _collect_process(self):
        # In fast mode when processes tab is not open, scan less to save CPU
        fast = not self.process_page_active
        data = self.process_collector.collect(limit=100 if self.process_page_active else 20, fast_mode=fast)
        event_bus.publish("metrics_process", data)
        
    def _collect_hardware(self):
        # Pass latest cached CPU and RAM metrics to avoid redundant psutil calls
        data = self.hardware_collector.collect(
            cpu_usage=self._latest_metrics["cpu_usage"],
            ram_percent=self._latest_metrics["ram_usage"]
        )
        event_bus.publish("metrics_hardware", data)

