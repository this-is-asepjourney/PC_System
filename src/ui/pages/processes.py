from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QHBoxLayout, QPushButton, QLineEdit
from PySide6.QtCore import Qt, Signal, QObject
from src.core.events import event_bus
import psutil

class ProcessBridge(QObject):
    process_updated = Signal(dict)

class ProcessesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Processes")
        header.setStyleSheet("font-size: 28px; font-weight: bold; color: #cdd6f4;")
        layout.addWidget(header)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search processes...")
        self.search_bar.setStyleSheet("padding: 8px; border-radius: 4px; background-color: #313244; color: #cdd6f4;")
        toolbar.addWidget(self.search_bar)
        
        kill_btn = QPushButton("Kill Process")
        kill_btn.setStyleSheet("background-color: #f38ba8; color: #11111b; padding: 8px 16px; border-radius: 4px; font-weight: bold;")
        kill_btn.clicked.connect(self._kill_selected)
        toolbar.addWidget(kill_btn)
        
        layout.addLayout(toolbar)
        
        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["PID", "Name", "CPU (%)", "Memory"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                gridline-color: #313244;
                border: 1px solid #313244;
            }
            QHeaderView::section {
                background-color: #313244;
                color: #a6adc8;
                padding: 5px;
                border: 1px solid #1e1e2e;
            }
        """)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)
        
        # Bridge setup
        self.bridge = ProcessBridge()
        self.bridge.process_updated.connect(self.update_table)
        event_bus.subscribe("metrics_process", self.bridge.process_updated.emit)
        
    def update_table(self, data: dict):
        # In a real app we'd smartly update existing rows. For now, clear and rebuild if simple enough.
        # To avoid losing selection, we remember it.
        processes = data.get("processes", [])
        
        # Filter if search
        search_term = self.search_bar.text().lower()
        if search_term:
            processes = [p for p in processes if search_term in p['name'].lower() or search_term in str(p['pid'])]
            
        self.table.setRowCount(len(processes))
        for row, proc in enumerate(processes):
            pid_item = QTableWidgetItem(str(proc['pid']))
            name_item = QTableWidgetItem(proc['name'])
            cpu_item = QTableWidgetItem(f"{proc['cpu']:.1f}")
            mem_item = QTableWidgetItem(f"{proc['memory'] / (1024**2):.1f} MB")
            
            # Read-only
            for item in [pid_item, name_item, cpu_item, mem_item]:
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                
            self.table.setItem(row, 0, pid_item)
            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, cpu_item)
            self.table.setItem(row, 3, mem_item)
            
    def _kill_selected(self):
        selected = self.table.selectedItems()
        if selected:
            pid = int(self.table.item(selected[0].row(), 0).text())
            try:
                p = psutil.Process(pid)
                p.terminate()
            except Exception as e:
                print(f"Failed to kill {pid}: {e}")
