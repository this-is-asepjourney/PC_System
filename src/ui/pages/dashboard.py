from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal, QObject
from src.ui.components.metric_card import MetricCard
from src.ui.components.performance_chart import PerformanceChart
from src.core.events import event_bus

class DashboardBridge(QObject):
    cpu_updated = Signal(dict)
    memory_updated = Signal(dict)
    disk_updated = Signal(dict)
    network_updated = Signal(dict)

class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        header = QLabel("Dashboard")
        header.setStyleSheet("font-size: 28px; font-weight: bold; color: #cdd6f4;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_taskbar_mode = QPushButton("Taskbar Mode")
        self.btn_taskbar_mode.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #45475a;
            }
        """)
        self.btn_taskbar_mode.clicked.connect(self.open_taskbar_mode)
        header_layout.addWidget(self.btn_taskbar_mode)
        
        layout.addLayout(header_layout)
        
        # Cards grid
        cards_layout = QGridLayout()
        cards_layout.setSpacing(15)
        
        self.cpu_card = MetricCard("CPU")
        self.ram_card = MetricCard("Memory")
        self.disk_card = MetricCard("Disk (C:)")
        self.net_card = MetricCard("Network")
        
        cards_layout.addWidget(self.cpu_card, 0, 0)
        cards_layout.addWidget(self.ram_card, 0, 1)
        cards_layout.addWidget(self.disk_card, 1, 0)
        cards_layout.addWidget(self.net_card, 1, 1)
        
        layout.addLayout(cards_layout)
        
        # Chart
        self.cpu_chart = PerformanceChart("CPU Usage (%)")
        layout.addWidget(self.cpu_chart)
        
        layout.addStretch()
        
        # Subscribe to events via bridge
        self.bridge = DashboardBridge()
        self.bridge.cpu_updated.connect(self.update_cpu)
        self.bridge.memory_updated.connect(self.update_memory)
        self.bridge.disk_updated.connect(self.update_disk)
        self.bridge.network_updated.connect(self.update_network)
        
        event_bus.subscribe("metrics_cpu", self.bridge.cpu_updated.emit)
        event_bus.subscribe("metrics_memory", self.bridge.memory_updated.emit)
        event_bus.subscribe("metrics_disk", self.bridge.disk_updated.emit)
        event_bus.subscribe("metrics_network", self.bridge.network_updated.emit)

    def update_cpu(self, data: dict):
        self.cpu_card.set_value(f"{data['usage']:.1f}%", f"{data['frequency']:.0f} MHz")
        self.cpu_chart.update_value(data['usage'])
        
    def update_memory(self, data: dict):
        total_gb = data['total'] / (1024**3)
        used_gb = data['used'] / (1024**3)
        self.ram_card.set_value(f"{data['percent']:.1f}%", f"{used_gb:.1f} / {total_gb:.1f} GB")
        
    def update_disk(self, data: dict):
        if data['partitions']:
            p = data['partitions'][0]
            total_gb = p['total'] / (1024**3)
            used_gb = p['used'] / (1024**3)
            self.disk_card.set_value(f"{p['percent']:.1f}%", f"{used_gb:.1f} / {total_gb:.1f} GB")
            
    def update_network(self, data: dict):
        dl_mb = data['download_speed'] / (1024**2)
        ul_mb = data['upload_speed'] / (1024**2)
        self.net_card.set_value(f"↓ {dl_mb:.1f} MB/s", f"↑ {ul_mb:.1f} MB/s")

    def open_taskbar_mode(self):
        window = self.window()
        if hasattr(window, 'tray'):
            window.tray.show_taskbar()
