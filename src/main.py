import logging
from PySide6.QtWidgets import QApplication
from src.core.logger import logger
from src.core.config import config
from src.services.monitoring_service import MonitoringService
from src.services.alert_service import AlertService
from src.ui.main_window import MainWindow
from src.ui.system_tray import SystemTray
from src.ui.mini_widget import MiniWidget

def main(app: QApplication):
    logger.info("Starting PC-System Monitor...")
    # Initialize Services
    app.monitoring_service = MonitoringService()
    app.monitoring_service.start()
    
    app.alert_service = AlertService()
    
    # Initialize UI
    app.window = MainWindow()
    app.mini_widget = MiniWidget(app.window)
    app.window.mini_widget = app.mini_widget # give window access to it
    
    from src.ui.taskbar_widget import TaskbarWidget
    app.taskbar_widget = TaskbarWidget(app.window)
    app.window.taskbar_widget = app.taskbar_widget
    
    # Initialize System Tray
    app.setQuitOnLastWindowClosed(False)
    app.window.tray = SystemTray(app.window, app)
    app.window.tray.show()
    
    app.window.show()
    
    # Let the app run, but ensure we stop services on exit
    app.aboutToQuit.connect(app.monitoring_service.stop)
