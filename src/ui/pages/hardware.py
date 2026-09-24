from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PySide6.QtCore import Qt, Signal, QObject
from src.core.events import event_bus

class HardwareBridge(QObject):
    hardware_updated = Signal(dict)

class HardwarePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Hardware & Sensors")
        header.setStyleSheet("font-size: 28px; font-weight: bold; color: #cdd6f4;")
        layout.addWidget(header)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background-color: transparent;")
        layout.addWidget(self.scroll)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.content_widget)
        
        self.info_label = QLabel("Waiting for data...")
        self.info_label.setStyleSheet("color: #a6adc8; font-size: 16px;")
        self.info_label.setWordWrap(True)
        self.content_layout.addWidget(self.info_label)
        
        self.bridge = HardwareBridge()
        self.bridge.hardware_updated.connect(self.update_hardware)
        event_bus.subscribe("metrics_hardware", self.bridge.hardware_updated.emit)
        
    def update_hardware(self, data: dict):
        lines = []
        
        # Battery
        batt = data.get("battery")
        if batt:
            lines.append("🔋 <b>System Battery</b>")
            lines.append(f"Level: {batt['percent']}%")
            lines.append(f"Plugged In: {'Yes' if batt['power_plugged'] else 'No'}")
            lines.append("")
            
        # Bluetooth Batteries
        bt_batts = data.get("bluetooth_batteries", [])
        if bt_batts:
            lines.append("🖱️ <b>Bluetooth Devices Battery</b>")
            for bt in bt_batts:
                lines.append(f"{bt.get('Name', 'Unknown Device')}: {bt.get('Battery', 0)}%")
            lines.append("")
            
        # Temperatures
        temps = data.get("temperatures", {})
        if temps:
            lines.append("🌡️ <b>Temperatures</b>")
            for name, entries in temps.items():
                for entry in entries:
                    lines.append(f"{name} ({entry.label}): {entry.current}°C")
            lines.append("")
            
        # Fans
        fans = data.get("fans", {})
        if fans:
            lines.append("❄️ <b>Fans</b>")
            for name, entries in fans.items():
                for entry in entries:
                    lines.append(f"{name} ({entry.label}): {entry.current} RPM")
            lines.append("")

        # Connected Devices
        connected_devices = data.get("connected_devices", [])
        if connected_devices:
            lines.append("🔌 <b>Connected Devices</b>")
            
            # Group by Class or just list them
            # We'll list them sorted by status (OK first, then others)
            # Actually just list all
            for dev in connected_devices:
                name = dev.get("Name", "Unknown")
                status = dev.get("Status", "Unknown")
                cls = dev.get("Class", "")
                
                status_icon = "🟢" if status == "OK" else "🔴"
                lines.append(f"{status_icon} <b>{name}</b> ({cls}) - {status}")
                
            lines.append("")
                    
        if not lines:
            self.info_label.setText("No hardware sensors available on this system natively via psutil.")
        else:
            self.info_label.setText("<br>".join(lines))
