import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QSharedMemory
from src.main import main

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Check for single instance
    shared_mem = QSharedMemory("PCSystemMonitorSharedMemoryKey")
    if not shared_mem.create(1):
        # Memory already exists, so another instance is running
        QMessageBox.warning(None, "Already Running", "PC-System Monitor is already running.")
        sys.exit(0)
        
    main(app)
    sys.exit(app.exec())
