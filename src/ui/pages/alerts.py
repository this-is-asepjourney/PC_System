from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, Signal, QObject
from src.core.events import event_bus
import time

class AlertsBridge(QObject):
    alert_triggered = Signal(object)
    alert_resolved = Signal(object)

class AlertsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Alerts")
        header.setStyleSheet("font-size: 28px; font-weight: bold; color: #cdd6f4;")
        layout.addWidget(header)
        
        # List
        self.alert_list = QListWidget()
        self.alert_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #313244;
            }
        """)
        layout.addWidget(self.alert_list)
        
        # Bridge
        self.bridge = AlertsBridge()
        self.bridge.alert_triggered.connect(self.on_alert_triggered)
        self.bridge.alert_resolved.connect(self.on_alert_resolved)
        
        event_bus.subscribe("alert_triggered", self.bridge.alert_triggered.emit)
        event_bus.subscribe("alert_resolved", self.bridge.alert_resolved.emit)
        
    def on_alert_triggered(self, alert):
        item = QListWidgetItem()
        ts = time.strftime("%H:%M:%S")
        color = "#f38ba8" if alert.severity == "Critical" else "#f9e2af"
        item.setText(f"[{ts}] 🚨 {alert.severity}: {alert.message}")
        item.setForeground(Qt.black)
        item.setBackground(Qt.red if alert.severity == "Critical" else Qt.yellow)
        self.alert_list.insertItem(0, item)
        
    def on_alert_resolved(self, alert):
        item = QListWidgetItem()
        ts = time.strftime("%H:%M:%S")
        item.setText(f"[{ts}] ✅ RESOLVED: {alert.message}")
        item.setForeground(Qt.green)
        self.alert_list.insertItem(0, item)
