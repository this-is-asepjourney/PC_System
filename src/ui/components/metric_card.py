from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import Qt

class MetricCard(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("MetricCard")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        self.title_label = QLabel(title)
        self.title_label.setObjectName("MetricTitle")
        
        self.value_label = QLabel("--")
        self.value_label.setObjectName("MetricValue")
        
        self.subvalue_label = QLabel("")
        self.subvalue_label.setObjectName("MetricSubValue")
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.subvalue_label)
        layout.addStretch()

    def set_value(self, value: str, subvalue: str = ""):
        self.value_label.setText(value)
        if subvalue:
            self.subvalue_label.setText(subvalue)
            self.subvalue_label.show()
        else:
            self.subvalue_label.hide()
