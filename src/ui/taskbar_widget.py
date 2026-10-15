import os
import json
import subprocess
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QMenu,
    QGraphicsDropShadowEffect, QFrame, QApplication
)
from PySide6.QtCore import Qt, QPoint, QTimer, Signal, QObject, QEvent
from PySide6.QtGui import QColor, QPainter, QCursor, QAction, QFont, QGuiApplication
from src.core.events import event_bus

CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "taskbar_config.json")

class TaskbarBridge(QObject):
    cpu_updated = Signal(dict)
    memory_updated = Signal(dict)
    disk_updated = Signal(dict)
    network_updated = Signal(dict)
    hardware_updated = Signal(dict)
    process_updated = Signal(dict)

class DragGrip(QWidget):
    """
    Ultra-compact vertical drag grip handle.
    Width: 6px. Fits seamlessly without consuming horizontal space.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(6)
        self.setFixedHeight(22)
        self._hovered = False
        self._locked = False
        self.setCursor(Qt.SizeAllCursor)
        self.setToolTip("Tahan & Geser untuk memindahkan\nKlik kanan untuk Opsi")

    def set_locked(self, locked: bool):
        self._locked = locked
        self.setCursor(Qt.ArrowCursor if locked else Qt.SizeAllCursor)
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._locked:
            color = QColor(108, 112, 134, 80)
        elif self._hovered:
            color = QColor(137, 180, 250, 220)
        else:
            color = QColor(255, 255, 255, 50)

        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        # Single rounded slim pill handle
        painter.drawRoundedRect(1, 2, 3, 18, 1.5, 1.5)

class DualRowItem(QWidget):
    """
    Single compact line within the 2-row layout.
    Displays tag badge, tabular numeric value, and temperature badge.
    Height: 15px.
    """
    def __init__(self, tag: str, tag_color: str, parent=None):
        super().__init__(parent)
        self.tag = tag
        self.tag_color = tag_color
        self._show_sub = True
        self.setFixedHeight(15)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        # Tag Badge
        self.lbl_tag = QLabel(tag)
        c = QColor(tag_color)
        self.lbl_tag.setStyleSheet(f"""
            QLabel {{
                color: {tag_color};
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 8.5px;
                font-weight: 800;
                background-color: rgba({c.red()}, {c.green()}, {c.blue()}, 0.16);
                border-radius: 2px;
                padding: 0px 3px;
                min-width: 18px;
            }}
        """)
        layout.addWidget(self.lbl_tag)

        # Primary Value (e.g. 41%)
        self.lbl_val = QLabel("--%")
        self.lbl_val.setStyleSheet("""
            QLabel {{
                color: #ffffff;
                font-family: 'Segoe UI Variable Small', 'Segoe UI', Consolas, monospace;
                font-size: 9.5px;
                font-weight: 700;
            }}
        """)
        layout.addWidget(self.lbl_val)

        # Sub / Temperature Badge (e.g. 66°C)
        self.lbl_sub = QLabel("")
        self.lbl_sub.setStyleSheet("""
            QLabel {{
                color: #a6e3a1;
                font-family: 'Segoe UI Variable Small', 'Segoe UI', Consolas, monospace;
                font-size: 8.5px;
                font-weight: 600;
                background-color: rgba(166, 227, 161, 0.12);
                border-radius: 2px;
                padding: 0px 2px;
            }}
        """)
        layout.addWidget(self.lbl_sub)

    def set_data(self, val_str: str, sub_str: str = "", sub_color: str = None, sub_bg: str = None):
        if self.lbl_val.text() != val_str:
            self.lbl_val.setText(val_str)

        if sub_str and self._show_sub:
            if self.lbl_sub.text() != sub_str:
                self.lbl_sub.setText(sub_str)
                if sub_color:
                    bg = sub_bg or "rgba(255, 255, 255, 0.08)"
                    self.lbl_sub.setStyleSheet(f"""
                        QLabel {{
                            color: {sub_color};
                            font-family: 'Segoe UI Variable Small', 'Segoe UI', Consolas, monospace;
                            font-size: 8.5px;
                            font-weight: 600;
                            background-color: {bg};
                            border-radius: 2px;
                            padding: 0px 2px;
                        }}
                    """)
            if not self.lbl_sub.isVisible():
                self.lbl_sub.show()
        else:
            if self.lbl_sub.isVisible():
                self.lbl_sub.hide()

    def set_show_sub(self, show: bool):
        self._show_sub = show
        if not show:
            self.lbl_sub.hide()
        elif self.lbl_sub.text():
            self.lbl_sub.show()

class DualRowNet(QWidget):
    """
    Stacked 2-row network bandwidth indicator.
    Row 1: ↓ Download speed
    Row 2: ↑ Upload speed
    Total height: 32px.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        # Row 1: Download
        row_dl = QHBoxLayout()
        row_dl.setContentsMargins(0, 0, 0, 0)
        row_dl.setSpacing(2)

        self.lbl_dl_icon = QLabel("↓")
        self.lbl_dl_icon.setStyleSheet("color: #38bdf8; font-size: 9px; font-weight: 900;")
        self.lbl_dl_val = QLabel("0 KB/s")
        self.lbl_dl_val.setStyleSheet("color: #ffffff; font-family: 'Segoe UI Variable Small', 'Segoe UI', Consolas, monospace; font-size: 9px; font-weight: 700;")
        row_dl.addWidget(self.lbl_dl_icon)
        row_dl.addWidget(self.lbl_dl_val)
        layout.addLayout(row_dl)

        # Row 2: Upload
        row_ul = QHBoxLayout()
        row_ul.setContentsMargins(0, 0, 0, 0)
        row_ul.setSpacing(2)

        self.lbl_ul_icon = QLabel("↑")
        self.lbl_ul_icon.setStyleSheet("color: #c084fc; font-size: 9px; font-weight: 900;")
        self.lbl_ul_val = QLabel("0 KB/s")
        self.lbl_ul_val.setStyleSheet("color: #cdd6f4; font-family: 'Segoe UI Variable Small', 'Segoe UI', Consolas, monospace; font-size: 9px; font-weight: 600;")
        row_ul.addWidget(self.lbl_ul_icon)
        row_ul.addWidget(self.lbl_ul_val)
        layout.addLayout(row_ul)

    def set_speeds(self, dl_bps: float, ul_bps: float):
        dl_str = self._format_speed(dl_bps)
        ul_str = self._format_speed(ul_bps)
        if self.lbl_dl_val.text() != dl_str:
            self.lbl_dl_val.setText(dl_str)
        if self.lbl_ul_val.text() != ul_str:
            self.lbl_ul_val.setText(ul_str)

    def _format_speed(self, b_s: float) -> str:
        if b_s < 1024:
            return f"{b_s:.0f} B/s"
        elif b_s < 1024 * 1024:
            return f"{b_s / 1024:.0f} KB/s"
        elif b_s < 1024 * 1024 * 1024:
            return f"{b_s / (1024 * 1024):.1f} MB/s"
        else:
            return f"{b_s / (1024 * 1024 * 1024):.2f} GB/s"

class DualRowBattery(QWidget):
    """
    Compact single-line battery widget for row 2.
    Height: 15px.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(15)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.lbl_icon = QLabel("⚡")
        self.lbl_icon.setStyleSheet("font-size: 9px; color: #a6e3a1;")
        layout.addWidget(self.lbl_icon)

        self.lbl_val = QLabel("100%")
        self.lbl_val.setStyleSheet("color: #a6e3a1; font-family: 'Segoe UI Variable Small', 'Segoe UI', Consolas, monospace; font-size: 9px; font-weight: 700;")
        layout.addWidget(self.lbl_val)

    def update_battery(self, battery_data: dict):
        if not battery_data:
            self.hide()
            return

        pct = battery_data.get("percent", 0)
        plugged = battery_data.get("power_plugged", False)

        self.lbl_icon.setText("⚡" if plugged else "🔋")
        self.lbl_val.setText(f"{pct:.0f}%")

        if pct < 20 and not plugged:
            color = "#f38ba8"
        elif pct < 45 and not plugged:
            color = "#f9e2af"
        else:
            color = "#a6e3a1"

        self.lbl_val.setStyleSheet(f"color: {color}; font-family: 'Segoe UI Variable Small', 'Segoe UI', Consolas, monospace; font-size: 9px; font-weight: 700;")
        self.lbl_icon.setStyleSheet(f"font-size: 9px; color: {color};")
        if not self.isVisible():
            self.show()

class TaskbarWidget(QWidget):
    """
    Next-Generation Taskbar Mode Monitor.
    Defaults to Dual-Row layout (height: 36px, width: ~210px) which fits seamlessly
    inside the Windows 11 taskbar without covering pinned app icons.
    Engineered for ultra-low CPU and memory footprint.
    """
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

        # Window Flags & Attributes
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Settings with sensible defaults
        self._settings = {
            "opacity": 0.92,
            "locked": False,
            "dock_preset": "right",
            "saved_x": None,
            "saved_y": None,
            "show_temps": True,
            "show_disk": True,
            "show_net": True,
            "show_battery": True,
            "view_mode": "dual_row"  # "dual_row", "single_compact", "single_full"
        }
        self._load_settings()

        # Telemetry Cache
        self._drag_pos = QPoint()
        self._cpu_temp_val = 40.0
        self._ram_temp_val = 36.0
        self._disk_temp_val = 33.0
        self._cpu_temp_str = "--°"
        self._ram_temp_str = "--°"
        self._disk_temp_str = "--°"

        self._cached_cpu_data = {}
        self._cached_mem_data = {}
        self._cached_disk_data = {}
        self._cached_net_data = {}
        self._cached_hw_data = {}
        self._top_cpu_proc = "-"
        self._top_mem_proc = "-"

        # Keep on top timer (gentle 5s interval to save CPU)
        self.top_timer = QTimer(self)
        self.top_timer.timeout.connect(self._ensure_on_top)
        self.top_timer.start(5000)

        # Build UI
        self._init_ui()

        # Connect Event Bus
        self.bridge = TaskbarBridge()
        self.bridge.cpu_updated.connect(self.update_cpu)
        self.bridge.memory_updated.connect(self.update_memory)
        self.bridge.disk_updated.connect(self.update_disk)
        self.bridge.network_updated.connect(self.update_network)
        self.bridge.hardware_updated.connect(self.update_hardware)
        self.bridge.process_updated.connect(self.update_process)

        event_bus.subscribe("metrics_cpu", self.bridge.cpu_updated.emit)
        event_bus.subscribe("metrics_memory", self.bridge.memory_updated.emit)
        event_bus.subscribe("metrics_disk", self.bridge.disk_updated.emit)
        event_bus.subscribe("metrics_network", self.bridge.network_updated.emit)
        event_bus.subscribe("metrics_hardware", self.bridge.hardware_updated.emit)
        event_bus.subscribe("metrics_process", self.bridge.process_updated.emit)

        # Enable Tooltip on demand via EventFilter
        self.container.installEventFilter(self)

    def _init_ui(self):
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # Main background container
        self.container = QWidget()
        self.container.setObjectName("TaskbarContainer")
        self._apply_container_style()

        # Subtle shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 1)
        self.container.setGraphicsEffect(shadow)
        root_layout.addWidget(self.container)

        # Content Layout
        self.content_layout = QHBoxLayout(self.container)
        self.content_layout.setContentsMargins(5, 2, 5, 2)
        self.content_layout.setSpacing(4)

        # 1. Drag Grip Handle (Left)
        self.grip = DragGrip(self)
        self.grip.set_locked(self._settings["locked"])
        self.content_layout.addWidget(self.grip)

        # 2. Column 1: CPU (Row 1) & RAM (Row 2)
        self.col_cpu_ram = QWidget()
        layout_col1 = QVBoxLayout(self.col_cpu_ram)
        layout_col1.setContentsMargins(0, 0, 0, 0)
        layout_col1.setSpacing(1)

        self.item_cpu = DualRowItem("CPU", "#74c7ec", self.col_cpu_ram)
        self.item_ram = DualRowItem("RAM", "#a6e3a1", self.col_cpu_ram)
        layout_col1.addWidget(self.item_cpu)
        layout_col1.addWidget(self.item_ram)
        self.content_layout.addWidget(self.col_cpu_ram)

        # Divider 1
        self.div1 = self._create_divider()
        self.content_layout.addWidget(self.div1)

        # 3. Column 2: DSK (Row 1) & Battery (Row 2)
        self.col_dsk_bat = QWidget()
        layout_col2 = QVBoxLayout(self.col_dsk_bat)
        layout_col2.setContentsMargins(0, 0, 0, 0)
        layout_col2.setSpacing(1)

        self.item_dsk = DualRowItem("DSK", "#fab387", self.col_dsk_bat)
        self.item_bat = DualRowBattery(self.col_dsk_bat)
        layout_col2.addWidget(self.item_dsk)
        layout_col2.addWidget(self.item_bat)
        self.content_layout.addWidget(self.col_dsk_bat)

        # Divider 2
        self.div2 = self._create_divider()
        self.content_layout.addWidget(self.div2)

        # 4. Column 3: Network Bandwidth (Down & Up stacked)
        self.net_block = DualRowNet(self)
        self.content_layout.addWidget(self.net_block)

        # 5. Quick Restore Button (↗)
        self.btn_restore = QPushButton("↗")
        self.btn_restore.setFixedSize(14, 14)
        self.btn_restore.setCursor(Qt.PointingHandCursor)
        self.btn_restore.setToolTip("Buka Window Utama (atau Double Click)")
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
        self.content_layout.addWidget(self.btn_restore)

        self._apply_element_visibility()

    def _apply_container_style(self):
        alpha = int(self._settings["opacity"] * 255)
        self.container.setStyleSheet(f"""
            QWidget#TaskbarContainer {{
                background-color: rgba(18, 18, 26, {alpha});
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-top: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 6px;
            }}
            QWidget#TaskbarContainer:hover {{
                border-color: rgba(137, 180, 250, 0.35);
            }}
        """)

    def _create_divider(self) -> QFrame:
        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setFrameShadow(QFrame.Plain)
        divider.setFixedWidth(1)
        divider.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.08);
                border: none;
                margin-top: 4px;
                margin-bottom: 4px;
            }
        """)
        return divider

    def _apply_element_visibility(self):
        show_temps = self._settings["show_temps"]
        show_disk = self._settings["show_disk"]
        show_net = self._settings["show_net"]
        show_bat = self._settings["show_battery"]

        self.item_cpu.set_show_sub(show_temps)
        self.item_ram.set_show_sub(show_temps)
        self.item_dsk.set_show_sub(show_temps)

        # DSK & Battery Column
        self.col_dsk_bat.setVisible(show_disk or show_bat)
        self.item_dsk.setVisible(show_disk)
        self.item_bat.setVisible(show_bat)
        self.div1.setVisible(show_disk or show_bat)

        # Net Column
        self.net_block.setVisible(show_net)
        self.div2.setVisible(show_net and (show_disk or show_bat))

        self.adjustSize()

    def _get_temp_color_and_bg(self, temp_val: float) -> tuple[str, str]:
        if temp_val < 55.0:
            return ("#a6e3a1", "rgba(166, 227, 161, 0.12)")
        elif temp_val < 75.0:
            return ("#f9e2af", "rgba(249, 226, 175, 0.14)")
        else:
            return ("#f38ba8", "rgba(243, 139, 168, 0.18)")

    # Updaters
    def update_hardware(self, data: dict):
        self._cached_hw_data = data
        temps = data.get("temperatures", {})
        if "cpu" in temps and temps["cpu"]:
            curr = getattr(temps["cpu"][0], "current", temps["cpu"][0].get("current") if isinstance(temps["cpu"][0], dict) else 40.0)
            self._cpu_temp_val = float(curr)
            self._cpu_temp_str = f"{self._cpu_temp_val:.0f}°"

        if "ram" in temps and temps["ram"]:
            curr = getattr(temps["ram"][0], "current", temps["ram"][0].get("current") if isinstance(temps["ram"][0], dict) else 36.0)
            self._ram_temp_val = float(curr)
            self._ram_temp_str = f"{self._ram_temp_val:.0f}°"

        if "disk" in temps and temps["disk"]:
            curr = getattr(temps["disk"][0], "current", temps["disk"][0].get("current") if isinstance(temps["disk"][0], dict) else 33.0)
            self._disk_temp_val = float(curr)
            self._disk_temp_str = f"{self._disk_temp_val:.0f}°"

        # Battery update
        if self._settings["show_battery"]:
            battery_data = data.get("battery")
            if battery_data:
                self.item_bat.update_battery(battery_data)
            else:
                self.item_bat.hide()

    def update_cpu(self, data: dict):
        self._cached_cpu_data = data
        usage = data.get('usage', 0.0)
        fg_col, bg_col = self._get_temp_color_and_bg(self._cpu_temp_val)
        self.item_cpu.set_data(f"{usage:.0f}%", self._cpu_temp_str, fg_col, bg_col)

    def update_memory(self, data: dict):
        self._cached_mem_data = data
        pct = data.get('percent', 0.0)
        fg_col, bg_col = self._get_temp_color_and_bg(self._ram_temp_val)
        self.item_ram.set_data(f"{pct:.0f}%", self._ram_temp_str, fg_col, bg_col)

    def update_disk(self, data: dict):
        self._cached_disk_data = data
        if not self._settings["show_disk"]:
            return
        partitions = data.get("partitions", [])
        pct = partitions[0]['percent'] if partitions else 0.0
        fg_col, bg_col = self._get_temp_color_and_bg(self._disk_temp_val)
        self.item_dsk.set_data(f"{pct:.0f}%", self._disk_temp_str, fg_col, bg_col)

    def update_network(self, data: dict):
        self._cached_net_data = data
        if not self._settings["show_net"]:
            return
        dl_bytes = data.get('download_speed', 0.0)
        ul_bytes = data.get('upload_speed', 0.0)
        self.net_block.set_speeds(dl_bytes, ul_bytes)

    def update_process(self, data: dict):
        procs = data.get("processes", [])
        if procs:
            top_cpu = procs[0]
            self._top_cpu_proc = f"{top_cpu.get('name', 'App')} ({top_cpu.get('cpu', 0):.1f}%)"
            top_mem = max(procs, key=lambda p: p.get('memory', 0), default=None)
            if top_mem:
                mem_mb = top_mem.get('memory', 0) / (1024 * 1024)
                self._top_mem_proc = f"{top_mem.get('name', 'App')} ({mem_mb:.0f} MB)"

    # Tooltip on Demand
    def eventFilter(self, watched, event):
        if event.type() == QEvent.ToolTip:
            self._generate_tooltip()
        return super().eventFilter(watched, event)

    def _generate_tooltip(self):
        cpu_usage = self._cached_cpu_data.get('usage', 0.0)
        cpu_freq = self._cached_cpu_data.get('frequency', 0.0)
        mem_pct = self._cached_mem_data.get('percent', 0.0)
        total_gb = self._cached_mem_data.get('total', 0) / (1024**3)
        used_gb = self._cached_mem_data.get('used', 0) / (1024**3)
        dl_b = self._cached_net_data.get('download_speed', 0.0)
        ul_b = self._cached_net_data.get('upload_speed', 0.0)
        dl_fmt = self.net_block._format_speed(dl_b)
        ul_fmt = self.net_block._format_speed(ul_b)

        tt = f"""
            <div style="font-family: 'Segoe UI', Arial; font-size: 11px; line-height: 140%;">
                <b style="color: #74c7ec;">⚡ CPU:</b> {cpu_usage:.0f}% ({cpu_freq:.0f} MHz) | Suhu: {self._cpu_temp_str}C<br>
                <b style="color: #a6e3a1;">🧠 RAM:</b> {mem_pct:.0f}% ({used_gb:.1f}/{total_gb:.1f} GB) | Suhu: {self._ram_temp_str}C<br>
                <b style="color: #fab387;">💾 DSK:</b> Suhu: {self._disk_temp_str}C<br>
                <b style="color: #38bdf8;">↓ DL:</b> {dl_fmt} &nbsp;|&nbsp; <b style="color: #c084fc;">↑ UL:</b> {ul_fmt}<br>
                <span style="color: #a6adc8;">Top CPU: {self._top_cpu_proc}</span>
            </div>
        """
        self.container.setToolTip(tt)

    # Window Dragging & Mouse Events
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self._settings["locked"]:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self._settings["locked"]:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and not self._settings["locked"]:
            self._settings["dock_preset"] = "custom"
            self._settings["saved_x"] = self.x()
            self._settings["saved_y"] = self.y()
            self._save_settings()

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

    def position_in_taskbar(self, align: str = None):
        """
        Calculates exact coordinates and docks widget safely in taskbar
        without overlapping pinned app icons.
        """
        if align:
            self._settings["dock_preset"] = align
            self._save_settings()
        else:
            align = self._settings["dock_preset"]

        screen = self.screen()
        if not screen:
            screen = QGuiApplication.primaryScreen()

        geom = screen.geometry()
        avail = screen.availableGeometry()

        taskbar_height = geom.height() - avail.height()
        if taskbar_height <= 0:
            taskbar_height = 48  # Default Windows 11 taskbar height

        self.adjustSize()
        widget_w = max(self.sizeHint().width(), self.width())
        widget_h = 36  # Ergonomic height for 2 rows in taskbar
        self.setFixedHeight(widget_h)

        # Vertically centered in bottom taskbar
        target_y = geom.height() - taskbar_height + (taskbar_height - widget_h) // 2
        if target_y + widget_h > geom.height():
            target_y = geom.height() - widget_h - 2
        if target_y < 0:
            target_y = 0

        # Target X based on alignment
        if align == "right":
            # Safely docked to the right, just to the left of Windows 11 system tray
            target_x = avail.right() - widget_w - 180
        elif align == "center":
            target_x = (geom.width() - widget_w) // 2
        elif align == "left":
            target_x = 120
        elif align == "custom" and self._settings["saved_x"] is not None:
            target_x = self._settings["saved_x"]
            target_y = self._settings["saved_y"]
        else:
            target_x = avail.right() - widget_w - 180

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
                padding: 5px 20px 5px 12px;
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

        act_opt = menu.addAction("🚀  Buka Optimizer")
        act_opt.triggered.connect(self._open_optimizer)

        act_tm = menu.addAction("⚙️  Buka Windows Task Manager")
        act_tm.triggered.connect(self._open_task_manager)

        menu.addSeparator()

        # Component Toggles submenu
        comp_menu = menu.addMenu("👁️  Elemen Ditampilkan")
        comp_menu.setStyleSheet(menu.styleSheet())

        act_t_temps = comp_menu.addAction(f"{'✓ ' if self._settings['show_temps'] else '    '}Suhu (°C)")
        act_t_temps.triggered.connect(self._toggle_temps)

        act_t_disk = comp_menu.addAction(f"{'✓ ' if self._settings['show_disk'] else '    '}Kolom Penyimpanan (DSK)")
        act_t_disk.triggered.connect(self._toggle_disk)

        act_t_net = comp_menu.addAction(f"{'✓ ' if self._settings['show_net'] else '    '}Kolom Network (NET)")
        act_t_net.triggered.connect(self._toggle_net)

        act_t_batt = comp_menu.addAction(f"{'✓ ' if self._settings['show_battery'] else '    '}Baterai (jika ada)")
        act_t_batt.triggered.connect(self._toggle_battery)

        # Docking submenu
        dock_menu = menu.addMenu("📍  Dock ke Taskbar")
        dock_menu.setStyleSheet(menu.styleSheet())

        act_dock_r = dock_menu.addAction("Kanan (Dekat System Tray)")
        act_dock_r.triggered.connect(lambda: self.position_in_taskbar("right"))

        act_dock_c = dock_menu.addAction("Tengah")
        act_dock_c.triggered.connect(lambda: self.position_in_taskbar("center"))

        act_dock_l = dock_menu.addAction("Kiri")
        act_dock_l.triggered.connect(lambda: self.position_in_taskbar("left"))

        # Lock toggle
        act_lock = menu.addAction(f"{'🔓 Buka Kunci Posisi' if self._settings['locked'] else '🔒 Kunci Posisi'}")
        act_lock.triggered.connect(self._toggle_lock)

        # Opacity submenu
        opacity_menu = menu.addMenu("👁️  Transparansi")
        opacity_menu.setStyleSheet(menu.styleSheet())
        for pct, val in [("100%", 1.0), ("92%", 0.92), ("85%", 0.85), ("75%", 0.75)]:
            act_op = opacity_menu.addAction(f"{'✓ ' if abs(self._settings['opacity'] - val) < 0.02 else '    '}{pct}")
            act_op.triggered.connect(lambda checked=False, v=val: self._set_opacity(v))

        menu.addSeparator()
        act_quit = menu.addAction("✕  Keluar Aplikasi")
        act_quit.triggered.connect(self._quit_app)

        menu.exec(pos)

    def _toggle_temps(self):
        self._settings["show_temps"] = not self._settings["show_temps"]
        self._apply_element_visibility()
        self._save_settings()
        self.position_in_taskbar()

    def _toggle_disk(self):
        self._settings["show_disk"] = not self._settings["show_disk"]
        self._apply_element_visibility()
        self._save_settings()
        self.position_in_taskbar()

    def _toggle_net(self):
        self._settings["show_net"] = not self._settings["show_net"]
        self._apply_element_visibility()
        self._save_settings()
        self.position_in_taskbar()

    def _toggle_battery(self):
        self._settings["show_battery"] = not self._settings["show_battery"]
        self._apply_element_visibility()
        self._save_settings()
        self.position_in_taskbar()

    def _toggle_lock(self):
        self._settings["locked"] = not self._settings["locked"]
        self.grip.set_locked(self._settings["locked"])
        self._save_settings()

    def _set_opacity(self, val: float):
        self._settings["opacity"] = val
        self._apply_container_style()
        self._save_settings()

    def _switch_to_mini(self):
        self.hide()
        if hasattr(self.main_window, "mini_widget"):
            self.main_window.mini_widget.show()
            self.main_window.mini_widget.activateWindow()

    def _open_optimizer(self):
        self.restore_window_mode()
        if hasattr(self.main_window, "change_page"):
            self.main_window.change_page("optimizer")

    def _open_task_manager(self):
        try:
            subprocess.Popen(["taskmgr"], shell=True)
        except Exception:
            pass

    def _quit_app(self):
        QApplication.instance().quit()

    # Settings Persistence
    def _load_settings(self):
        if os.path.exists(CONFIG_FILE_PATH):
            try:
                with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self._settings.update(loaded)
            except Exception:
                pass

    def _save_settings(self):
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
            with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2)
        except Exception:
            pass
