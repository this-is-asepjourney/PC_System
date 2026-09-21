from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit, QGroupBox, QGridLayout
from PySide6.QtCore import Qt, QTimer
from src.services.optimizer_service import OptimizerService
from src.services.verify_service import VerifyService

class OptimizerPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.optimizer_service = OptimizerService()
        self.verify_service = VerifyService()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("System Optimizer")
        header.setStyleSheet("font-size: 28px; font-weight: bold; color: #cdd6f4;")
        layout.addWidget(header)
        
        # Description
        desc = QLabel("Optimize your system performance by freeing up RAM, closing heavy background processes, cleaning junk, and adjusting power plans.")
        desc.setStyleSheet("color: #a6adc8; font-size: 14px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Controls Group
        controls_group = QGroupBox("Optimization Controls")
        controls_group.setStyleSheet("QGroupBox { color: #89b4fa; font-weight: bold; border: 1px solid #313244; border-radius: 4px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }")
        
        controls_layout = QGridLayout(controls_group)
        controls_layout.setSpacing(10)
        
        self.btn_free_ram = QPushButton("Free Memory")
        self.btn_free_ram.setStyleSheet("background-color: #a6e3a1; color: #11111b; padding: 12px; border-radius: 6px; font-weight: bold; font-size: 14px;")
        self.btn_free_ram.clicked.connect(self._on_free_ram_clicked)
        
        self.btn_kill_heavy = QPushButton("Kill Heavy Processes")
        self.btn_kill_heavy.setStyleSheet("background-color: #f38ba8; color: #11111b; padding: 12px; border-radius: 6px; font-weight: bold; font-size: 14px;")
        self.btn_kill_heavy.clicked.connect(self._on_kill_heavy_clicked)
        
        self.btn_cleanup = QPushButton("Clean Temp Files")
        self.btn_cleanup.setStyleSheet("background-color: #fab387; color: #11111b; padding: 12px; border-radius: 6px; font-weight: bold; font-size: 14px;")
        self.btn_cleanup.clicked.connect(self._on_cleanup_clicked)
        
        self.btn_power_high = QPushButton("High Performance Power")
        self.btn_power_high.setStyleSheet("background-color: #cba6f7; color: #11111b; padding: 12px; border-radius: 6px; font-weight: bold; font-size: 14px;")
        self.btn_power_high.clicked.connect(lambda: self._on_power_clicked(True))
        
        self.btn_power_balanced = QPushButton("Balanced Power")
        self.btn_power_balanced.setStyleSheet("background-color: #89b4fa; color: #11111b; padding: 12px; border-radius: 6px; font-weight: bold; font-size: 14px;")
        self.btn_power_balanced.clicked.connect(lambda: self._on_power_clicked(False))
        
        controls_layout.addWidget(self.btn_free_ram, 0, 0)
        controls_layout.addWidget(self.btn_kill_heavy, 0, 1)
        controls_layout.addWidget(self.btn_cleanup, 1, 0)
        controls_layout.addWidget(self.btn_power_high, 1, 1)
        controls_layout.addWidget(self.btn_power_balanced, 2, 0, 1, 2)
        
        layout.addWidget(controls_group)
        
        # Log Area
        log_label = QLabel("Optimization Log & Verification:")
        log_label.setStyleSheet("color: #cdd6f4; font-weight: bold;")
        layout.addWidget(log_label)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #1e1e2e; color: #a6adc8; border: 1px solid #313244; padding: 10px; font-family: monospace;")
        layout.addWidget(self.log_area)
        
    def _log_message(self, msg: str):
        self.log_area.append(msg)
        
    def _execute_with_verify(self, action_func, action_name):
        self._log_message(f"Starting {action_name}...")
        self.verify_service.start_verification()
        
        action_func()
        
        # Verify after a short delay to let metrics settle
        QTimer.singleShot(1500, self._verify_results)
        
    def _verify_results(self):
        self._log_message("--- Post-Optimization Verification ---")
        result = self.verify_service.complete_verification()
        if result["success"]:
            for r in result["results"]:
                self._log_message(f"  ✓ {r}")
        self._log_message("=" * 40)
        
    def _on_free_ram_clicked(self):
        def _action():
            self.btn_free_ram.setEnabled(False)
            result = self.optimizer_service.free_memory()
            if result["success"]:
                freed_mb = result["freed_bytes"] / (1024**2)
                self._log_message(f"Success: {result['message']}")
                self._log_message(f"Freed approximately {freed_mb:.2f} MB of RAM.")
            else:
                self._log_message(f"Error: {result['message']}")
            self.btn_free_ram.setEnabled(True)
            
        self._execute_with_verify(_action, "memory optimization")
        
    def _on_kill_heavy_clicked(self):
        def _action():
            self.btn_kill_heavy.setEnabled(False)
            result = self.optimizer_service.kill_heavy_processes()
            if result["success"]:
                self._log_message(result["message"])
                for proc in result["killed_processes"]:
                    self._log_message(f"  - Killed {proc['name']} (PID: {proc['pid']})")
            else:
                self._log_message(f"Error: {result['message']}")
            self.btn_kill_heavy.setEnabled(True)
            
        self._execute_with_verify(_action, "heavy process termination")
        
    def _on_cleanup_clicked(self):
        def _action():
            self.btn_cleanup.setEnabled(False)
            result = self.optimizer_service.cleanup_temp_files()
            if result["success"]:
                self._log_message(f"Cleanup: {result['message']}")
                self._log_message(f"Freed {result['freed_bytes'] / (1024**2):.2f} MB of disk space.")
            else:
                self._log_message(f"Error: {result['message']}")
            self.btn_cleanup.setEnabled(True)
            
        self._execute_with_verify(_action, "temp file cleanup")
        
    def _on_power_clicked(self, high_performance: bool):
        def _action():
            result = self.optimizer_service.set_power_plan(high_performance)
            if result["success"]:
                self._log_message(f"Power: {result['message']}")
            else:
                self._log_message(f"Power Error: {result['message']}")
                
        self._execute_with_verify(_action, "power plan adjustment")
