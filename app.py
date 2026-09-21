import sys
from PySide6.QtWidgets import QApplication
from src.main import main

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main(app)
    sys.exit(app.exec())
