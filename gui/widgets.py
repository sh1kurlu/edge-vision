from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout

from utils.image_utils import numpy_to_qimage_rgb


class ImagePreview(QLabel):
    def __init__(self, placeholder: str = "No image", parent=None) -> None:
        super().__init__(parent)
        self._placeholder = placeholder
        self._pixmap: QPixmap | None = None
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(
            "QLabel { background-color: #2b2b2b; color: #aaaaaa; border: 1px solid #555; }"
        )
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
        self.setWordWrap(True)
        self.setMinimumHeight(28)
        self.set_info("Ready. Upload an image to begin.")

    def set_info(self, message: str) -> None:
        self.setStyleSheet("color: #cccccc;")
        self.setText(message)

    def set_success(self, message: str) -> None:
        self.setStyleSheet("color: #6fcf97;")
        self.setText(message)

    def set_error(self, message: str) -> None:
        self.setStyleSheet("color: #eb5757;")
        self.setText(message)

    def set_progress(self, message: str) -> None:
        self.setStyleSheet("color: #f2c94c;")
        self.setText(message)
