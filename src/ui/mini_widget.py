from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal, QObject, QPoint
from src.core.events import event_bus

class MiniBridge(QObject):
    cpu_updated = Signal(dict)
    memory_updated = Signal(dict)
    network_updated = Signal(dict)

class MiniWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        
        # Window attributes for a widget
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(250, 120)
        
        # We need variables for dragging
        self._drag_pos = QPoint()
        
        # Main layout inside a stylized frame
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.bg_frame = QWidget()
        self.bg_frame.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 46, 230);
                border-radius: 8px;
                border: 1px solid #313244;
                color: #cdd6f4;
                font-family: 'Segoe UI', Arial;
            }
        """)
        layout.addWidget(self.bg_frame)
        
        inner_layout = QVBoxLayout(self.bg_frame)
        inner_layout.setContentsMargins(10, 5, 10, 10)
        inner_layout.setSpacing(5)
        
        # Header (Top bar)
        header_layout = QHBoxLayout()
        title = QLabel("PC-System")
        title.setStyleSheet("font-size: 10px; font-weight: bold; color: #89b4fa; border: none; background: transparent;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Button to restore main window
        restore_btn = QPushButton("⛶")
        restore_btn.setFixedSize(20, 20)
        restore_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #a6adc8;
            }
            QPushButton:hover { color: #cdd6f4; }
        """)
        restore_btn.clicked.connect(self.restore_main)
        header_layout.addWidget(restore_btn)
        
        inner_layout.addLayout(header_layout)
        
        # Metrics labels
        self.lbl_cpu = QLabel("CPU: --")
        self.lbl_ram = QLabel("RAM: --")
        self.lbl_net = QLabel("Net: ↓ -- ↑ --")
        
        for lbl in [self.lbl_cpu, self.lbl_ram, self.lbl_net]:
            lbl.setStyleSheet("font-size: 12px; border: none; background: transparent;")
            inner_layout.addWidget(lbl)
            
        # Bridge setup
        self.bridge = MiniBridge()
        self.bridge.cpu_updated.connect(self.update_cpu)
        self.bridge.memory_updated.connect(self.update_memory)
        self.bridge.network_updated.connect(self.update_network)
        
        event_bus.subscribe("metrics_cpu", self.bridge.cpu_updated.emit)
        event_bus.subscribe("metrics_memory", self.bridge.memory_updated.emit)
        event_bus.subscribe("metrics_network", self.bridge.network_updated.emit)

    def restore_main(self):
        self.hide()
        self.main_window.show()
        self.main_window.activateWindow()

    # Dragging logic
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            
    # Updaters
    def update_cpu(self, data: dict):
        self.lbl_cpu.setText(f"CPU: {data['usage']:.1f}%")
        
    def update_memory(self, data: dict):
        self.lbl_ram.setText(f"RAM: {data['percent']:.1f}%")
        
    def update_network(self, data: dict):
        dl_mb = data['download_speed'] / (1024**2)
        ul_mb = data['upload_speed'] / (1024**2)
        self.lbl_net.setText(f"Net: ↓ {dl_mb:.1f} MB/s  ↑ {ul_mb:.1f} MB/s")
