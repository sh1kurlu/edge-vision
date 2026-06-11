from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from utils.image_utils import numpy_to_qimage_rgb


class ImagePreview(QLabel):
    def __init__(self, placeholder: str = "No image", parent=None) -> None:
        super().__init__(parent)
        self._placeholder = placeholder
        self._pixmap: QPixmap | None = None
        self.setObjectName("imagePreview")
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(280, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._show_placeholder()

    def _show_placeholder(self) -> None:
        self.setText(self._placeholder)
        self._pixmap = None

    def set_image(self, image: np.ndarray | None) -> None:
        if image is None or image.size == 0:
            self._show_placeholder()
            return

        qimage = numpy_to_qimage_rgb(image)
        self._pixmap = QPixmap.fromImage(qimage)
        self._update_scaled_pixmap()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_scaled_pixmap()

    def _update_scaled_pixmap(self) -> None:
        if self._pixmap is None or self._pixmap.isNull():
            return
        scaled = self._pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.setPixmap(scaled)
        self.setText("")


class StatusBarLabel(QLabel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statusLabel")
        self.setWordWrap(False)
        self.set_ready("Ready")

    def _set_state(self, state: str, message: str) -> None:
        self.setProperty("state", state)
        self.setText(message)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_ready(self, message: str = "Ready") -> None:
        self._set_state("ready", message)

    def set_info(self, message: str) -> None:
        self._set_state("info", message)

    def set_success(self, message: str) -> None:
        self._set_state("success", message)

    def set_error(self, message: str) -> None:
        self._set_state("error", message)

    def set_progress(self, message: str) -> None:
        self._set_state("progress", message)


class EmptyWorkspace(QWidget):
    upload_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("emptyWorkspace")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        title = QLabel("No document loaded")
        title.setObjectName("sectionTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        hint = QLabel(
            "Upload a photo of a document to detect edges,\n"
            "correct perspective, and enhance the scan."
        )
        hint.setObjectName("workspaceHint")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        self.upload_btn = QPushButton("Upload Image")
        self.upload_btn.setObjectName("primaryButton")
        self.upload_btn.setMinimumWidth(180)
        self.upload_btn.clicked.connect(self.upload_requested.emit)
        layout.addWidget(self.upload_btn, alignment=Qt.AlignCenter)

        formats = QLabel("Supports JPG, PNG, BMP")
        formats.setObjectName("workspaceHint")
        formats.setAlignment(Qt.AlignCenter)
        layout.addWidget(formats)
