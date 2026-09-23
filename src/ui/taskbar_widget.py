from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QPoint
from src.core.events import event_bus
from src.ui.mini_widget import MiniBridge

class TaskbarWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        
        # Frameless, stay on top, tool window (no taskbar icon for this one since it acts as a taskbar widget itself)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        
        self.bg_frame = QWidget()
        self.bg_frame.setStyleSheet("""
            QWidget {
                background-color: rgba(20, 20, 30, 240);
                border-radius: 4px;
                border: 1px solid #313244;
                color: #cdd6f4;
                font-family: 'Segoe UI', Arial;
            }
        """)
        layout.addWidget(self.bg_frame)
        
        inner_layout = QHBoxLayout(self.bg_frame)
        inner_layout.setContentsMargins(10, 2, 10, 2)
        inner_layout.setSpacing(15)
        
        # Labels
        self.lbl_cpu = QLabel("CPU: --")
        self.lbl_ram = QLabel("RAM: --")
        self.lbl_disk = QLabel("Disk: --")
        
        for lbl in [self.lbl_cpu, self.lbl_ram, self.lbl_disk]:
            lbl.setStyleSheet("font-size: 11px; border: none; background: transparent;")
            inner_layout.addWidget(lbl)
            
        self._cpu_temp = "--"
        self._ram_temp = "--"
        self._disk_temp = "--"
        
        self._drag_pos = QPoint()
        
        # Bridge
        self.bridge = MiniBridge()
        self.bridge.cpu_updated.connect(self.update_cpu)
        self.bridge.memory_updated.connect(self.update_memory)
        self.bridge.disk_updated.connect(self.update_disk)
        self.bridge.hardware_updated.connect(self.update_hardware)
        
        event_bus.subscribe("metrics_cpu", self.bridge.cpu_updated.emit)
        event_bus.subscribe("metrics_memory", self.bridge.memory_updated.emit)
        event_bus.subscribe("metrics_disk", self.bridge.disk_updated.emit)
        event_bus.subscribe("metrics_hardware", self.bridge.hardware_updated.emit)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            
    def mouseDoubleClickEvent(self, event):
        # Double click to restore main window
        if event.button() == Qt.LeftButton:
            self.hide()
            self.main_window.show()
            self.main_window.activateWindow()

    # Updaters
    def update_hardware(self, data: dict):
        temps = data.get("temperatures", {})
        if "cpu" in temps and temps["cpu"]:
            self._cpu_temp = f"{temps['cpu'][0]['current']}°C"
        if "ram" in temps and temps["ram"]:
            self._ram_temp = f"{temps['ram'][0]['current']}°C"
        if "disk" in temps and temps["disk"]:
            self._disk_temp = f"{temps['disk'][0]['current']}°C"

    def update_cpu(self, data: dict):
        self.lbl_cpu.setText(f"CPU: {data['usage']:.0f}% {self._cpu_temp}")
        
    def update_memory(self, data: dict):
        self.lbl_ram.setText(f"RAM: {data['percent']:.0f}% {self._ram_temp}")
        
    def update_disk(self, data: dict):
        partitions = data.get("partitions", [])
        if partitions:
            self.lbl_disk.setText(f"Disk: {partitions[0]['percent']:.0f}% {self._disk_temp}")
