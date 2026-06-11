DARK_THEME = """
QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #cccccc;
    font-family: "Segoe UI", "Helvetica Neue", "Arial", sans-serif;
    font-size: 13px;
}

QWidget#appHeader {
    background-color: transparent;
    border-bottom: 1px solid #333333;
    padding-bottom: 4px;
}
QLabel#appTitle {
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 2px;
    color: #ffffff;
}
QLabel#appSubtitle {
    font-size: 13px;
    font-weight: 600;
    color: #e0e0e0;
}
QLabel#appTagline {
    font-size: 12px;
    color: #858585;
    padding-top: 2px;
}
QLabel#sectionTitle {
    font-size: 11px;
    font-weight: 600;
    color: #858585;
    letter-spacing: 0.5px;
    padding: 0 2px 6px 2px;
}
QLabel#workspaceHint {
    font-size: 12px;
    color: #858585;
}

QWidget#sidebarPanel {
    background-color: #252526;
    border-right: 1px solid #333333;
}
QWidget#statusBar {
    background-color: #252526;
    border-top: 1px solid #333333;
}
QLabel#statusLabel {
    color: #cccccc;
    font-size: 12px;
    padding: 0 4px;
}
QLabel#statusLabel[state="ready"] { color: #858585; }
QLabel#statusLabel[state="info"] { color: #cccccc; }
QLabel#statusLabel[state="progress"] { color: #dcdcaa; }
QLabel#statusLabel[state="success"] { color: #4ec9b0; }
QLabel#statusLabel[state="error"] { color: #f48771; }

QGroupBox {
    border: 1px solid #333333;
    border-radius: 4px;
    margin-top: 16px;
    padding: 12px 10px 10px 10px;
    font-size: 11px;
    font-weight: 600;
    color: #858585;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #858585;
}

QPushButton {
    background-color: #0e639c;
    color: #ffffff;
    border: 1px solid #1177bb;
    border-radius: 4px;
    padding: 8px 14px;
    font-weight: 600;
    font-size: 13px;
    min-height: 20px;
}
QPushButton:hover { background-color: #1177bb; }
QPushButton:pressed { background-color: #0d5689; }
QPushButton:disabled {
    background-color: #2d2d2d;
    border-color: #3c3c3c;
    color: #6e6e6e;
}
QPushButton#primaryButton {
    background-color: #0e639c;
    border-color: #1177bb;
    padding: 10px 16px;
    font-size: 14px;
}
QPushButton#primaryButton:hover { background-color: #1177bb; }
QPushButton#secondaryButton {
    background-color: #2d2d2d;
    border: 1px solid #3c3c3c;
    color: #cccccc;
    font-weight: 500;
}
QPushButton#secondaryButton:hover {
    background-color: #383838;
    border-color: #4a4a4a;
}
QPushButton#textButton {
    background-color: transparent;
    border: none;
    color: #858585;
    font-weight: 500;
    padding: 4px 8px;
}
QPushButton#textButton:hover {
    color: #cccccc;
    background-color: #2a2d2e;
}

QSlider::groove:horizontal {
    border: none;
    height: 4px;
    background: #3c3c3c;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #cccccc;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
    border: 1px solid #1e1e1e;
}
QSlider::handle:horizontal:hover { background: #ffffff; }
QSlider::sub-page:horizontal {
    background: #0e639c;
    border-radius: 2px;
}

QComboBox {
    background-color: #2d2d2d;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    padding: 6px 10px;
    min-height: 22px;
    color: #cccccc;
}
QComboBox:hover { border-color: #4a4a4a; }
QComboBox::drop-down {
    border: none;
    width: 22px;
}
QComboBox QAbstractItemView {
    background-color: #252526;
    border: 1px solid #3c3c3c;
    selection-background-color: #094771;
}

QTabWidget::pane {
    border: 1px solid #333333;
    border-radius: 0;
    background: #1e1e1e;
    top: -1px;
}
QTabWidget#workspaceTabs::pane {
    border: none;
    background: #1e1e1e;
}
QTabBar::tab {
    background: transparent;
    color: #858585;
    padding: 8px 16px;
    margin-right: 0;
    border-bottom: 2px solid transparent;
    font-size: 12px;
    font-weight: 500;
}
QTabBar::tab:selected {
    color: #ffffff;
    border-bottom: 2px solid #0e639c;
    background: transparent;
}
QTabBar::tab:hover:!selected {
    color: #cccccc;
    background: #2a2d2e;
}
QTabWidget#pipelineTabs QTabBar::tab {
    padding: 6px 12px;
    font-size: 11px;
}
QTabWidget#pipelineTabs::pane {
    border: 1px solid #333333;
    border-top: none;
}

QCheckBox {
    spacing: 8px;
    color: #cccccc;
    font-size: 12px;
    padding: 2px 0;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #3c3c3c;
    background: #2d2d2d;
}
QCheckBox::indicator:checked {
    background: #0e639c;
    border-color: #0e639c;
}
QCheckBox::indicator:hover {
    border-color: #4a4a4a;
}

QScrollArea { border: none; background: transparent; }
QScrollArea#sidebarScroll { background: #252526; }
QSplitter::handle { background: #333333; width: 1px; }

QLabel#sliderLabel {
    font-size: 12px;
    color: #cccccc;
}
QLabel#sliderValue {
    font-size: 12px;
    color: #858585;
}
QLabel#fieldLabel {
    font-size: 12px;
    color: #cccccc;
}

QWidget#comparisonWidget {
    background-color: #181818;
    border: 1px solid #333333;
}
QWidget#emptyWorkspace {
    background-color: #181818;
    border: 1px solid #333333;
}
QLabel#imagePreview {
    background-color: #181818;
    color: #6e6e6e;
    border: none;
}
"""
