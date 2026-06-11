from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class AppHeader(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("appHeader")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(2)

        title = QLabel("EDGEVISION")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        subtitle = QLabel("Smart Document Scanner")
        subtitle.setObjectName("appSubtitle")
        layout.addWidget(subtitle)

        tagline = QLabel("Transform photos into clean scans using computer vision.")
        tagline.setObjectName("appTagline")
        layout.addWidget(tagline)
