from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent, QPainter, QPaintEvent, QPixmap, QWheelEvent
from PySide6.QtWidgets import QWidget

from utils.image_utils import numpy_to_qimage_rgb


class ComparisonWidget(QWidget):
    dividerMoved = Signal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._before: QPixmap | None = None
        self._after: QPixmap | None = None
        self._divider = 0.5
        self._dragging = False
        self._scale = 1.0
        self._offset = QPoint(0, 0)
        self._panning = False
        self._pan_start = QPoint()
        self._corners: np.ndarray | None = None
        self._show_overlay = False

        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)
        self.setStyleSheet("background-color: #12151a; border: 1px solid #2f3540; border-radius: 8px;")

    def set_images(
        self,
        before: np.ndarray | None,
        after: np.ndarray | None,
    ) -> None:
        self._before = None
        self._after = None
        if before is not None and before.size > 0:
            self._before = QPixmap.fromImage(numpy_to_qimage_rgb(before))
        if after is not None and after.size > 0:
            self._after = QPixmap.fromImage(numpy_to_qimage_rgb(after))
        self._scale = 1.0
        self._offset = QPoint(0, 0)
        self.update()

    def set_overlay_corners(self, corners: np.ndarray | None, show: bool) -> None:
        self._corners = corners
        self._show_overlay = show
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.fillRect(self.rect(), Qt.black)

        if self._before is None and self._after is None:
            painter.setPen(Qt.gray)
            painter.drawText(self.rect(), Qt.AlignCenter, "Upload an image — drag divider to compare")
            painter.end()
            return

        pix = self._after or self._before
        if pix is None:
            painter.end()
            return

        w = int(pix.width() * self._scale)
        h = int(pix.height() * self._scale)
        x = (self.width() - w) // 2 + self._offset.x()
        y = (self.height() - h) // 2 + self._offset.y()

        if self._before is not None:
            painter.drawPixmap(x, y, w, h, self._before)
        if self._after is not None:
            clip_x = x + int(w * self._divider)
            painter.setClipRect(clip_x, y, w - int(w * self._divider), h)
            painter.drawPixmap(x, y, w, h, self._after)
            painter.setClipping(False)

        line_x = x + int(w * self._divider)
        painter.setPen(Qt.white)
        painter.drawLine(line_x, y, line_x, y + h)
        painter.fillRect(line_x - 2, y + h // 2 - 20, 4, 40, Qt.white)

        if self._show_overlay and self._corners is not None and self._before is not None:
            sx = w / self._before.width()
            sy = h / self._before.height()
            pts = [(x + cx * sx, y + cy * sy) for cx, cy in self._corners]
            painter.setPen(Qt.green)
            for i in range(4):
                p1 = pts[i]
                p2 = pts[(i + 1) % 4]
                painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))
            painter.setBrush(Qt.cyan)
            for px, py in pts:
                painter.drawEllipse(int(px) - 6, int(py) - 6, 12, 12)

        painter.end()

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 1.1 if event.angleDelta().y() > 0 else 1 / 1.1
        self._scale = max(0.2, min(5.0, self._scale * factor))
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            pix = self._after or self._before
            if pix is None:
                return
            w = int(pix.width() * self._scale)
            x0 = (self.width() - w) // 2 + self._offset.x()
            line_x = x0 + int(w * self._divider)
            if abs(event.position().x() - line_x) < 12:
                self._dragging = True
            else:
                self._panning = True
                self._pan_start = event.position().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            pix = self._after or self._before
            if pix is None:
                return
            w = int(pix.width() * self._scale)
            x0 = (self.width() - w) // 2 + self._offset.x()
            rel = (event.position().x() - x0) / max(w, 1)
            self._divider = max(0.02, min(0.98, rel))
            self.dividerMoved.emit(self._divider)
            self.update()
        elif self._panning:
            delta = event.position().toPoint() - self._pan_start
            self._offset += delta
            self._pan_start = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._dragging = False
        self._panning = False

    def reset_view(self) -> None:
        self._scale = 1.0
        self._offset = QPoint(0, 0)
        self._divider = 0.5
        self.update()
