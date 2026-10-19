from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QGridLayout, QProgressBar, QPushButton
)
from PySide6.QtCore import Qt, Signal, QObject
from src.core.events import event_bus

class HardwareBridge(QObject):
    hardware_updated = Signal(dict)

class HardwarePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        
        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)
        header = QLabel("Hardware & Sensors")
        header.setStyleSheet("font-size: 26px; font-weight: 800; color: #cdd6f4;")
        subtitle = QLabel("Detailed hardware telemetry, battery states, and device connectivity")
        subtitle.setStyleSheet("font-size: 13px; color: #a6adc8;")
        header_layout.addWidget(header)
        header_layout.addWidget(subtitle)
        layout.addLayout(header_layout)
        
        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background-color: transparent;")
        layout.addWidget(self.scroll)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(16)
        self.content_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.content_widget)
        
        # Section 1: Temperatures Card
        self.temp_card = QFrame()
        self.temp_card.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        self.temp_layout = QVBoxLayout(self.temp_card)
        self.temp_layout.setSpacing(12)
        
        temp_title = QLabel("🌡️ System Thermals")
        temp_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #89b4fa; border: none;")
        self.temp_layout.addWidget(temp_title)
        
        self.temp_grid = QGridLayout()
        self.temp_grid.setSpacing(10)
        self.temp_layout.addLayout(self.temp_grid)
        self.content_layout.addWidget(self.temp_card)
        
        # Section 2: Battery & Power Card
        self.battery_card = QFrame()
        self.battery_card.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        self.battery_layout = QVBoxLayout(self.battery_card)
        self.battery_layout.setSpacing(8)
        
        battery_title = QLabel("🔋 Power & Battery")
        battery_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #a6e3a1; border: none;")
        self.battery_layout.addWidget(battery_title)
        
        self.battery_info = QLabel("Checking battery status...")
        self.battery_info.setStyleSheet("color: #cdd6f4; font-size: 13px; border: none;")
        self.battery_layout.addWidget(self.battery_info)
        self.content_layout.addWidget(self.battery_card)
        
        # Section 3: Connected & Bluetooth Devices Card
        self.devices_card = QFrame()
        self.devices_card.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        self.devices_layout = QVBoxLayout(self.devices_card)
        self.devices_layout.setSpacing(8)
        
        # Header row for devices with manual refresh
        dev_header = QHBoxLayout()
        dev_title = QLabel("🔌 Connected Devices & Peripherals")
        dev_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #cba6f7; border: none;")
        dev_header.addWidget(dev_title)
        dev_header.addStretch()

        self.btn_scan_devices = QPushButton("🔄 Scan Peripherals")
        self.btn_scan_devices.setCursor(Qt.PointingHandCursor)
        self.btn_scan_devices.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cba6f7;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #cba6f7;
                color: #11111b;
            }
        """)
        self.btn_scan_devices.clicked.connect(self._manual_device_scan)
        dev_header.addWidget(self.btn_scan_devices)
        self.devices_layout.addLayout(dev_header)
        
        self.devices_info = QLabel("Klik 'Scan Peripherals' untuk memindai perangkat bluetooth & USB tanpa membebani CPU saat startup.")
        self.devices_info.setStyleSheet("color: #a6adc8; font-size: 13px; border: none;")
        self.devices_info.setWordWrap(True)
        self.devices_layout.addWidget(self.devices_info)
        self.content_layout.addWidget(self.devices_card)
        
        # Bridge
        self.bridge = HardwareBridge()
        self.bridge.hardware_updated.connect(self.update_hardware)
        event_bus.subscribe("metrics_hardware", self.bridge.hardware_updated.emit)
        
    def _manual_device_scan(self):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if hasattr(app, "monitoring_service"):
            app.monitoring_service.hardware_collector.trigger_background_device_scan(force=True)
            self.devices_info.setText("Scanning Bluetooth and connected peripherals in background...")

    def update_hardware(self, data: dict):
        if not self.isVisible():
            return
        # 1. Update Temperatures
        # Clear grid
        while self.temp_grid.count():
            item = self.temp_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
        temps = data.get("temperatures", {})
        row = 0
        if temps:
            for category, entries in temps.items():
                for entry in entries:
                    label = getattr(entry, "label", entry.get("label", str(category)) if isinstance(entry, dict) else str(category))
                    current = getattr(entry, "current", entry.get("current", 0.0) if isinstance(entry, dict) else 0.0)
                    
                    # Name label
                    lbl_name = QLabel(f"<b>{category.upper()}</b> ({label})")
                    lbl_name.setStyleSheet("color: #cdd6f4; font-size: 13px; border: none;")
                    
                    # Value label
                    color = "#a6e3a1" if current < 55.0 else ("#f9e2af" if current < 75.0 else "#f38ba8")
                    lbl_val = QLabel(f"{current:.1f}°C")
                    lbl_val.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold; border: none;")
                    
                    # Progress bar
                    pbar = QProgressBar()
                    pbar.setRange(20, 100)
                    pbar.setValue(int(current))
                    pbar.setTextVisible(False)
                    pbar.setFixedHeight(6)
                    pbar.setStyleSheet(f"""
                        QProgressBar {{
                            background-color: #313244;
                            border: none;
                            border-radius: 3px;
                        }}
                        QProgressBar::chunk {{
                            background-color: {color};
                            border-radius: 3px;
                        }}
                    """)
                    
                    self.temp_grid.addWidget(lbl_name, row, 0)
                    self.temp_grid.addWidget(lbl_val, row, 1)
                    self.temp_grid.addWidget(pbar, row, 2)
                    row += 1
        else:
            no_temp = QLabel("Thermal sensors not available natively.")
            no_temp.setStyleSheet("color: #a6adc8; border: none;")
            self.temp_grid.addWidget(no_temp, 0, 0)
            
        # 2. Update Battery
        batt = data.get("battery")
        bt_batts = data.get("bluetooth_batteries", [])
        batt_lines = []
        if batt:
            status = "Charging / Plugged in ⚡" if batt.get('power_plugged') else "On Battery 🔋"
            batt_lines.append(f"<b>System Battery:</b> {batt.get('percent', 0)}% — {status}")
            
        if bt_batts:
            for bt in bt_batts:
                batt_lines.append(f"<b>{bt.get('Name', 'Wireless Device')}:</b> {bt.get('Battery', 0)}% Battery")
                
        if not batt and not bt_batts:
            batt_lines.append("Desktop PC (Continuous AC Power) — No internal battery detected.")
            
        self.battery_info.setText("<br>".join(batt_lines))
        
        # 3. Update Devices
        connected_devices = data.get("connected_devices", [])
        if connected_devices:
            dev_lines = []
            for dev in connected_devices[:15]: # Show top 15 devices cleanly
                name = dev.get("Name", "Device")
                cls = dev.get("Class", "")
                status = dev.get("Status", "OK")
                icon = "🟢" if status == "OK" else "🔴"
                dev_lines.append(f"{icon} <b>{name}</b> <span style='color: #6c7086;'>({cls})</span>")
                
            if len(connected_devices) > 15:
                dev_lines.append(f"<span style='color: #a6adc8;'>...and {len(connected_devices) - 15} more devices</span>")
                
            self.devices_info.setText("<br>".join(dev_lines))
        else:
            self.devices_info.setText("Standard HID & System Peripherals connected.")
