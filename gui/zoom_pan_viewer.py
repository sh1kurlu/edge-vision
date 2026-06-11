from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QPainter, QPixmap, QWheelEvent
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from utils.image_utils import numpy_to_qimage_rgb


class ZoomPanViewer(QGraphicsView):
    cornersChanged = Signal(object)

    def __init__(self, placeholder: str = "No image", parent=None) -> None:
        super().__init__(parent)
        self._placeholder = placeholder
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._scale_factor = 1.0
        self._panning = False
        self._pan_start = QPointF()
        self._corner_items: list = []
        self._corner_edit_enabled = False
        self._corners: np.ndarray | None = None
        self._drag_index: int | None = None
        self._image_shape: tuple[int, int] | None = None

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("background-color: #12151a; border: 1px solid #2f3540; border-radius: 8px;")
        self.setMinimumSize(280, 200)

        self._placeholder_text = placeholder

    def set_image(self, image: np.ndarray | None) -> None:
        self._scene.clear()
        self._pixmap_item = None
        self._corner_items.clear()
        self._corners = None
        self._image_shape = None
        self.resetTransform()
        self._scale_factor = 1.0

        if image is None or image.size == 0:
            from PySide6.QtWidgets import QGraphicsTextItem
            text = QGraphicsTextItem(self._placeholder_text)
            text.setDefaultTextColor(Qt.gray)
            self._scene.addItem(text)
            return

        qimage = numpy_to_qimage_rgb(image)
        pixmap = QPixmap.fromImage(qimage)
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._image_shape = (image.shape[1], image.shape[0])
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self.fit_in_view()

    def set_corners(self, corners: np.ndarray | None, editable: bool = False) -> None:
        self._corner_edit_enabled = editable
        self._corners = corners.copy() if corners is not None else None
        self._rebuild_corner_handles()

    def _rebuild_corner_handles(self) -> None:
        for item in self._corner_items:
            self._scene.removeItem(item)
        self._corner_items.clear()

        if self._corners is None or self._pixmap_item is None:
            return

        from PySide6.QtWidgets import QGraphicsEllipseItem

        for i, (x, y) in enumerate(self._corners):
            r = 10
            ellipse = QGraphicsEllipseItem(x - r, y - r, r * 2, r * 2)
            ellipse.setBrush(Qt.red if self._corner_edit_enabled else Qt.cyan)
            ellipse.setPen(Qt.white)
            ellipse.setZValue(10)
            ellipse.setFlag(ellipse.GraphicsItemFlag.ItemIsMovable, self._corner_edit_enabled)
            ellipse.setFlag(ellipse.GraphicsItemFlag.ItemSendsGeometryChanges, self._corner_edit_enabled)
            ellipse.setData(0, i)
            self._scene.addItem(ellipse)
            self._corner_items.append(ellipse)

        if len(self._corner_items) == 4:
            from PySide6.QtGui import QPen
            from PySide6.QtWidgets import QGraphicsLineItem

            for i in range(4):
                p1 = self._corners[i]
                p2 = self._corners[(i + 1) % 4]
                line = QGraphicsLineItem(p1[0], p1[1], p2[0], p2[1])
                line.setPen(QPen(Qt.green, 2))
                line.setZValue(5)
                self._scene.addItem(line)
                self._corner_items.append(line)

    def fit_in_view(self) -> None:
        if self._pixmap_item is not None:
            self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)
            self._scale_factor = self.transform().m11()

    def reset_zoom(self) -> None:
        self.resetTransform()
        self._scale_factor = 1.0
        self.fit_in_view()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._pixmap_item is None:
            return
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        new_scale = self._scale_factor * factor
        if 0.1 <= new_scale <= 10.0:
            self.scale(factor, factor)
            self._scale_factor = new_scale

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MiddleButton or (
            event.button() == Qt.LeftButton and not self._corner_edit_enabled
        ):
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                int(self.horizontalScrollBar().value() - delta.x())
            )
            self.verticalScrollBar().setValue(
                int(self.verticalScrollBar().value() - delta.y())
            )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._panning:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
        if self._corner_edit_enabled and self._corners is not None:
            updated = []
            for item in self._corner_items:
                if hasattr(item, "rect"):
                    idx = item.data(0)
                    center = item.rect().center()
                    updated.append((idx, center.x(), center.y()))
            if len(updated) == 4:
                updated.sort(key=lambda t: t[0])
                self._corners = np.array([[x, y] for _, x, y in updated], dtype=np.float32)
                self.cornersChanged.emit(self._corners.copy())
        super().mouseReleaseEvent(event)


class ZoomPanWidget(QWidget):
    def __init__(self, title: str = "", parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if title:
            from PySide6.QtWidgets import QLabel
            lbl = QLabel(title)
            lbl.setStyleSheet("font-weight: 600; color: #9aa0a6;")
            layout.addWidget(lbl)
        self.viewer = ZoomPanViewer()
        layout.addWidget(self.viewer)
