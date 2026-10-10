from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QLabel, QHBoxLayout
from PySide6.QtCore import Signal, Qt

class Sidebar(QFrame):
    page_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(210)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 20, 0, 20)
        self.layout.setSpacing(4)
        
        # Brand Header
        brand_layout = QVBoxLayout()
        brand_layout.setContentsMargins(16, 0, 16, 15)
        brand_layout.setSpacing(4)
        
        title = QLabel("⚡ PC-SYSTEM")
        title.setStyleSheet("font-size: 16px; font-weight: 800; color: #89b4fa; letter-spacing: 0.5px;")
        brand_layout.addWidget(title)
        
        status_sub = QLabel("● Live System Monitor")
        status_sub.setStyleSheet("font-size: 11px; color: #a6e3a1; font-weight: 600;")
        brand_layout.addWidget(status_sub)
        
        self.layout.addLayout(brand_layout)
        
        # Nav label
        nav_lbl = QLabel("NAVIGATION")
        nav_lbl.setStyleSheet("font-size: 10px; font-weight: 700; color: #6c7086; padding: 5px 16px; letter-spacing: 1px;")
        self.layout.addWidget(nav_lbl)
        
        self.buttons = {}
        self._add_nav_button("📊 Dashboard", "dashboard")
        self._add_nav_button("⚡ Processes", "processes")
        self._add_nav_button("🌡️ Hardware", "hardware")
        self._add_nav_button("🔍 Analyze", "analyze")
        self._add_nav_button("🚀 Optimizer", "optimizer")
        self._add_nav_button("⚙️ Settings", "settings")
        
        self.layout.addStretch()
        
        # Quick Switch Modes Section
        modes_lbl = QLabel("OVERLAY MODES")
        modes_lbl.setStyleSheet("font-size: 10px; font-weight: 700; color: #6c7086; padding: 5px 16px; letter-spacing: 1px;")
        self.layout.addWidget(modes_lbl)
        
        taskbar_btn = QPushButton("📌 Taskbar Mode")
        taskbar_btn.setProperty("class", "SidebarActionBtn")
        taskbar_btn.setToolTip("Dock compact monitor directly onto Windows Taskbar")
        taskbar_btn.clicked.connect(self._on_taskbar_mode_clicked)
        self.layout.addWidget(taskbar_btn)
        
        mini_btn = QPushButton("🗗 Mini Widget")
        mini_btn.setProperty("class", "SidebarActionBtn")
        mini_btn.setToolTip("Floating compact desktop widget")
        mini_btn.clicked.connect(self._on_mini_mode_clicked)
        self.layout.addWidget(mini_btn)
        
        # Select first by default
        self.set_active("dashboard")

    def _add_nav_button(self, text: str, page_id: str):
        btn = QPushButton(text)
        btn.setProperty("class", "SidebarButton")
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self._on_button_clicked(page_id))
        self.layout.addWidget(btn)
        self.buttons[page_id] = btn

    def _on_button_clicked(self, page_id: str):
        self.set_active(page_id)
        self.page_changed.emit(page_id)
        
    def _on_mini_mode_clicked(self):
        win = self.window()
        win.hide()
        if hasattr(win, "taskbar_widget"):
            win.taskbar_widget.hide()
        if hasattr(win, "mini_widget"):
            win.mini_widget.show()
            win.mini_widget.activateWindow()

    def _on_taskbar_mode_clicked(self):
        win = self.window()
        win.hide()
        if hasattr(win, "mini_widget"):
            win.mini_widget.hide()
        if hasattr(win, "taskbar_widget"):
            win.taskbar_widget.show()
            win.taskbar_widget.activateWindow()

    def set_active(self, page_id: str):
        for pid, btn in self.buttons.items():
            btn.setChecked(pid == page_id)
