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
from gui.header import AppHeader
from gui.labeled_slider import LabeledSlider
from gui.pipeline_viewer import PipelineViewer
from gui.theme import DARK_THEME
from gui.widgets import StatusBarLabel
from scanner.enhancement import EnhancementMode
from scanner.pipeline import DocumentScanner, ScanConfig, ScanResult
from scanner.preprocessing import PreprocessOptions
from utils.image_utils import is_supported_format, load_image, resize_for_preview, save_image
from utils.pdf_export import save_as_pdf

DEBOUNCE_MS = 400


class ScanWorker(QObject):
    finished = Signal(int, object)
    stage_changed = Signal(str)

    def __init__(
        self,
        scanner: DocumentScanner,
        image: np.ndarray,
        config: ScanConfig,
        generation: int,
    ) -> None:
        super().__init__()
        self._scanner = scanner
        self._image = image
        self._config = config
        self._generation = generation

    @Slot()
    def run(self) -> None:
        def on_stage(msg: str) -> None:
            self.stage_changed.emit(msg)

        self._scanner.config = self._config
        result = self._scanner.scan(
            self._image,
            status_callback=on_stage,
            use_cache=True,
        )
        self.finished.emit(self._generation, result)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("EdgeVision")
        self.resize(1400, 860)
        self.setStyleSheet(DARK_THEME)

        self._full_image: np.ndarray | None = None
        self._preview_image: np.ndarray | None = None
        self._scan_result: ScanResult | None = None
        self._source_path: Path | None = None
        self._thread: QThread | None = None
        self._worker: ScanWorker | None = None
        self._processing = False
        self._scan_generation = 0
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
        root = QVBoxLayout(central)
        root.setSpacing(8)
        root.setContentsMargins(16, 12, 16, 16)

        root.addWidget(AppHeader())

        main_splitter = QSplitter()
        root.addWidget(main_splitter, stretch=1)

        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setMaximumWidth(340)
        controls_scroll.setMinimumWidth(280)
        controls_panel = QWidget()
        controls_layout = QVBoxLayout(controls_panel)
        controls_layout.setSpacing(12)
        controls_layout.setContentsMargins(4, 4, 8, 4)

        file_group = QGroupBox("File")
        file_layout = QVBoxLayout(file_group)
        file_layout.setSpacing(8)
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
        detect_form.setSpacing(10)
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
        pre_layout.setSpacing(6)
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
        view_layout.setSpacing(6)
        self.chk_overlay = QCheckBox("Show Detection Overlay")
        self.chk_overlay.setChecked(True)
        self.btn_reset_comparison = QPushButton("Reset Comparison")
        self.btn_reset_comparison.setObjectName("secondaryButton")
        view_layout.addWidget(self.chk_overlay)
        view_layout.addWidget(self.btn_reset_comparison)
        controls_layout.addWidget(view_group)

        metrics_group = QGroupBox("Processing Info")
        metrics_layout = QVBoxLayout(metrics_group)
        self.metrics_label = QLabel("No scan yet.")
        self.metrics_label.setObjectName("metricsLabel")
        self.metrics_label.setWordWrap(True)
        metrics_layout.addWidget(self.metrics_label)
        controls_layout.addWidget(metrics_group)

        controls_layout.addStretch()
        self.status_label = StatusBarLabel()
        self.status_label.setObjectName("statusLabel")
        controls_layout.addWidget(self.status_label)

        controls_scroll.setWidget(controls_panel)
        main_splitter.addWidget(controls_scroll)

        viz_panel = QWidget()
        viz_layout = QVBoxLayout(viz_panel)
        viz_layout.setContentsMargins(0, 0, 0, 0)
        viz_layout.setSpacing(8)

        compare_label = QLabel("Enhancement Comparison")
        compare_label.setObjectName("sectionTitle")
        viz_layout.addWidget(compare_label)

        self.viz_tabs = QTabWidget()
        self.comparison = ComparisonWidget()
        self.pipeline_viewer = PipelineViewer()
        self.viz_tabs.addTab(self.comparison, "Compare")
        self.viz_tabs.addTab(self.pipeline_viewer, "Pipeline")
        viz_layout.addWidget(self.viz_tabs, stretch=1)

        main_splitter.addWidget(viz_panel)
        main_splitter.setSizes([300, 1100])

    def _connect_signals(self) -> None:
        self.upload_btn.clicked.connect(self._on_upload)
        self.save_btn.clicked.connect(self._on_save)
        self.btn_reset_comparison.clicked.connect(self.comparison.reset_view)

        self.canny_lower.valueChanged.connect(self._on_setting_changed)
        self.canny_upper.valueChanged.connect(self._on_setting_changed)
        self.morph_kernel.valueChanged.connect(self._on_morph_changed)
        self.enhancement_mode.currentIndexChanged.connect(self._on_setting_changed)
        self.chk_clahe.stateChanged.connect(self._on_setting_changed)
        self.chk_bilateral.stateChanged.connect(self._on_setting_changed)
        self.chk_shadow.stateChanged.connect(self._on_setting_changed)
        self.chk_multi.stateChanged.connect(self._on_setting_changed)
        self.chk_refine.stateChanged.connect(self._on_setting_changed)
        self.chk_overlay.stateChanged.connect(self._refresh_pipeline_overlay)

    def _on_morph_changed(self, val: int) -> None:
        if val % 2 == 0:
            self.morph_kernel.setValue(val + 1)
            return
        self._on_setting_changed()

    def _build_config(self) -> ScanConfig:
        morph = self.morph_kernel.value()
        if morph % 2 == 0:
            morph += 1

        lower = self.canny_lower.value()
        upper = self.canny_upper.value()
        if lower >= upper:
            upper = lower + 1
            if self.canny_upper.value() != upper:
                self.canny_upper.setValue(upper)

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
        self._scan_generation += 1
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
        self._preview_image, _ = resize_for_preview(image, 1200)
        self._source_path = Path(path)
        self._scan_result = None
        self._scanner.invalidate_cache()
        self.comparison.set_images(None, None)
        self.save_btn.setEnabled(False)
        self.status_label.set_success(f"Loaded: {self._source_path.name}")
        self._scan_generation += 1
        self._schedule_scan()

    def _schedule_scan(self) -> None:
        if self._full_image is None:
            return

        if self._processing:
            self._debounce.start()
            return

        self._processing = True
        generation = self._scan_generation
        self.status_label.set_progress("Processing...")

        config = self._build_config()
        work_image = self._preview_image if self._preview_image is not None else self._full_image

        if self._thread is not None and self._thread.isRunning():
            self._thread.requestInterruption()
            self._thread.quit()
            self._thread.wait(200)

        self._thread = QThread()
        self._worker = ScanWorker(self._scanner, work_image, config, generation)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.stage_changed.connect(self.status_label.set_progress)
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_scan_finished(self, generation: int, result: ScanResult) -> None:
        self._processing = False

        if generation != self._scan_generation:
            self._debounce.start()
            return

        self._scan_result = result
        self._apply_result(result)

        if self._scan_generation != generation:
            self._debounce.start()

    def _apply_result(self, result: ScanResult) -> None:
        if not result.success:
            self.comparison.set_images(None, None)
            self.pipeline_viewer.update_stages(
                self._full_image, result.stages, result.detection_overlay
            )
            self.save_btn.setEnabled(False)
            self._update_metrics(result)
            self.status_label.set_error(result.message)
            return

        warped = result.warped
        enhanced = result.enhanced if result.enhanced is not None else result.warped
        self.comparison.set_images(warped, enhanced)
        self._refresh_pipeline_overlay()
        self.save_btn.setEnabled(True)
        self._update_metrics(result)
        self.status_label.set_success(f"Done ({result.elapsed_seconds * 1000:.0f} ms)")

    def _refresh_pipeline_overlay(self) -> None:
        if self._scan_result is None or self._full_image is None:
            return

        result = self._scan_result
        overlay = result.detection_overlay if self.chk_overlay.isChecked() else None
        self.pipeline_viewer.update_stages(
            self._full_image,
            result.stages,
            overlay,
            result.warped,
            result.enhanced,
        )

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
        self.metrics_label.setText("\n".join(lines))

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
        corners = self._scan_result.corners if self._scan_result else None
        result = scanner.scan_for_export(self._full_image, corners=corners)
        if not result.success:
            raise ValueError(result.message)
        return result.enhanced or result.warped  # type: ignore[return-value]
