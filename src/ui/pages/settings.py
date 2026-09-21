from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFormLayout, QSpinBox, QPushButton
from PySide6.QtCore import Qt
from src.core.config import config

class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Settings")
        header.setStyleSheet("font-size: 28px; font-weight: bold; color: #cdd6f4;")
        layout.addWidget(header)
        
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignLeft)
        
        # We simulate settings since we need to write back to yaml to persist
        self.cpu_thresh = QSpinBox()
        self.cpu_thresh.setRange(10, 100)
        self.cpu_thresh.setValue(int(config.get('alerts.thresholds.cpu', 90)))
        self.cpu_thresh.setStyleSheet("padding: 5px; background: #313244; color: #cdd6f4;")
        
        self.mem_thresh = QSpinBox()
        self.mem_thresh.setRange(10, 100)
        self.mem_thresh.setValue(int(config.get('alerts.thresholds.memory', 90)))
        self.mem_thresh.setStyleSheet("padding: 5px; background: #313244; color: #cdd6f4;")
        
        form_layout.addRow(QLabel("CPU Alert Threshold (%):"), self.cpu_thresh)
        form_layout.addRow(QLabel("Memory Alert Threshold (%):"), self.mem_thresh)
        
        layout.addLayout(form_layout)
        
        save_btn = QPushButton("Save Settings (Not Persisted Yet)")
        save_btn.setStyleSheet("background-color: #89b4fa; color: #11111b; padding: 10px; font-weight: bold;")
        layout.addWidget(save_btn)
        
        layout.addStretch()
