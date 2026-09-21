import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget
from PySide6.QtCore import QTimer
import numpy as np

class PerformanceChart(QWidget):
    def __init__(self, title: str, max_points: int = 60, parent=None):
        super().__init__(parent)
        self.max_points = max_points
        self.data = np.zeros(max_points)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Configure PlotWidget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1e1e2e')
        self.plot_widget.setTitle(title, color='#cdd6f4', size='12pt')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setYRange(0, 100)
        
        # Hide axes for cleaner look
        self.plot_widget.getAxis('bottom').setStyle(showValues=False)
        self.plot_widget.getAxis('left').setPen('#6c7086')
        self.plot_widget.getAxis('bottom').setPen('#6c7086')
        
        # Create plot line
        pen = pg.mkPen(color='#89b4fa', width=2)
        self.curve = self.plot_widget.plot(self.data, pen=pen, fillLevel=0, brush=(137, 180, 250, 50))
        
        layout.addWidget(self.plot_widget)

    def update_value(self, value: float):
        # Shift data left
        self.data[:-1] = self.data[1:]
        self.data[-1] = value
        self.curve.setData(self.data)
