from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QObject, Signal
from src.core.events import event_bus

class SystemTrayBridge(QObject):
    cpu_updated = Signal(dict)

class SystemTray(QSystemTrayIcon):
    def __init__(self, main_window, app):
        super().__init__()
        self.main_window = main_window
        self.app = app
        
        # We need an icon for the tray. We'll use a default fallback if none exists.
        # For this prototype, we can use a built-in icon or just let it be blank.
        # It's better to set a standard Qt Icon.
        self.setIcon(main_window.style().standardIcon(main_window.style().StandardPixmap.SP_ComputerIcon))
        self.setToolTip("PC-System Monitor")
        
        # Menu
        self.menu = QMenu()
        
        self.show_action = QAction("Open Dashboard")
        self.show_action.triggered.connect(self.show_window)
        self.menu.addAction(self.show_action)
        
        self.mini_action = QAction("Open Mini Widget")
        self.mini_action.triggered.connect(self.show_mini)
        self.menu.addAction(self.mini_action)
        
        self.taskbar_action = QAction("Open Taskbar Mode")
        self.taskbar_action.triggered.connect(self.show_taskbar)
        self.menu.addAction(self.taskbar_action)
        
        self.menu.addSeparator()
        
        self.quit_action = QAction("Exit")
        self.quit_action.triggered.connect(self.quit_app)
        self.menu.addAction(self.quit_action)
        
        self.setContextMenu(self.menu)
        self.activated.connect(self.on_tray_activated)
        
        # Bridge for tooltip
        self.bridge = SystemTrayBridge()
        self.bridge.cpu_updated.connect(self.update_tooltip)
        event_bus.subscribe("metrics_cpu", self.bridge.cpu_updated.emit)
        
    def show_window(self):
        if hasattr(self.main_window, "mini_widget"):
            self.main_window.mini_widget.hide()
        if hasattr(self.main_window, "taskbar_widget"):
            self.main_window.taskbar_widget.hide()
        self.main_window.show()
        self.main_window.activateWindow()
        
    def show_mini(self):
        self.main_window.hide()
        if hasattr(self.main_window, "taskbar_widget"):
            self.main_window.taskbar_widget.hide()
        if hasattr(self.main_window, "mini_widget"):
            self.main_window.mini_widget.show()
            self.main_window.mini_widget.activateWindow()

    def show_taskbar(self):
        self.main_window.hide()
        if hasattr(self.main_window, "mini_widget"):
            self.main_window.mini_widget.hide()
        if hasattr(self.main_window, "taskbar_widget"):
            self.main_window.taskbar_widget.show()
            self.main_window.taskbar_widget.activateWindow()
        
    def quit_app(self):
        self.app.quit()
        
    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show_window()

    def update_tooltip(self, data: dict):
        self.setToolTip(f"PC-System Monitor\nCPU: {data['usage']:.1f}%")
