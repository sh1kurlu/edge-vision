from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gui.comparison_widget import ComparisonWidget
from gui.labeled_slider import LabeledSlider
from gui.pipeline_viewer import PipelineViewer
from gui.theme import DARK_THEME
from gui.widgets import StatusBarLabel
from gui.zoom_pan_viewer import ZoomPanViewer
from scanner.enhancement import EnhancementMode
from scanner.pipeline import DocumentScanner, ScanConfig, ScanResult
from scanner.preprocessing import PreprocessOptions
from utils.image_utils import is_supported_format, load_image, resize_for_preview, save_image
from utils.pdf_export import save_as_pdf

DEBOUNCE_MS = 400


class ScanWorker(QObject):
    finished = Signal(object)
    stage_changed = Signal(str)

    def __init__(
        self,
        scanner: DocumentScanner,
        image: np.ndarray,
        config: ScanConfig,
        preview_corners: np.ndarray | None = None,
    ) -> None:
        super().__init__()
        self._scanner = scanner
        self._image = image
        self._config = config
        self._preview_corners = preview_corners

    @Slot()
    def run(self) -> None:
        def on_stage(msg: str) -> None:
            self.stage_changed.emit(msg)

        self._scanner.config = self._config
        result = self._scanner.scan(
            self._image,
            manual_corners=self._preview_corners,
            status_callback=on_stage,
            use_cache=True,
        )
        self.finished.emit(result)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Document Scanner Pro")
        self.resize(1400, 860)
        self.setStyleSheet(DARK_THEME)

        self._full_image: np.ndarray | None = None
        self._preview_image: np.ndarray | None = None
        self._preview_scale: float = 1.0
        self._scan_result: ScanResult | None = None
        self._source_path: Path | None = None
        self._thread: QThread | None = None
        self._worker: ScanWorker | None = None
        self._manual_corners: np.ndarray | None = None
        self._processing = False
        self._scanner = DocumentScanner()

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(DEBOUNCE_MS)
        self._debounce.timeout.connect(self._schedule_scan)

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setSpacing(12)
        root.setContentsMargins(12, 12, 12, 12)

        main_splitter = QSplitter()
        root.addWidget(main_splitter)

        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setMaximumWidth(360)
        controls_scroll.setMinimumWidth(300)
        controls_panel = QWidget()
        controls_layout = QVBoxLayout(controls_panel)
        controls_layout.setSpacing(10)

        file_group = QGroupBox("File")
        file_layout = QVBoxLayout(file_group)
        self.upload_btn = QPushButton("Upload Image")
        self.save_btn = QPushButton("Save Result")
        self.save_btn.setEnabled(False)
        file_layout.addWidget(self.upload_btn)
        file_layout.addWidget(self.save_btn)
        self.export_full_res = QCheckBox("Export Original Resolution")
        self.export_full_res.setChecked(True)
        file_layout.addWidget(self.export_full_res)
        controls_layout.addWidget(file_group)

        detect_group = QGroupBox("Detection")
        detect_form = QFormLayout(detect_group)
        self.canny_lower = LabeledSlider("Canny Lower", 0, 500, 75)
        self.canny_upper = LabeledSlider("Canny Upper", 1, 500, 200)
        self.morph_kernel = LabeledSlider("Morph Kernel", 3, 31, 5, step=2)
        detect_form.addRow(self.canny_lower)
        detect_form.addRow(self.canny_upper)
        detect_form.addRow(self.morph_kernel)
        controls_layout.addWidget(detect_group)

        enhance_group = QGroupBox("Enhancement")
        enhance_form = QFormLayout(enhance_group)
        self.enhancement_mode = QComboBox()
        self.enhancement_mode.addItem("Adaptive Threshold", EnhancementMode.ADAPTIVE)
        self.enhancement_mode.addItem("Otsu Threshold", EnhancementMode.OTSU)
        self.enhancement_mode.addItem("No Enhancement", EnhancementMode.NONE)
        enhance_form.addRow("Mode:", self.enhancement_mode)
        controls_layout.addWidget(enhance_group)

        pre_group = QGroupBox("Optional Preprocessing")
        pre_layout = QVBoxLayout(pre_group)
        self.chk_clahe = QCheckBox("CLAHE contrast enhancement")
        self.chk_bilateral = QCheckBox("Bilateral filtering")
        self.chk_shadow = QCheckBox("Shadow reduction")
        self.chk_multi = QCheckBox("Multi-strategy detection")
        self.chk_multi.setChecked(True)
        self.chk_refine = QCheckBox("Auto corner refinement (cornerSubPix)")
        self.chk_refine.setChecked(True)
        pre_layout.addWidget(self.chk_clahe)
        pre_layout.addWidget(self.chk_bilateral)
        pre_layout.addWidget(self.chk_shadow)
        pre_layout.addWidget(self.chk_multi)
        pre_layout.addWidget(self.chk_refine)
        controls_layout.addWidget(pre_group)

        view_group = QGroupBox("Visualization")
        view_layout = QVBoxLayout(view_group)
        self.chk_overlay = QCheckBox("Show Detection Overlay")
        self.chk_overlay.setChecked(True)
        self.chk_corner_edit = QCheckBox("Manual Corner Editing")
        self.btn_reset_zoom = QPushButton("Reset Zoom / Comparison")
        self.btn_fit = QPushButton("Fit to Window")
        view_layout.addWidget(self.chk_overlay)
        view_layout.addWidget(self.chk_corner_edit)
        view_layout.addWidget(self.btn_reset_zoom)
        view_layout.addWidget(self.btn_fit)
        controls_layout.addWidget(view_group)

        metrics_group = QGroupBox("Metrics")
        metrics_layout = QVBoxLayout(metrics_group)
        self.metrics_label = QLabel("No scan yet.")
        self.metrics_label.setObjectName("metricsLabel")
        self.metrics_label.setWordWrap(True)
        self.confidence_label = QLabel("Detection Confidence: —")
        self.confidence_label.setStyleSheet("font-weight: 600; color: #6fcf97;")
        metrics_layout.addWidget(self.confidence_label)
        metrics_layout.addWidget(self.metrics_label)
        controls_layout.addWidget(metrics_group)

        controls_layout.addStretch()
        self.status_label = StatusBarLabel()
        self.status_label.setObjectName("statusLabel")
        controls_layout.addWidget(self.status_label)

        controls_scroll.setWidget(controls_panel)
        main_splitter.addWidget(controls_scroll)

        viz_splitter = QSplitter()
        self.viz_tabs = QTabWidget()
        self.comparison = ComparisonWidget()
        self.pipeline_viewer = PipelineViewer()
        self.zoom_original = ZoomPanViewer("Original — scroll to zoom, drag to pan")
        self.viz_tabs.addTab(self.comparison, "Compare")
        self.viz_tabs.addTab(self.pipeline_viewer, "Pipeline")
        self.viz_tabs.addTab(self.zoom_original, "Zoom / Pan")
        viz_splitter.addWidget(self.viz_tabs)
        main_splitter.addWidget(viz_splitter)
        main_splitter.setSizes([320, 1080])

    def _connect_signals(self) -> None:
        self.upload_btn.clicked.connect(self._on_upload)
        self.save_btn.clicked.connect(self._on_save)
        self.btn_reset_zoom.clicked.connect(self._on_reset_view)
        self.btn_fit.clicked.connect(self._on_fit_view)

        self.canny_lower.valueChanged.connect(self._on_setting_changed)
        self.canny_upper.valueChanged.connect(self._on_setting_changed)
        self.morph_kernel.valueChanged.connect(self._on_setting_changed)
        self.enhancement_mode.currentIndexChanged.connect(self._on_setting_changed)
        self.chk_clahe.stateChanged.connect(self._on_setting_changed)
        self.chk_bilateral.stateChanged.connect(self._on_setting_changed)
        self.chk_shadow.stateChanged.connect(self._on_setting_changed)
        self.chk_multi.stateChanged.connect(self._on_setting_changed)
        self.chk_refine.stateChanged.connect(self._on_setting_changed)
        self.chk_overlay.stateChanged.connect(self._update_display)
        self.chk_corner_edit.stateChanged.connect(self._on_corner_edit_toggled)
        self.zoom_original.cornersChanged.connect(self._on_manual_corners_changed)

    def _build_config(self) -> ScanConfig:
        morph = self.morph_kernel.value()
        if morph % 2 == 0:
            morph += 1

        lower = self.canny_lower.value()
        upper = self.canny_upper.value()
        if lower >= upper:
            upper = lower + 1

        return ScanConfig(
            canny_lower=lower,
            canny_upper=upper,
            morph_kernel_size=morph,
            enhancement_mode=self.enhancement_mode.currentData(),
            preprocess_options=PreprocessOptions(
                use_clahe=self.chk_clahe.isChecked(),
                use_bilateral=self.chk_bilateral.isChecked(),
                use_shadow_reduction=self.chk_shadow.isChecked(),
            ),
            refine_corners=self.chk_refine.isChecked(),
            multi_strategy=self.chk_multi.isChecked(),
            preview_max_dimension=1200,
        )

    def _on_setting_changed(self, *_args) -> None:
        if self._full_image is None:
            return
        self._debounce.start()

    def _on_upload(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            str(Path.home()),
            "Images (*.jpg *.jpeg *.png *.bmp)",
        )
        if not path:
            return

        if not is_supported_format(path):
            QMessageBox.warning(self, "Unsupported Format", "Please select JPG, JPEG, PNG, or BMP.")
            return

        try:
            image = load_image(path)
        except ValueError as exc:
            QMessageBox.critical(self, "Load Error", str(exc))
            self.status_label.set_error(str(exc))
            return

        self._full_image = image
        self._preview_image, self._preview_scale = resize_for_preview(image, 1200)
        self._source_path = Path(path)
        self._scan_result = None
        self._manual_corners = None
        self._scanner.invalidate_cache()

        self.zoom_original.set_image(image)
        self.comparison.set_images(image, None)
        self.save_btn.setEnabled(False)
        self.status_label.set_success(f"Loaded: {self._source_path.name}")
        self._schedule_scan()

    def _schedule_scan(self) -> None:
        if self._full_image is None or self._processing:
            if self._full_image is not None and self._processing:
                self._debounce.start()
            return

        self._processing = True
        self.status_label.set_progress("Processing...")

        config = self._build_config()
        work_image = self._preview_image if self._preview_image is not None else self._full_image

        preview_corners = None
        if self._manual_corners is not None and self._preview_scale < 1.0:
            preview_corners = (self._manual_corners * self._preview_scale).astype(np.float32)
        elif self._manual_corners is not None:
            preview_corners = self._manual_corners

        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(100)

        self._thread = QThread()
        self._worker = ScanWorker(self._scanner, work_image, config, preview_corners=preview_corners)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.stage_changed.connect(self.status_label.set_progress)
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_scan_finished(self, result: ScanResult) -> None:
        self._processing = False
        self._scan_result = result

        if not result.success:
            before = self._full_image
            self.comparison.set_images(before, result.detection_overlay or before)
            self.pipeline_viewer.update_stages(before, result.stages, result.detection_overlay)
            self.save_btn.setEnabled(False)
            self.confidence_label.setText(f"Detection Confidence: {result.confidence:.0f}%")
            self._update_metrics(result)
            self.status_label.set_error(result.message)
            self._update_corner_editor(result)
            if self._full_image is not None:
                self._debounce.start()
            return

        display = result.enhanced if result.enhanced is not None else result.warped
        before = self._full_image
        self.comparison.set_images(before, display)
        self.pipeline_viewer.update_stages(
            before, result.stages, result.detection_overlay, display
        )
        self.save_btn.setEnabled(True)
        self.confidence_label.setText(f"Detection Confidence: {result.confidence:.0f}%")
        self._update_metrics(result)
        self.status_label.set_success(
            f"Done ({result.elapsed_seconds * 1000:.0f} ms) — auto-updating on setting changes"
        )
        self._update_display()
        self._update_corner_editor(result)

    def _update_metrics(self, result: ScanResult) -> None:
        in_res = result.input_resolution or (0, 0)
        out_res = result.output_resolution or (0, 0)
        mode = "Preview" if result.preview_mode else "Full"
        lines = [
            f"Processing time: {result.elapsed_seconds * 1000:.0f} ms",
            f"Input resolution: {in_res[0]}×{in_res[1]}",
            f"Output resolution: {out_res[0]}×{out_res[1]}",
            f"Mode: {mode}",
        ]
        if result.detection and result.detection.strategy:
            lines.append(f"Strategy: {result.detection.strategy}")
        self.metrics_label.setText("\n".join(lines))

    def _update_display(self) -> None:
        if self._scan_result is None or self._full_image is None:
            return

        after = self._scan_result.enhanced or self._scan_result.warped
        self.comparison.set_images(self._full_image, after)

        corners = self._manual_corners if self._manual_corners is not None else self._scan_result.corners
        show = self.chk_overlay.isChecked()
        if corners is not None and self._preview_scale < 1.0 and self._scan_result.preview_mode:
            display_corners = corners
        else:
            display_corners = corners

        self.comparison.set_overlay_corners(display_corners, show)

    def _update_corner_editor(self, result: ScanResult) -> None:
        corners = self._manual_corners if self._manual_corners is not None else result.corners
        editable = self.chk_corner_edit.isChecked()
        if self._full_image is not None:
            self.zoom_original.set_image(self._full_image)
            if corners is not None:
                self.zoom_original.set_corners(corners, editable=editable)

    def _on_corner_edit_toggled(self) -> None:
        if self._scan_result:
            self._update_corner_editor(self._scan_result)

    def _on_manual_corners_changed(self, corners: np.ndarray) -> None:
        self._manual_corners = corners.copy()
        self._debounce.start()

    def _on_reset_view(self) -> None:
        self.comparison.reset_view()
        self.zoom_original.reset_zoom()

    def _on_fit_view(self) -> None:
        self.zoom_original.fit_in_view()

    def _on_save(self) -> None:
        if self._scan_result is None or self._full_image is None:
            self.status_label.set_error("No scanned result to save.")
            return

        default_name = "scanned_document.png"
        if self._source_path:
            default_name = f"{self._source_path.stem}_scanned.png"

        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Scanned Document",
            str(Path.home() / default_name),
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;PDF (*.pdf)",
        )
        if not path:
            return

        try:
            suffix = Path(path).suffix.lower()
            if not suffix:
                if "PDF" in selected_filter:
                    path = f"{path}.pdf"
                elif "JPEG" in selected_filter or "jpg" in selected_filter:
                    path = f"{path}.jpg"
                else:
                    path = f"{path}.png"

            image = self._get_export_image()

            if path.lower().endswith(".pdf"):
                save_as_pdf(image, path)
            else:
                save_image(image, path)

            self.status_label.set_success(f"Saved to {path}")
        except (ValueError, RuntimeError, OSError) as exc:
            QMessageBox.critical(self, "Save Error", str(exc))
            self.status_label.set_error(str(exc))

    def _get_export_image(self) -> np.ndarray:
        assert self._full_image is not None

        if not self.export_full_res.isChecked():
            img = self._scan_result.enhanced or self._scan_result.warped if self._scan_result else None
            if img is not None:
                return img

        self.status_label.set_progress("Exporting at full resolution...")
        config = self._build_config()
        scanner = DocumentScanner(config)
        corners = self._manual_corners if self._manual_corners is not None else (
            self._scan_result.corners if self._scan_result else None
        )
        result = scanner.scan_for_export(self._full_image, corners=corners)
        if not result.success:
            raise ValueError(result.message)
        return result.enhanced or result.warped  # type: ignore[return-value]
