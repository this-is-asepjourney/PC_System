from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMenu
from PySide6.QtCore import Qt, Signal, QObject, QPoint, QTimer
from PySide6.QtGui import QAction
from src.core.events import event_bus

class MiniBridge(QObject):
    cpu_updated = Signal(dict)
    memory_updated = Signal(dict)
    network_updated = Signal(dict)
    disk_updated = Signal(dict)
    hardware_updated = Signal(dict)

class MiniMetricRow(QWidget):
    def __init__(self, tag: str, tag_color: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)
        
        # Tag
        self.lbl_tag = QLabel(tag)
        self.lbl_tag.setStyleSheet(f"""
            color: {tag_color};
            font-size: 11px;
            font-weight: 800;
            background: rgba(255, 255, 255, 0.06);
            border-radius: 4px;
            padding: 1px 5px;
        """)
        layout.addWidget(self.lbl_tag)
        
        # Value
        self.lbl_val = QLabel("--")
        self.lbl_val.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 700;")
        layout.addWidget(self.lbl_val)
        
        layout.addStretch()
        
        # Temp / Sub
        self.lbl_sub = QLabel("")
        self.lbl_sub.setStyleSheet("color: #a6adc8; font-size: 11px; font-weight: 600;")
        layout.addWidget(self.lbl_sub)
        
    def set_data(self, val: str, sub: str = "", sub_color: str = None):
        self.lbl_val.setText(val)
        if sub:
            self.lbl_sub.setText(sub)
            if sub_color:
                self.lbl_sub.setStyleSheet(f"color: {sub_color}; font-size: 11px; font-weight: 600;")
            self.lbl_sub.show()
        else:
            self.lbl_sub.hide()

class MiniWidget(QWidget):
    """
    Floating desktop mini widget with sleek dark card styling.
    """
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        
        # Window attributes
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(260, 165)
        
        # Keep-on-top timer
        self.top_timer = QTimer(self)
        self.top_timer.timeout.connect(self._ensure_on_top)
        self.top_timer.start(2500)
        
        self._drag_pos = QPoint()
        self._cpu_temp_val = 40.0
        self._ram_temp_val = 36.0
        self._disk_temp_val = 33.0
        self._cpu_temp_str = "--°C"
        self._ram_temp_str = "--°C"
        self._disk_temp_str = "--°C"
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        
        self.bg_frame = QWidget()
        self.bg_frame.setStyleSheet("""
            QWidget {
                background-color: rgba(24, 24, 37, 235);
                border-radius: 10px;
                border: 1px solid #313244;
                color: #cdd6f4;
                font-family: 'Segoe UI', Arial;
            }
        """)
        layout.addWidget(self.bg_frame)
        
        inner_layout = QVBoxLayout(self.bg_frame)
        inner_layout.setContentsMargins(12, 8, 12, 10)
        inner_layout.setSpacing(6)
        
        # Header (Top bar)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("⚡ SYSTEM MONITOR")
        title.setStyleSheet("font-size: 10px; font-weight: 800; color: #89b4fa; letter-spacing: 0.5px; border: none; background: transparent;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Taskbar Mode switch button
        taskbar_btn = QPushButton("📌")
        taskbar_btn.setFixedSize(20, 20)
        taskbar_btn.setCursor(Qt.PointingHandCursor)
        taskbar_btn.setToolTip("Switch to Taskbar Mode")
        taskbar_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; color: #a6adc8; font-size: 11px; }
            QPushButton:hover { color: #89b4fa; }
        """)
        taskbar_btn.clicked.connect(self.switch_to_taskbar)
        header_layout.addWidget(taskbar_btn)
        
        # Restore button
        restore_btn = QPushButton("⛶")
        restore_btn.setFixedSize(20, 20)
        restore_btn.setCursor(Qt.PointingHandCursor)
        restore_btn.setToolTip("Restore Window Mode (Dashboard)")
        restore_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; color: #a6adc8; font-size: 11px; }
            QPushButton:hover { color: #ffffff; }
        """)
        restore_btn.clicked.connect(self.restore_main)
        header_layout.addWidget(restore_btn)
        
        inner_layout.addLayout(header_layout)
        
        # Rows
        self.row_cpu = MiniMetricRow("CPU", "#74c7ec")
        self.row_ram = MiniMetricRow("RAM", "#a6e3a1")
        self.row_disk = MiniMetricRow("DSK", "#fab387")
        self.row_net = MiniMetricRow("NET", "#cba6f7")
        
        inner_layout.addWidget(self.row_cpu)
        inner_layout.addWidget(self.row_ram)
        inner_layout.addWidget(self.row_disk)
        inner_layout.addWidget(self.row_net)
            
        # Bridge setup
        self.bridge = MiniBridge()
        self.bridge.cpu_updated.connect(self.update_cpu)
        self.bridge.memory_updated.connect(self.update_memory)
        self.bridge.network_updated.connect(self.update_network)
        self.bridge.disk_updated.connect(self.update_disk)
        self.bridge.hardware_updated.connect(self.update_hardware)
        
        event_bus.subscribe("metrics_cpu", self.bridge.cpu_updated.emit)
        event_bus.subscribe("metrics_memory", self.bridge.memory_updated.emit)
        event_bus.subscribe("metrics_network", self.bridge.network_updated.emit)
        event_bus.subscribe("metrics_disk", self.bridge.disk_updated.emit)
        event_bus.subscribe("metrics_hardware", self.bridge.hardware_updated.emit)

    def restore_main(self):
        self.hide()
        self.main_window.show()
        self.main_window.activateWindow()

    def switch_to_taskbar(self):
        self.hide()
        if hasattr(self.main_window, "taskbar_widget"):
            self.main_window.taskbar_widget.show()
            self.main_window.taskbar_widget.activateWindow()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.restore_main()
            event.accept()

    def _ensure_on_top(self):
        if self.isVisible():
            self.raise_()

    def _get_temp_color(self, temp: float) -> str:
        if temp < 55.0:
            return "#a6e3a1"
        elif temp < 75.0:
            return "#f9e2af"
        else:
            return "#f38ba8"

    def update_hardware(self, data: dict):
        temps = data.get("temperatures", {})
        if "cpu" in temps and temps["cpu"]:
            curr = getattr(temps["cpu"][0], "current", temps["cpu"][0].get("current") if isinstance(temps["cpu"][0], dict) else 40.0)
            self._cpu_temp_val = float(curr)
            self._cpu_temp_str = f"{self._cpu_temp_val:.0f}°C"
            
        if "ram" in temps and temps["ram"]:
            curr = getattr(temps["ram"][0], "current", temps["ram"][0].get("current") if isinstance(temps["ram"][0], dict) else 36.0)
            self._ram_temp_val = float(curr)
            self._ram_temp_str = f"{self._ram_temp_val:.0f}°C"
            
        if "disk" in temps and temps["disk"]:
            curr = getattr(temps["disk"][0], "current", temps["disk"][0].get("current") if isinstance(temps["disk"][0], dict) else 33.0)
            self._disk_temp_val = float(curr)
            self._disk_temp_str = f"{self._disk_temp_val:.0f}°C"

    def update_cpu(self, data: dict):
        usage = data['usage']
        color = self._get_temp_color(self._cpu_temp_val)
        self.row_cpu.set_data(f"{usage:.1f}%", f"🌡️ {self._cpu_temp_str}", color)
        
    def update_memory(self, data: dict):
        pct = data['percent']
        color = self._get_temp_color(self._ram_temp_val)
        self.row_ram.set_data(f"{pct:.1f}%", f"🌡️ {self._ram_temp_str}", color)
        
    def update_disk(self, data: dict):
        partitions = data.get("partitions", [])
        pct = partitions[0]['percent'] if partitions else 0.0
        color = self._get_temp_color(self._disk_temp_val)
        self.row_disk.set_data(f"{pct:.1f}%", f"🌡️ {self._disk_temp_str}", color)

    def update_network(self, data: dict):
        dl_b = data.get('download_speed', 0.0)
        ul_b = data.get('upload_speed', 0.0)
        dl_str = self._format_speed(dl_b)
        ul_str = self._format_speed(ul_b)
        self.row_net.set_data(f"↓ {dl_str}", f"↑ {ul_str}", "#cdd6f4")

    def _format_speed(self, b_s: float) -> str:
        if b_s < 1024:
            return f"{b_s:.0f} B/s"
        elif b_s < 1024 * 1024:
            return f"{b_s / 1024:.0f} KB/s"
        elif b_s < 1024 * 1024 * 1024:
            return f"{b_s / (1024 * 1024):.1f} MB/s"
        else:
            return f"{b_s / (1024 * 1024 * 1024):.1f} GB/s"

    def _show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item:selected {
                background-color: #313244;
                color: #ffffff;
            }
        """)
        act_dash = menu.addAction("🖥️ Buka Dashboard (Window Mode)")
        act_dash.triggered.connect(self.restore_main)
        act_task = menu.addAction("📌 Pindah ke Taskbar Mode")
        act_task.triggered.connect(self.switch_to_taskbar)
        menu.addSeparator()
        act_quit = menu.addAction("✕ Keluar")
        act_quit.triggered.connect(lambda: self.main_window.close())
        menu.exec(pos)
