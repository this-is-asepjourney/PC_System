STYLESHEET = """
QMainWindow {
    background-color: #11111b;
}

QWidget {
    color: #cdd6f4;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

/* Sidebar */
QFrame#Sidebar {
    background-color: #181825;
    border-right: 1px solid #28283d;
}

QPushButton.SidebarButton {
    background-color: transparent;
    color: #a6adc8;
    text-align: left;
    padding: 10px 16px;
    border: 1px solid transparent;
    border-radius: 8px;
    margin: 2px 10px;
    font-weight: 500;
    font-size: 13px;
}

QPushButton.SidebarButton:hover {
    background-color: rgba(255, 255, 255, 0.05);
    color: #cdd6f4;
}

QPushButton.SidebarButton:checked {
    background-color: #89b4fa;
    color: #11111b;
    font-weight: bold;
}

QPushButton.SidebarActionBtn {
    background-color: rgba(49, 50, 68, 0.6);
    color: #cdd6f4;
    text-align: left;
    padding: 9px 14px;
    border: 1px solid #313244;
    border-radius: 8px;
    margin: 3px 10px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton.SidebarActionBtn:hover {
    background-color: #313244;
    border-color: #89b4fa;
    color: #ffffff;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #181825;
    width: 8px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical {
    background: #313244;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #45475a;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

/* Tooltip */
QToolTip {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}
"""
