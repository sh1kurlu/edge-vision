from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class AppHeader(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("appHeader")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 12)
        layout.setSpacing(2)

        title = QLabel("EDGEVISION")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        tagline = QLabel("Transform photos into clean scans.")
        tagline.setObjectName("appTagline")
        layout.addWidget(tagline)
