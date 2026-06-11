from __future__ import annotations

import numpy as np
from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from gui.widgets import ImagePreview
from scanner.pipeline import PipelineStages
from utils.image_utils import gray_to_bgr


class PipelineViewer(QWidget):
    TAB_NAMES = (
        "Original",
        "Grayscale",
        "Edge Detection",
        "Morphology",
        "Contour Detection",
        "Perspective Corrected",
        "Final Enhanced Scan",
    )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._viewers: dict[str, ImagePreview] = {}
        for name in self.TAB_NAMES:
            preview = ImagePreview(f"Waiting for {name.lower()}...")
            preview.setStyleSheet(
                "QLabel { background-color: #12151a; color: #6b7280; border: none; border-radius: 6px; }"
            )
            self._viewers[name] = preview
            self._tabs.addTab(preview, name)
        layout.addWidget(self._tabs)

    def update_stages(
        self,
        original: np.ndarray | None,
        stages: PipelineStages | None,
        overlay: np.ndarray | None = None,
        warped: np.ndarray | None = None,
        final: np.ndarray | None = None,
    ) -> None:
        if original is not None:
            self._viewers["Original"].set_image(original)

        if stages is None:
            return

        if stages.grayscale is not None:
            self._viewers["Grayscale"].set_image(gray_to_bgr(stages.grayscale))
        if stages.edges is not None:
            self._viewers["Edge Detection"].set_image(gray_to_bgr(stages.edges))
        if stages.morphology is not None:
            self._viewers["Morphology"].set_image(gray_to_bgr(stages.morphology))

        contour_img = overlay if overlay is not None else stages.contour_overlay
        if contour_img is not None:
            self._viewers["Contour Detection"].set_image(contour_img)

        perspective = warped if warped is not None else stages.warped
        if perspective is not None:
            self._viewers["Perspective Corrected"].set_image(perspective)

        result = final if final is not None else stages.final
        if result is not None:
            self._viewers["Final Enhanced Scan"].set_image(result)
