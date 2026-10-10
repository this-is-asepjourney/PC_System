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
    hardware_updated = Signal(dict)

class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State
        self._cpu_temp = "--"
        self._ram_temp = "--"
        self._disk_temp = "--"
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        
        # Header Section
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        header = QLabel("System Dashboard")
        header.setStyleSheet("font-size: 26px; font-weight: 800; color: #cdd6f4;")
        subtitle = QLabel("Live performance overview and telemetry")
        subtitle.setStyleSheet("font-size: 13px; color: #a6adc8;")
        title_box.addWidget(header)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        
        header_layout.addStretch()
        
        # Mode buttons in header
        modes_bar = QHBoxLayout()
        modes_bar.setSpacing(8)
        
        self.btn_taskbar_mode = QPushButton("📌 Taskbar Mode")
        self.btn_taskbar_mode.setCursor(Qt.PointingHandCursor)
        self.btn_taskbar_mode.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #89b4fa;
                border-color: #89b4fa;
                color: #11111b;
            }
        """)
        self.btn_taskbar_mode.clicked.connect(self.open_taskbar_mode)
        modes_bar.addWidget(self.btn_taskbar_mode)
        
        self.btn_mini_mode = QPushButton("🗗 Mini Widget")
        self.btn_mini_mode.setCursor(Qt.PointingHandCursor)
        self.btn_mini_mode.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #a6e3a1;
                border-color: #a6e3a1;
                color: #11111b;
            }
        """)
        self.btn_mini_mode.clicked.connect(self.open_mini_mode)
        modes_bar.addWidget(self.btn_mini_mode)
        
        header_layout.addLayout(modes_bar)
        layout.addLayout(header_layout)
        
        # Cards grid: 4 Metric Cards with colors and temperatures
        cards_layout = QGridLayout()
        cards_layout.setSpacing(14)
        
        self.cpu_card = MetricCard("CPU Processor", accent_color="#89b4fa")
        self.ram_card = MetricCard("System Memory", accent_color="#a6e3a1")
        self.disk_card = MetricCard("Disk Storage (C:)", accent_color="#fab387")
        self.net_card = MetricCard("Internet Bandwidth", accent_color="#cba6f7")
        
        cards_layout.addWidget(self.cpu_card, 0, 0)
        cards_layout.addWidget(self.ram_card, 0, 1)
        cards_layout.addWidget(self.disk_card, 1, 0)
        cards_layout.addWidget(self.net_card, 1, 1)
        
        layout.addLayout(cards_layout)
        
        # Chart
        self.cpu_chart = PerformanceChart("CPU Activity (%)")
        layout.addWidget(self.cpu_chart, 1)
        
        # Subscribe to events via bridge
        self.bridge = DashboardBridge()
        self.bridge.cpu_updated.connect(self.update_cpu)
        self.bridge.memory_updated.connect(self.update_memory)
        self.bridge.disk_updated.connect(self.update_disk)
        self.bridge.network_updated.connect(self.update_network)
        self.bridge.hardware_updated.connect(self.update_hardware)
        
        event_bus.subscribe("metrics_cpu", self.bridge.cpu_updated.emit)
        event_bus.subscribe("metrics_memory", self.bridge.memory_updated.emit)
        event_bus.subscribe("metrics_disk", self.bridge.disk_updated.emit)
        event_bus.subscribe("metrics_network", self.bridge.network_updated.emit)
        event_bus.subscribe("metrics_hardware", self.bridge.hardware_updated.emit)

    def update_hardware(self, data: dict):
        temps = data.get("temperatures", {})
        if "cpu" in temps and temps["cpu"]:
            curr = getattr(temps["cpu"][0], "current", temps["cpu"][0].get("current") if isinstance(temps["cpu"][0], dict) else 0)
            self._cpu_temp = f"{curr:.1f}°C"
            self.cpu_card.set_temp(self._cpu_temp)
            
        if "ram" in temps and temps["ram"]:
            curr = getattr(temps["ram"][0], "current", temps["ram"][0].get("current") if isinstance(temps["ram"][0], dict) else 0)
            self._ram_temp = f"{curr:.1f}°C"
            self.ram_card.set_temp(self._ram_temp)
            
        if "disk" in temps and temps["disk"]:
            curr = getattr(temps["disk"][0], "current", temps["disk"][0].get("current") if isinstance(temps["disk"][0], dict) else 0)
            self._disk_temp = f"{curr:.1f}°C"
            self.disk_card.set_temp(self._disk_temp)

    def update_cpu(self, data: dict):
        usage = data['usage']
        freq = data.get('frequency', 0)
        sub = f"{freq:.0f} MHz" if freq > 0 else "Active"
        self.cpu_card.set_value(f"{usage:.1f}%", subvalue=sub, percent=usage, temp=self._cpu_temp)
        self.cpu_chart.update_value(usage)
        
    def update_memory(self, data: dict):
        pct = data['percent']
        total_gb = data['total'] / (1024**3)
        used_gb = data['used'] / (1024**3)
        self.ram_card.set_value(f"{pct:.1f}%", subvalue=f"{used_gb:.1f} / {total_gb:.1f} GB", percent=pct, temp=self._ram_temp)
        
    def update_disk(self, data: dict):
        if data.get('partitions'):
            p = data['partitions'][0]
            pct = p['percent']
            total_gb = p['total'] / (1024**3)
            used_gb = p['used'] / (1024**3)
            
            read_speed = data.get('read_speed', 0.0) / (1024**2)
            write_speed = data.get('write_speed', 0.0) / (1024**2)
            io_info = f" | R: {read_speed:.1f} W: {write_speed:.1f} MB/s" if (read_speed > 0 or write_speed > 0) else ""
            
            self.disk_card.set_value(f"{pct:.1f}%", subvalue=f"{used_gb:.1f} / {total_gb:.1f} GB{io_info}", percent=pct, temp=self._disk_temp)
            
    def update_network(self, data: dict):
        dl_bps = data.get('download_speed', 0.0)
        ul_bps = data.get('upload_speed', 0.0)
        
        dl_str = self._format_speed(dl_bps)
        ul_str = self._format_speed(ul_bps)
        
        # Estimate network activity percentage for bar (up to 100 MB/s full scale)
        max_scale = 50 * 1024 * 1024 # 50 MB/s
        activity_pct = min(100.0, ((dl_bps + ul_bps) / max_scale) * 100.0)
        
        self.net_card.set_value(f"↓ {dl_str}", subvalue=f"↑ {ul_str} upload", percent=activity_pct)

    def _format_speed(self, bytes_per_sec: float) -> str:
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.0f} B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        elif bytes_per_sec < 1024 * 1024 * 1024:
            return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024 * 1024):.2f} GB/s"

    def open_taskbar_mode(self):
        window = self.window()
        window.hide()
        if hasattr(window, 'mini_widget'):
            window.mini_widget.hide()
        if hasattr(window, 'taskbar_widget'):
            window.taskbar_widget.show()
            window.taskbar_widget.activateWindow()

    def open_mini_mode(self):
        window = self.window()
        window.hide()
        if hasattr(window, 'taskbar_widget'):
            window.taskbar_widget.hide()
        if hasattr(window, 'mini_widget'):
            window.mini_widget.show()
            window.mini_widget.activateWindow()
