from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt

class MetricCard(QFrame):
    def __init__(self, title: str, accent_color: str = "#89b4fa", parent=None):
        super().__init__(parent)
        self.setObjectName("MetricCard")
        self.accent_color = accent_color
        
        self.setStyleSheet(f"""
            QFrame#MetricCard {{
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 12px;
                padding: 14px;
            }}
            QFrame#MetricCard:hover {{
                border: 1px solid {accent_color};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        
        # Header: Title + Temperature badge
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        self.title_label = QLabel(title.upper())
        self.title_label.setStyleSheet(f"""
            font-size: 12px;
            font-weight: 700;
            color: {accent_color};
            letter-spacing: 0.8px;
        """)
        top_layout.addWidget(self.title_label)
        
        top_layout.addStretch()
        
        self.temp_badge = QLabel("")
        self.temp_badge.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.08);
            color: #f9e2af;
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: bold;
        """)
        self.temp_badge.hide()
        top_layout.addWidget(self.temp_badge)
        
        layout.addLayout(top_layout)
        
        # Main Value
        self.value_label = QLabel("--")
        self.value_label.setStyleSheet("""
            color: #ffffff;
            font-size: 26px;
            font-weight: 800;
            letter-spacing: -0.5px;
        """)
        layout.addWidget(self.value_label)
        
        # Subvalue / Detail
        self.subvalue_label = QLabel("")
        self.subvalue_label.setStyleSheet("""
            color: #a6adc8;
            font-size: 12px;
            font-weight: 500;
        """)
        self.subvalue_label.hide()
        layout.addWidget(self.subvalue_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #313244;
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {accent_color};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(self.progress_bar)
        
        layout.addStretch()

    def set_value(self, value: str, subvalue: str = "", percent: float = None, temp: str = ""):
        self.value_label.setText(value)
        if subvalue:
            self.subvalue_label.setText(subvalue)
            self.subvalue_label.show()
        else:
            self.subvalue_label.hide()
            
        if percent is not None:
            self.progress_bar.setValue(int(max(0, min(100, percent))))
            self.progress_bar.show()
        else:
            self.progress_bar.hide()
            
        if temp:
            self.set_temp(temp)
        else:
            self.temp_badge.hide()

    def set_temp(self, temp_str: str):
        if not temp_str or temp_str == "--":
            self.temp_badge.hide()
            return
            
        # Parse temperature value if possible to color code
        clean_val = temp_str.replace("°C", "").replace("C", "").strip()
        try:
            val = float(clean_val)
            if val < 55.0:
                color = "#a6e3a1" # Cool green
                bg = "rgba(166, 227, 161, 0.15)"
            elif val < 75.0:
                color = "#f9e2af" # Warm yellow
                bg = "rgba(249, 226, 175, 0.15)"
            else:
                color = "#f38ba8" # Hot red
                bg = "rgba(243, 139, 168, 0.2)"
        except ValueError:
            color = "#f9e2af"
            bg = "rgba(255, 255, 255, 0.1)"
            
        self.temp_badge.setText(f"🌡️ {temp_str}")
        self.temp_badge.setStyleSheet(f"""
            background-color: {bg};
            color: {color};
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: bold;
        """)
        self.temp_badge.show()
