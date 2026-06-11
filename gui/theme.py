DARK_THEME = """
QMainWindow, QWidget {
    background-color: #1a1d23;
    color: #e8eaed;
    font-family: "Segoe UI", "SF Pro Text", "Helvetica Neue", sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #2f3540;
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px 10px 10px 10px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #9aa0a6;
}
QPushButton {
    background-color: #2d6cdf;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton:hover { background-color: #3d7cf0; }
QPushButton:pressed { background-color: #2558b8; }
QPushButton:disabled { background-color: #3a3f4b; color: #7a7f8a; }
QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #2f3540;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #4c8bf5;
    width: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::sub-page:horizontal {
    background: #4c8bf5;
    border-radius: 3px;
}
QComboBox, QSpinBox {
    background-color: #252930;
    border: 1px solid #3a404c;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 20px;
}
QComboBox::drop-down { border: none; width: 24px; }
QTabWidget::pane {
    border: 1px solid #2f3540;
    border-radius: 8px;
    background: #1e2229;
}
QTabBar::tab {
    background: #252930;
    color: #9aa0a6;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background: #2d6cdf;
    color: white;
}
QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #3a404c;
    background: #252930;
}
QCheckBox::indicator:checked {
    background: #2d6cdf;
    border-color: #2d6cdf;
}
QScrollArea { border: none; background: transparent; }
QSplitter::handle { background: #2f3540; width: 3px; }
QLabel#metricsLabel { color: #9aa0a6; font-size: 12px; }
QLabel#statusLabel { padding: 6px 10px; border-radius: 6px; background: #252930; }
"""
