from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget
from src.ui.theme import STYLESHEET
from src.ui.components.sidebar import Sidebar
from src.ui.pages.dashboard import DashboardPage
from src.ui.pages.processes import ProcessesPage
from src.ui.pages.hardware import HardwarePage
from src.ui.pages.alerts import AlertsPage
from src.ui.pages.settings import SettingsPage
from src.ui.pages.optimizer import OptimizerPage
from src.ui.pages.analyze import AnalyzePage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PC-System Monitor")
        self.resize(1000, 700)
        self.setStyleSheet(STYLESHEET)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self.change_page)
        layout.addWidget(self.sidebar)
        
        # Content Area
        self.content_area = QStackedWidget()
        layout.addWidget(self.content_area, 1) # stretch=1
        
        # Pages
        self.pages = {}
        self._add_page("dashboard", DashboardPage())
        self._add_page("processes", ProcessesPage())
        self._add_page("hardware", HardwarePage())
        self._add_page("alerts", AlertsPage())
        self._add_page("analyze", AnalyzePage())
        self._add_page("optimizer", OptimizerPage())
        self._add_page("settings", SettingsPage())
        
        # Initial page
        self.change_page("dashboard")

    def _add_page(self, page_id: str, widget: QWidget):
        self.content_area.addWidget(widget)
        self.pages[page_id] = widget
        
    def change_page(self, page_id: str):
        if page_id in self.pages:
            self.content_area.setCurrentWidget(self.pages[page_id])
            
    def closeEvent(self, event):
        # Minimize to tray instead of closing
        event.ignore()
        self.hide()
