from __future__ import annotations

import numpy as np
from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from gui.zoom_pan_viewer import ZoomPanViewer
from scanner.pipeline import PipelineStages
from utils.image_utils import gray_to_bgr


class PipelineViewer(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._viewers: dict[str, ZoomPanViewer] = {}
        for name in ("Original", "Grayscale", "Edges", "Morphology", "Detected Contour", "Final Scan"):
            viewer = ZoomPanViewer(f"No {name.lower()} yet")
            self._viewers[name] = viewer
            self._tabs.addTab(viewer, name)
        layout.addWidget(self._tabs)

    def update_stages(
        self,
        original: np.ndarray | None,
        stages: PipelineStages | None,
        overlay: np.ndarray | None = None,
        final: np.ndarray | None = None,
    ) -> None:
        if original is not None:
            self._viewers["Original"].set_image(original)

        if stages is None:
            return

        if stages.grayscale is not None:
            self._viewers["Grayscale"].set_image(gray_to_bgr(stages.grayscale))
        if stages.edges is not None:
            self._viewers["Edges"].set_image(gray_to_bgr(stages.edges))
        if stages.morphology is not None:
            self._viewers["Morphology"].set_image(gray_to_bgr(stages.morphology))

        contour_img = overlay if overlay is not None else stages.contour_overlay
        if contour_img is not None:
            self._viewers["Detected Contour"].set_image(contour_img)

        result = final if final is not None else stages.final
        if result is not None:
            self._viewers["Final Scan"].set_image(result)
