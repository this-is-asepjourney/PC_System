import sys
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QMenu, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QPoint, QTimer, Signal, QObject
from PySide6.QtGui import QColor, QAction, QFont, QCursor
from src.core.events import event_bus

class TaskbarBridge(QObject):
    cpu_updated = Signal(dict)
    memory_updated = Signal(dict)
    disk_updated = Signal(dict)
    network_updated = Signal(dict)
    hardware_updated = Signal(dict)

class TaskbarMetricBlock(QWidget):
    """Compact high-information-density metric block for taskbar."""
    def __init__(self, tag: str, tag_color: str, parent=None):
        super().__init__(parent)
        self.tag = tag
        self.tag_color = tag_color
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 1, 6, 1)
        layout.setSpacing(5)
        
        # Tag badge (e.g. CPU, RAM, DSK, NET)
        self.lbl_tag = QLabel(tag)
        self.lbl_tag.setStyleSheet(f"""
            QLabel {{
                color: {tag_color};
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10px;
                font-weight: 800;
                background-color: rgba(255, 255, 255, 0.06);
                border-radius: 3px;
                padding: 1px 4px;
            }}
        """)
        layout.addWidget(self.lbl_tag)
        
        # Primary value (e.g. 45%, or speed)
        self.lbl_val = QLabel("--")
        self.lbl_val.setStyleSheet("""
            QLabel {{
                color: #ffffff;
                font-family: 'Segoe UI Variable Small', 'Segoe UI', Consolas, monospace;
                font-size: 11px;
                font-weight: 700;
            }}
        """)
        layout.addWidget(self.lbl_val)
        
        # Secondary badge (e.g. temp 48°C or upload speed)
        self.lbl_sub = QLabel("")
        self.lbl_sub.setStyleSheet("""
            QLabel {{
                color: #a6e3a1;
                font-family: 'Segoe UI Variable Small', 'Segoe UI', Consolas, monospace;
                font-size: 10px;
                font-weight: 600;
                background: transparent;
            }}
        """)
        layout.addWidget(self.lbl_sub)
        
    def set_data(self, val: str, sub: str = "", sub_color: str = None):
        self.lbl_val.setText(val)
        if sub:
            self.lbl_sub.setText(sub)
            if sub_color:
                self.lbl_sub.setStyleSheet(f"""
                    QLabel {{
                        color: {sub_color};
                        font-family: 'Segoe UI Variable Small', 'Segoe UI', Consolas, monospace;
                        font-size: 10px;
                        font-weight: 600;
                        background: transparent;
                    }}
                """)
            self.lbl_sub.show()
        else:
            self.lbl_sub.hide()

class TaskbarWidget(QWidget):
    """
    Ultra-sleek, professional Taskbar Mode widget.
    Displays CPU + temp, RAM + temp, Disk + temp, and Internet Bandwidth.
    Fits seamlessly in the Windows taskbar with acrylic styling, drag, and snap.
    """
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        
        # Window attributes
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # State
        self._locked = False
        self._drag_pos = QPoint()
        self._opacity = 0.92
        self._cpu_temp_val = 40.0
        self._ram_temp_val = 36.0
        self._disk_temp_val = 33.0
        self._cpu_temp_str = "--°C"
        self._ram_temp_str = "--°C"
        self._disk_temp_str = "--°C"
        
        # Setup keep-on-top timer
        self.top_timer = QTimer(self)
        self.top_timer.timeout.connect(self._ensure_on_top)
        self.top_timer.start(2500)
        
        # Main Layout
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        
        # Background Container Card
        self.container = QWidget()
        self.container.setObjectName("TaskbarContainer")
        self._apply_container_style()
        
        # Add subtle drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(14)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 2)
        self.container.setGraphicsEffect(shadow)
        
        root_layout.addWidget(self.container)
        
        # Content Layout
        content_layout = QHBoxLayout(self.container)
        content_layout.setContentsMargins(6, 2, 6, 2)
        content_layout.setSpacing(2)
        
        # 1. Drag Grip Icon (⋮⋮)
        self.grip_icon = QLabel("⋮⋮")
        self.grip_icon.setStyleSheet("""
            QLabel {
                color: #585b70;
                font-size: 11px;
                font-weight: bold;
                padding-right: 2px;
            }
            QLabel:hover {
                color: #89b4fa;
            }
        """)
        self.grip_icon.setToolTip("Drag to move / Right click for options")
        content_layout.addWidget(self.grip_icon)
        
        # 2. CPU + Temp Block
        self.block_cpu = TaskbarMetricBlock("CPU", "#74c7ec")
        self.block_cpu.setToolTip("CPU Load & Package Temperature")
        content_layout.addWidget(self.block_cpu)
        
        content_layout.addWidget(self._create_divider())
        
        # 3. RAM + Temp Block
        self.block_ram = TaskbarMetricBlock("RAM", "#a6e3a1")
        self.block_ram.setToolTip("RAM Memory Usage & Module Temperature")
        content_layout.addWidget(self.block_ram)
        
        content_layout.addWidget(self._create_divider())
        
        # 4. DISK + Temp Block
        self.block_disk = TaskbarMetricBlock("DSK", "#fab387")
        self.block_disk.setToolTip("Primary Disk Usage & Drive Temperature")
        content_layout.addWidget(self.block_disk)
        
        content_layout.addWidget(self._create_divider())
        
        # 5. NET Bandwidth Block
        self.block_net = TaskbarMetricBlock("NET", "#cba6f7")
        self.block_net.setToolTip("Internet Download & Upload Speed")
        content_layout.addWidget(self.block_net)
        
        # 6. Quick Restore Button (⛶)
        self.btn_restore = QPushButton("⛶")
        self.btn_restore.setFixedSize(18, 18)
        self.btn_restore.setCursor(Qt.PointingHandCursor)
        self.btn_restore.setToolTip("Kembali ke Window Mode (Double click anywhere)")
        self.btn_restore.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #6c7086;
                font-size: 10px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                color: #ffffff;
                background-color: rgba(255, 255, 255, 0.12);
                border-radius: 3px;
            }
        """)
        self.btn_restore.clicked.connect(self.restore_window_mode)
        content_layout.addWidget(self.btn_restore)
        
        # Event Bus Bridge
        self.bridge = TaskbarBridge()
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

    def _apply_container_style(self):
        alpha = int(self._opacity * 255)
        self.container.setStyleSheet(f"""
            QWidget#TaskbarContainer {{
                background-color: rgba(18, 18, 26, {alpha});
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 7px;
            }}
            QWidget#TaskbarContainer:hover {{
                border: 1px solid rgba(137, 180, 250, 0.4);
            }}
        """)

    def _create_divider(self) -> QLabel:
        divider = QLabel("|")
        divider.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.15);
                font-size: 10px;
                padding: 0 1px;
            }
        """)
        return divider

    def _get_temp_color(self, temp_val: float) -> str:
        if temp_val < 55.0:
            return "#a6e3a1" # Cool Mint
        elif temp_val < 75.0:
            return "#f9e2af" # Warm Amber
        else:
            return "#f38ba8" # Hot Coral Red

    # Metric Updaters
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
        self.block_cpu.set_data(f"{usage:.0f}%", self._cpu_temp_str, color)
        
    def update_memory(self, data: dict):
        pct = data['percent']
        color = self._get_temp_color(self._ram_temp_val)
        self.block_ram.set_data(f"{pct:.0f}%", self._ram_temp_str, color)
        
    def update_disk(self, data: dict):
        partitions = data.get("partitions", [])
        pct = partitions[0]['percent'] if partitions else 0
        color = self._get_temp_color(self._disk_temp_val)
        self.block_disk.set_data(f"{pct:.0f}%", self._disk_temp_str, color)

    def update_network(self, data: dict):
        dl_bytes = data.get('download_speed', 0.0)
        ul_bytes = data.get('upload_speed', 0.0)
        
        dl_fmt = self._format_compact_speed(dl_bytes)
        ul_fmt = self._format_compact_speed(ul_bytes)
        
        # High-density format: "↓ 1.2M" and sub "↑ 240K"
        self.block_net.set_data(f"↓{dl_fmt}", f"↑{ul_fmt}", "#cdd6f4")

    def _format_compact_speed(self, b_s: float) -> str:
        if b_s < 1024:
            return f"{b_s:.0f}B"
        elif b_s < 1024 * 1024:
            return f"{b_s / 1024:.0f}K"
        elif b_s < 1024 * 1024 * 1024:
            return f"{b_s / (1024 * 1024):.1f}M"
        else:
            return f"{b_s / (1024 * 1024 * 1024):.1f}G"

    # Mouse & Window Drag / Interaction
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self._locked:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self._locked:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.restore_window_mode()
            event.accept()

    def _ensure_on_top(self):
        if self.isVisible():
            self.raise_()

    def restore_window_mode(self):
        self.hide()
        self.main_window.show()
        self.main_window.activateWindow()

    def showEvent(self, event):
        super().showEvent(event)
        self.adjustSize()
        QTimer.singleShot(20, self.position_in_taskbar)

    def position_in_taskbar(self, align: str = "right"):
        """
        Calculates exact taskbar coordinates and positions widget neatly.
        align can be 'right' (near tray), 'center', or 'left'.
        """
        screen = self.screen()
        if not screen:
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
            
        geom = screen.geometry()
        avail = screen.availableGeometry()
        
        # Calculate taskbar dimensions and position
        taskbar_height = geom.height() - avail.height()
        if taskbar_height <= 0:
            taskbar_height = 42 # fallback
            
        widget_w = max(self.width(), 410)
        widget_h = max(self.height(), 32)
        
        # Target Y: horizontally centered vertically in bottom taskbar
        target_y = geom.height() - taskbar_height + (taskbar_height - widget_h) // 2
        
        # Guard Y against overlapping offscreen
        if target_y + widget_h > geom.height():
            target_y = geom.height() - widget_h - 2
            
        # Target X based on alignment
        if align == "right":
            # Just to the left of the Windows system tray icons
            target_x = avail.width() - widget_w - 230
        elif align == "center":
            target_x = (geom.width() - widget_w) // 2
        else: # left
            target_x = 120
            
        # Guard X boundaries
        target_x = max(10, min(geom.width() - widget_w - 10, target_x))
            
        self.move(target_x, target_y)

    def _show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 4px;
                font-family: 'Segoe UI', Arial;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 20px 6px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #313244;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #313244;
                margin: 4px 6px;
            }
        """)
        
        act_dashboard = menu.addAction("🖥️  Buka Window Mode (Dashboard)")
        act_dashboard.triggered.connect(self.restore_window_mode)
        
        act_mini = menu.addAction("🗗  Buka Mini Widget")
        act_mini.triggered.connect(self._switch_to_mini)
        
        menu.addSeparator()
        
        # Docking presets
        dock_menu = menu.addMenu("📍  Dock ke Taskbar")
        dock_menu.setStyleSheet(menu.styleSheet())
        
        act_dock_r = dock_menu.addAction("Kanan (Dekat System Tray)")
        act_dock_r.triggered.connect(lambda: self.position_in_taskbar("right"))
        
        act_dock_c = dock_menu.addAction("Tengah")
        act_dock_c.triggered.connect(lambda: self.position_in_taskbar("center"))
        
        act_dock_l = dock_menu.addAction("Kiri")
        act_dock_l.triggered.connect(lambda: self.position_in_taskbar("left"))
        
        # Lock toggle
        act_lock = menu.addAction(f"{'🔓 Buka' if self._locked else '🔒 Kunci'} Posisi")
        act_lock.triggered.connect(self._toggle_lock)
        
        # Opacity submenu
        opacity_menu = menu.addMenu("👁️  Transparansi")
        opacity_menu.setStyleSheet(menu.styleSheet())
        for pct, val in [("100%", 1.0), ("90%", 0.90), ("80%", 0.80), ("70%", 0.70)]:
            act_op = opacity_menu.addAction(pct)
            act_op.triggered.connect(lambda checked=False, v=val: self._set_opacity(v))
            
        menu.addSeparator()
        act_quit = menu.addAction("✕  Keluar")
        act_quit.triggered.connect(self._quit_app)
        
        menu.exec(pos)

    def _toggle_lock(self):
        self._locked = not self._locked

    def _set_opacity(self, val: float):
        self._opacity = val
        self._apply_container_style()

    def _switch_to_mini(self):
        self.hide()
        if hasattr(self.main_window, "mini_widget"):
            self.main_window.mini_widget.show()
            self.main_window.mini_widget.activateWindow()

    def _quit_app(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()
