from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPoint, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QMouseEvent, QPainter, QPaintEvent, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from utils.image_utils import numpy_to_qimage_rgb


class ComparisonWidget(QWidget):
    dividerMoved = Signal(float)

    HANDLE_RADIUS = 22
    HANDLE_HIT = 28

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._before: QPixmap | None = None
        self._after: QPixmap | None = None
        self._divider = 0.5
        self._divider_display = 0.5
        self._dragging = False
        self._handle_hover = False
        self._anim = QPropertyAnimation(self, b"dividerDisplay", self)
        self._anim.setDuration(120)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)
        self.setStyleSheet("background-color: #12151a; border: 1px solid #2f3540; border-radius: 8px;")

    def getDividerDisplay(self) -> float:
        return self._divider_display

    def setDividerDisplay(self, value: float) -> None:
        self._divider_display = value
        self.update()

    dividerDisplay = Property(float, getDividerDisplay, setDividerDisplay)

    def set_images(self, before, after) -> None:
        import numpy as np

        self._before = None
        self._after = None
        if before is not None and isinstance(before, np.ndarray) and before.size > 0:
            self._before = QPixmap.fromImage(numpy_to_qimage_rgb(before))
        if after is not None and isinstance(after, np.ndarray) and after.size > 0:
            self._after = QPixmap.fromImage(numpy_to_qimage_rgb(after))
        self._divider = 0.5
        self._divider_display = 0.5
        self.update()

    def _image_rect(self) -> tuple[int, int, int, int] | None:
        pix = self._after or self._before
        if pix is None:
            return None
        w, h = pix.width(), pix.height()
        x = (self.width() - w) // 2
        y = (self.height() - h) // 2
        return x, y, w, h

    def _line_x(self) -> int | None:
        rect = self._image_rect()
        if rect is None:
            return None
        x, _, w, _ = rect
        return x + int(w * self._divider_display)

    def _near_handle(self, pos_x: float) -> bool:
        line_x = self._line_x()
        return line_x is not None and abs(pos_x - line_x) <= self.HANDLE_HIT

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor("#0d0f13"))

        if self._before is None and self._after is None:
            painter.setPen(QColor("#6b7280"))
            font = QFont()
            font.setPointSize(11)
            painter.setFont(font)
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                "Upload an image\n\nDrag the handle to compare rectified vs enhanced",
            )
            painter.end()
            return

        rect = self._image_rect()
        if rect is None:
            painter.end()
            return

        x, y, w, h = rect
        line_x = x + int(w * self._divider_display)

        if self._before is not None:
            painter.drawPixmap(x, y, w, h, self._before)
        if self._after is not None:
            painter.setClipRect(line_x, y, x + w - line_x, h)
            painter.drawPixmap(x, y, w, h, self._after)
            painter.setClipping(False)

        painter.setPen(QPen(QColor("#ffffff"), 3))
        painter.drawLine(line_x, y, line_x, y + h)

        handle_y = y + h // 2
        handle_color = QColor("#4c8bf5") if self._handle_hover or self._dragging else QColor("#2d6cdf")
        painter.setBrush(QBrush(handle_color))
        painter.setPen(QPen(Qt.white, 2))
        painter.drawEllipse(QPoint(line_x, handle_y), self.HANDLE_RADIUS, self.HANDLE_RADIUS)

        arrow_pen = QPen(Qt.white, 2)
        painter.setPen(arrow_pen)
        painter.drawLine(line_x - 10, handle_y, line_x - 4, handle_y)
        painter.drawLine(line_x - 6, handle_y - 4, line_x - 4, handle_y)
        painter.drawLine(line_x - 6, handle_y + 4, line_x - 4, handle_y)
        painter.drawLine(line_x + 10, handle_y, line_x + 4, handle_y)
        painter.drawLine(line_x + 6, handle_y - 4, line_x + 4, handle_y)
        painter.drawLine(line_x + 6, handle_y + 4, line_x + 4, handle_y)

        label_font = QFont()
        label_font.setPointSize(9)
        label_font.setBold(True)
        painter.setFont(label_font)
        painter.setPen(QColor("#c8cdd5"))
        painter.drawText(x + 8, y + 20, "Rectified")
        painter.drawText(x + w - 72, y + 20, "Enhanced")

        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._near_handle(event.position().x()):
            self._dragging = True
            self._anim.stop()
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        hover = self._near_handle(event.position().x())
        if hover != self._handle_hover:
            self._handle_hover = hover
            self.setCursor(Qt.SplitHCursor if hover or self._dragging else Qt.ArrowCursor)
            if not self._dragging:
                self.update()

        if self._dragging:
            rect = self._image_rect()
            if rect is None:
                return
            x, _, w, _ = rect
            rel = (event.position().x() - x) / max(w, 1)
            self._divider = max(0.02, min(0.98, rel))
            self._divider_display = self._divider
            self.dividerMoved.emit(self._divider)
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self._dragging = False
            self._animate_to(self._divider)
        self.setCursor(Qt.SplitHCursor if self._handle_hover else Qt.ArrowCursor)

    def _animate_to(self, target: float) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._divider_display)
        self._anim.setEndValue(target)
        self._anim.start()

    def reset_view(self) -> None:
        self._divider = 0.5
        self._animate_to(0.5)

    def leaveEvent(self, event) -> None:
        self._handle_hover = False
        self.setCursor(Qt.ArrowCursor)
        self.update()
        super().leaveEvent(event)
