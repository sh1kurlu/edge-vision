DARK_THEME = """
QMainWindow, QWidget {
    background-color: #1a1d23;
    color: #e8eaed;
    font-family: "Helvetica Neue", "Arial", sans-serif;
    font-size: 13px;
}
QWidget#appHeader {
    background-color: transparent;
}
QLabel#appTitle {
    font-size: 26px;
    font-weight: 800;
    letter-spacing: 4px;
    color: #ffffff;
}
QLabel#appTagline {
    font-size: 13px;
    color: #8b93a1;
    padding-bottom: 4px;
}
QLabel#sectionTitle {
    font-size: 14px;
    font-weight: 600;
    color: #c8cdd5;
    padding-left: 2px;
}
QGroupBox {
    border: 1px solid #2f3540;
    border-radius: 8px;
    margin-top: 14px;
    padding: 14px 12px 12px 12px;
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
    padding: 9px 16px;
    font-weight: 600;
}
QPushButton#secondaryButton {
    background-color: #2a2f38;
    border: 1px solid #3a404c;
}
QPushButton#secondaryButton:hover {
    background-color: #343a45;
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
    top: -1px;
}
QTabBar::tab {
    background: #252930;
    color: #9aa0a6;
    padding: 9px 18px;
    margin-right: 3px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background: #2d6cdf;
    color: white;
}
QCheckBox { spacing: 8px; color: #d0d4db; }
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
QSplitter::handle { background: #2f3540; width: 4px; }
QLabel#metricsLabel { color: #9aa0a6; font-size: 12px; line-height: 1.4; }
QLabel#statusLabel { padding: 8px 10px; border-radius: 6px; background: #252930; }
"""
