from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox, QListWidget, QProgressBar, QFrame, QSizePolicy
from PySide6.QtCore import Qt, QTimer
from src.services.analyze_service import AnalyzeService

class AnalyzePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.analyze_service = AnalyzeService()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)
        
        # Header Section
        header_layout = QHBoxLayout()
        
        title_layout = QVBoxLayout()
        header = QLabel("System Analysis")
        header.setStyleSheet("font-size: 32px; font-weight: bold; color: #cdd6f4; letter-spacing: 1px;")
        subtitle = QLabel("Identify bottlenecks and get actionable recommendations")
        subtitle.setStyleSheet("font-size: 14px; color: #a6adc8;")
        title_layout.addWidget(header)
        title_layout.addWidget(subtitle)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        self.btn_analyze = QPushButton("Run Diagnostics")
        self.btn_analyze.setCursor(Qt.PointingHandCursor)
        self.btn_analyze.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa; 
                color: #11111b; 
                padding: 12px 24px; 
                border-radius: 8px; 
                font-weight: bold; 
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #b4befe;
            }
            QPushButton:pressed {
                background-color: #74c7ec;
            }
        """)
        self.btn_analyze.clicked.connect(self._run_analysis)
        header_layout.addWidget(self.btn_analyze, alignment=Qt.AlignVCenter)
        
        layout.addLayout(header_layout)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #313244;")
        layout.addWidget(line)
        
        # Score Section
        score_layout = QVBoxLayout()
        
        score_title = QLabel("Overall Health Score")
        score_title.setStyleSheet("font-size: 18px; color: #bac2de; font-weight: 600;")
        score_layout.addWidget(score_title)
        
        self.score_label = QLabel("0")
        self.score_label.setAlignment(Qt.AlignCenter)
        self.score_label.setStyleSheet("""
            font-size: 72px; 
            font-weight: 900; 
            color: #a6e3a1; 
            margin: 10px 0;
        """)
        score_layout.addWidget(self.score_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 6px;
                background-color: #313244;
            }
            QProgressBar::chunk {
                border-radius: 6px;
                background-color: #a6e3a1;
            }
        """)
        score_layout.addWidget(self.progress_bar)
        
        layout.addLayout(score_layout)
        
        # Results Layout (Bottlenecks & Recommendations)
        results_layout = QHBoxLayout()
        results_layout.setSpacing(20)
        
        # Bottlenecks Card
        bn_card = QFrame()
        bn_card.setStyleSheet("QFrame { background-color: #1e1e2e; border-radius: 12px; border: 1px solid #313244; }")
        bn_layout = QVBoxLayout(bn_card)
        bn_layout.setContentsMargins(20, 20, 20, 20)
        
        bn_title = QLabel("Detected Bottlenecks")
        bn_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f9e2af; border: none;")
        bn_layout.addWidget(bn_title)
        
        self.bottleneck_list = QListWidget()
        self.bottleneck_list.setFocusPolicy(Qt.NoFocus)
        self.bottleneck_list.setStyleSheet("""
            QListWidget {
                background-color: transparent; 
                color: #cdd6f4; 
                border: none;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #313244;
            }
        """)
        bn_layout.addWidget(self.bottleneck_list)
        results_layout.addWidget(bn_card)
        
        # Recommendations Card
        rec_card = QFrame()
        rec_card.setStyleSheet("QFrame { background-color: #1e1e2e; border-radius: 12px; border: 1px solid #313244; }")
        rec_layout = QVBoxLayout(rec_card)
        rec_layout.setContentsMargins(20, 20, 20, 20)
        
        rec_title = QLabel("Actionable Recommendations")
        rec_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #a6e3a1; border: none;")
        rec_layout.addWidget(rec_title)
        
        self.rec_list = QListWidget()
        self.rec_list.setFocusPolicy(Qt.NoFocus)
        self.rec_list.setStyleSheet("""
            QListWidget {
                background-color: transparent; 
                color: #cdd6f4; 
                border: none;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #313244;
            }
        """)
        rec_layout.addWidget(self.rec_list)
        results_layout.addWidget(rec_card)
        
        layout.addLayout(results_layout)
        layout.setStretchFactor(results_layout, 1)
        
        # Initial Run
        QTimer.singleShot(500, self._run_analysis)
        
    def _run_analysis(self):
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.setText("Analyzing...")
        
        result = self.analyze_service.run_analysis()
        
        # Update Score
        score = result["score"]
        self.score_label.setText(str(score))
        self.progress_bar.setValue(score)
        
        # Color coding based on score
        color = "#a6e3a1" # Green
        if score <= 50:
            color = "#f38ba8" # Red
        elif score <= 80:
            color = "#f9e2af" # Yellow
            
        self.score_label.setStyleSheet(f"font-size: 72px; font-weight: 900; color: {color}; margin: 10px 0;")
        self.progress_bar.setStyleSheet(f"QProgressBar {{ border: none; border-radius: 6px; background-color: #313244; }} QProgressBar::chunk {{ border-radius: 6px; background-color: {color}; }}")
            
        # Update Lists
        self.bottleneck_list.clear()
        if result["bottlenecks"]:
            for bn in result["bottlenecks"]:
                self.bottleneck_list.addItem(f"⚠️ {bn}")
        else:
            self.bottleneck_list.addItem("✅ No bottlenecks detected.")
            
        self.rec_list.clear()
        if result["recommendations"]:
            for rec in result["recommendations"]:
                self.rec_list.addItem(f"💡 {rec}")
        else:
            self.rec_list.addItem("🎉 System is running optimally.")
            
        self.btn_analyze.setEnabled(True)
        self.btn_analyze.setText("Run Diagnostics")
