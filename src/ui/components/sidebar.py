from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Signal, Qt

class Sidebar(QFrame):
    page_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(200)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 20, 0, 20)
        self.layout.setSpacing(5)
        
        # Title
        title = QLabel("PC-SYSTEM")
        title.setObjectName("MetricValue")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("margin-bottom: 20px; color: #89b4fa;")
        self.layout.addWidget(title)
        
        self.buttons = {}
        
        self._add_nav_button("Dashboard", "dashboard")
        self._add_nav_button("Processes", "processes")
        self._add_nav_button("Hardware", "hardware")
        self._add_nav_button("Alerts", "alerts")
        self._add_nav_button("Settings", "settings")
        
        self.layout.addStretch()
        
        # Mini mode button at the bottom
        mini_btn = QPushButton("🗗 Mini Mode")
        mini_btn.setProperty("class", "SidebarButton")
        mini_btn.clicked.connect(self._on_mini_mode_clicked)
        self.layout.addWidget(mini_btn)
        
        # Select first by default
        self.set_active("dashboard")

    def _add_nav_button(self, text: str, page_id: str):
        btn = QPushButton(text)
        btn.setProperty("class", "SidebarButton")
        btn.setCheckable(True)
        btn.clicked.connect(lambda: self._on_button_clicked(page_id))
        self.layout.addWidget(btn)
        self.buttons[page_id] = btn

    def _on_button_clicked(self, page_id: str):
        self.set_active(page_id)
        self.page_changed.emit(page_id)
        
    def _on_mini_mode_clicked(self):
        self.window().hide()
        if hasattr(self.window(), "mini_widget"):
            self.window().mini_widget.show()
            self.window().mini_widget.activateWindow()

    def set_active(self, page_id: str):
        for pid, btn in self.buttons.items():
            btn.setChecked(pid == page_id)
