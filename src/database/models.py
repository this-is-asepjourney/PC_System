from dataclasses import dataclass
from typing import Optional

@dataclass
class SystemMetric:
    id: Optional[int] = None
    timestamp: Optional[str] = None
    cpu_usage: float = 0.0
    ram_usage: float = 0.0
    disk_usage: float = 0.0
    network_download: float = 0.0
    network_upload: float = 0.0

@dataclass
class Alert:
    type: str
    severity: str
    message: str
    id: Optional[int] = None
    timestamp: Optional[str] = None
    resolved: bool = False

@dataclass
class SystemLog:
    level: str
    source: str
    message: str
    id: Optional[int] = None
    timestamp: Optional[str] = None
