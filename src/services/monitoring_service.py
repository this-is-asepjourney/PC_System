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

class MonitoringService:
    def __init__(self):
        self._running = False
        self._threads: list[threading.Thread] = []
        
        # Initialize collectors
        self.cpu_collector = CPUCollector()
        self.memory_collector = MemoryCollector()
        self.disk_collector = DiskCollector()
        self.network_collector = NetworkCollector()
        from src.collectors.process import ProcessCollector
        from src.collectors.hardware import HardwareCollector
        self.process_collector = ProcessCollector()
        self.hardware_collector = HardwareCollector()
        
        # Load intervals
        self.intervals = config.get('monitoring.intervals', {})
        
        # State for computing speeds (network/disk)
        self._last_net_io = None
        self._last_net_time = None
        
        # Latest metrics cache for DB
        self._latest_metrics = {
            "cpu_usage": 0.0,
            "ram_usage": 0.0,
            "disk_usage": 0.0,
            "network_download": 0.0,
            "network_upload": 0.0
        }
        
    def start(self):
        if self._running:
            return
            
        self._running = True
        logger.info("Starting Monitoring Service...")
        
        self._start_worker("cpu", self.intervals.get('cpu', 1.0), self._collect_cpu)
        self._start_worker("memory", self.intervals.get('memory', 1.0), self._collect_memory)
        self._start_worker("disk", self.intervals.get('disk', 2.0), self._collect_disk)
        self._start_worker("network", self.intervals.get('network', 1.0), self._collect_network)
        self._start_worker("process", self.intervals.get('process', 2.0), self._collect_process)
        self._start_worker("hardware", self.intervals.get('hardware', 3.0), self._collect_hardware)
        self._start_worker("database", self.intervals.get('database', 5.0), self._save_metrics)

    def stop(self):
        self._running = False
        logger.info("Stopping Monitoring Service...")
        for t in self._threads:
            t.join(timeout=2.0)
        self._threads.clear()

    def _start_worker(self, name: str, interval: float, func):
        def worker_loop():
            logger.debug(f"Worker {name} started (interval: {interval}s)")
            while self._running:
                try:
                    func()
                except Exception as e:
                    logger.error(f"Error in {name} worker: {e}")
                time.sleep(interval)
                
        t = threading.Thread(target=worker_loop, name=f"Worker-{name}", daemon=True)
        t.start()
        self._threads.append(t)
        
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
        # For disk_usage we can use C: drive or the first partition for simplicity in the general metric
        if data["partitions"]:
            self._latest_metrics["disk_usage"] = data["partitions"][0]["percent"]
        event_bus.publish("metrics_disk", data)
        
    def _collect_network(self):
        data = self.network_collector.collect()
        
        current_time = time.time()
        
        if self._last_net_io and self._last_net_time:
            dt = current_time - self._last_net_time
            if dt > 0:
                data["download_speed"] = (data["bytes_recv"] - self._last_net_io["bytes_recv"]) / dt
                data["upload_speed"] = (data["bytes_sent"] - self._last_net_io["bytes_sent"]) / dt
            else:
                data["download_speed"] = 0
                data["upload_speed"] = 0
        else:
            data["download_speed"] = 0
            data["upload_speed"] = 0
            
        self._latest_metrics["network_download"] = data["download_speed"]
        self._latest_metrics["network_upload"] = data["upload_speed"]
        
        self._last_net_io = data.copy()
        self._last_net_time = current_time
        
        event_bus.publish("metrics_network", data)
        
    def _collect_process(self):
        data = self.process_collector.collect()
        event_bus.publish("metrics_process", data)
        
    def _collect_hardware(self):
        data = self.hardware_collector.collect()
        event_bus.publish("metrics_hardware", data)
