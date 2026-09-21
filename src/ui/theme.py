STYLESHEET = """
QMainWindow {
    background-color: #1e1e2e;
}

QWidget {
    color: #cdd6f4;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 14px;
}

QFrame#MetricCard {
    background-color: #313244;
    border-radius: 8px;
    padding: 10px;
}

QLabel#MetricTitle {
    color: #a6adc8;
    font-size: 12px;
    font-weight: bold;
    text-transform: uppercase;
}

QLabel#MetricValue {
    color: #cdd6f4;
    font-size: 24px;
    font-weight: bold;
}

QLabel#MetricSubValue {
    color: #a6adc8;
    font-size: 12px;
}

/* Sidebar */
QFrame#Sidebar {
    background-color: #181825;
    border-right: 1px solid #313244;
}

QPushButton.SidebarButton {
    background-color: transparent;
    color: #a6adc8;
    text-align: left;
    padding: 12px 20px;
    border: none;
    border-radius: 4px;
    margin: 2px 10px;
}

QPushButton.SidebarButton:hover {
    background-color: #313244;
    color: #cdd6f4;
}

QPushButton.SidebarButton:checked {
    background-color: #89b4fa;
    color: #11111b;
    font-weight: bold;
}
"""
