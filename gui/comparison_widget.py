from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QMouseEvent, QPainter, QPaintEvent, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from utils.image_utils import numpy_to_qimage_rgb


class ComparisonWidget(QWidget):
    dividerMoved = Signal(float)

    HANDLE_WIDTH = 3
    HANDLE_GRIP = 18

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("comparisonWidget")
        self._before: QPixmap | None = None
        self._after: QPixmap | None = None
        self._divider = 0.5
        self._dragging = False
        self._handle_hover = False

        self.setMinimumSize(480, 360)
        self.setMouseTracking(True)

    def set_images(self, before, after) -> None:
        import numpy as np

        self._before = None
        self._after = None
        if before is not None and isinstance(before, np.ndarray) and before.size > 0:
            self._before = QPixmap.fromImage(numpy_to_qimage_rgb(before))
        if after is not None and isinstance(after, np.ndarray) and after.size > 0:
            self._after = QPixmap.fromImage(numpy_to_qimage_rgb(after))
        self._divider = 0.5
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
        return x + int(w * self._divider)

    def _near_handle(self, pos_x: float) -> bool:
        line_x = self._line_x()
        return line_x is not None and abs(pos_x - line_x) <= self.HANDLE_GRIP

    def _draw_label(self, painter: QPainter, text: str, x: int, y: int) -> None:
        metrics = painter.fontMetrics()
        pad_x, pad_y = 8, 4
        w = metrics.horizontalAdvance(text) + pad_x * 2
        h = metrics.height() + pad_y
        painter.fillRect(x, y, w, h, QColor(0, 0, 0, 140))
        painter.setPen(QColor("#e0e0e0"))
        painter.drawText(x + pad_x, y + metrics.ascent() + pad_y // 2, text)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor("#181818"))

        if self._before is None and self._after is None:
            painter.setPen(QColor("#6e6e6e"))
            font = QFont()
            font.setPointSize(11)
            painter.setFont(font)
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                "Comparison will appear here after scanning.\n"
                "Drag the divider to compare rectified and enhanced results.",
            )
            painter.end()
            return

        rect = self._image_rect()
        if rect is None:
            painter.end()
            return

        x, y, w, h = rect
        line_x = x + int(w * self._divider)

        if self._before is not None:
            painter.drawPixmap(x, y, w, h, self._before)
        if self._after is not None:
            painter.setClipRect(line_x, y, x + w - line_x, h)
            painter.drawPixmap(x, y, w, h, self._after)
            painter.setClipping(False)

        line_color = QColor("#ffffff") if self._handle_hover or self._dragging else QColor("#858585")
        painter.setPen(QPen(line_color, self.HANDLE_WIDTH))
        painter.drawLine(line_x, y, line_x, y + h)

        handle_y = y + h // 2
        grip_h = 36
        grip_w = 8
        grip_color = QColor("#cccccc") if self._handle_hover or self._dragging else QColor("#6e6e6e")
        painter.setBrush(QBrush(grip_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(
            line_x - grip_w // 2,
            handle_y - grip_h // 2,
            grip_w,
            grip_h,
            2,
            2,
        )

        label_font = QFont()
        label_font.setPointSize(9)
        label_font.setWeight(QFont.DemiBold)
        painter.setFont(label_font)
        self._draw_label(painter, "Rectified", x + 10, y + 10)
        self._draw_label(painter, "Enhanced", x + w - 90, y + 10)

        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._near_handle(event.position().x()):
            self._dragging = True
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
            self.dividerMoved.emit(self._divider)
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self._dragging = False
            self.update()
        self.setCursor(Qt.SplitHCursor if self._handle_hover else Qt.ArrowCursor)

    def reset_view(self) -> None:
        self._divider = 0.5
        self.update()

    def leaveEvent(self, event) -> None:
        self._handle_hover = False
        self.setCursor(Qt.ArrowCursor)
        self.update()
        super().leaveEvent(event)
