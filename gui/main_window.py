from __future__ import annotations

import copy
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QMetaObject, QObject, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gui.comparison_widget import ComparisonWidget
from gui.header import AppHeader
from gui.labeled_slider import LabeledSlider
from gui.pipeline_viewer import PipelineViewer
from gui.theme import DARK_THEME
from gui.widgets import EmptyWorkspace, StatusBarLabel
from scanner.enhancement import EnhancementMode
from scanner.pipeline import DocumentScanner, ScanConfig, ScanResult
from scanner.preprocessing import PreprocessOptions
from utils.image_utils import is_supported_format, load_image, resize_for_preview, save_image
from utils.pdf_export import save_as_pdf

DEBOUNCE_MS = 400

_STAGE_STATUS = {
    "Processing...": "Processing scan...",
    "Preprocessing...": "Preparing image...",
    "Detecting edges...": "Detecting document...",
    "Finding contours...": "Locating document boundaries...",
    "Applying perspective correction...": "Applying perspective correction...",
    "Enhancing document...": "Enhancing scan...",
}


def _diag(msg: str) -> None:
    print(f"[EdgeVision] {msg}", flush=True)


class ScanWorker(QObject):
    finished = Signal(int, object)
    stage_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._image: np.ndarray | None = None
        self._config: ScanConfig | None = None
        self._generation = 0

    def prepare(self, image: np.ndarray, config: ScanConfig, generation: int) -> None:
        self._image = image
        self._config = copy.deepcopy(config)
        self._generation = generation

    @Slot()
    def run(self) -> None:
        cv2.setNumThreads(1)

        def on_stage(msg: str) -> None:
            self.stage_changed.emit(msg)

        assert self._image is not None and self._config is not None
        scanner = DocumentScanner(self._config)
        result = scanner.scan(
            self._image,
            status_callback=on_stage,
            use_cache=True,
        )
        self.finished.emit(self._generation, result)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("EdgeVision — Smart Document Scanner")
        self.resize(1440, 880)
        self.setStyleSheet(DARK_THEME)

        self._full_image: np.ndarray | None = None
        self._preview_image: np.ndarray | None = None
        self._scan_result: ScanResult | None = None
        self._source_path: Path | None = None
        self._thread: QThread | None = None
        self._processing = False
        self._scan_generation = 0
        self._scanner = DocumentScanner()

        self._thread = QThread(self)
        self._worker = ScanWorker()
        self._worker.moveToThread(self._thread)
        self._thread.start()
        _diag("THREAD CREATED")

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(DEBOUNCE_MS)
        self._debounce.timeout.connect(self._schedule_scan)

        self._build_ui()
        self._connect_signals()
        self._update_workspace_state()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(0)
        root.setContentsMargins(20, 16, 20, 0)

        root.addWidget(AppHeader())

        body = QHBoxLayout()
        body.setSpacing(0)
        body.setContentsMargins(0, 12, 0, 0)

        main_splitter = QSplitter(Qt.Horizontal)
        body.addWidget(main_splitter, stretch=1)
        root.addLayout(body, stretch=1)

        sidebar = QWidget()
        sidebar.setObjectName("sidebarPanel")
        sidebar.setMaximumWidth(300)
        sidebar.setMinimumWidth(260)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 12, 0)
        sidebar_layout.setSpacing(0)

        controls_scroll = QScrollArea()
        controls_scroll.setObjectName("sidebarScroll")
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        controls_panel = QWidget()
        controls_layout = QVBoxLayout(controls_panel)
        controls_layout.setSpacing(4)
        controls_layout.setContentsMargins(0, 0, 4, 12)

        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(8)
        self.upload_btn = QPushButton("Upload Image")
        self.upload_btn.setObjectName("primaryButton")
        self.save_btn = QPushButton("Save Result")
        self.save_btn.setObjectName("secondaryButton")
        self.save_btn.setEnabled(False)
        actions_layout.addWidget(self.upload_btn)
        actions_layout.addWidget(self.save_btn)
        self.export_full_res = QCheckBox("Export at original resolution")
        self.export_full_res.setChecked(True)
        actions_layout.addWidget(self.export_full_res)
        controls_layout.addLayout(actions_layout)

        detect_group = QGroupBox("Detection")
        detect_layout = QVBoxLayout(detect_group)
        detect_layout.setSpacing(12)
        self.canny_lower = LabeledSlider("Canny Lower", 0, 500, 75)
        self.canny_upper = LabeledSlider("Canny Upper", 1, 500, 200)
        self.morph_kernel = LabeledSlider("Morph Kernel", 3, 31, 5, step=2)
        detect_layout.addWidget(self.canny_lower)
        detect_layout.addWidget(self.canny_upper)
        detect_layout.addWidget(self.morph_kernel)
        self.chk_multi = QCheckBox("Multi-strategy detection")
        self.chk_multi.setChecked(True)
        self.chk_refine = QCheckBox("Corner refinement")
        self.chk_refine.setChecked(True)
        detect_layout.addWidget(self.chk_multi)
        detect_layout.addWidget(self.chk_refine)
        controls_layout.addWidget(detect_group)

        enhance_group = QGroupBox("Enhancement")
        enhance_layout = QVBoxLayout(enhance_group)
        enhance_layout.setSpacing(8)
        mode_row = QHBoxLayout()
        mode_label = QLabel("Mode")
        mode_label.setObjectName("fieldLabel")
        mode_row.addWidget(mode_label)
        self.enhancement_mode = QComboBox()
        self.enhancement_mode.addItem("Adaptive Threshold", EnhancementMode.ADAPTIVE)
        self.enhancement_mode.addItem("Otsu Threshold", EnhancementMode.OTSU)
        self.enhancement_mode.addItem("No Enhancement", EnhancementMode.NONE)
        mode_row.addWidget(self.enhancement_mode, stretch=1)
        enhance_layout.addLayout(mode_row)
        controls_layout.addWidget(enhance_group)

        pre_group = QGroupBox("Preprocessing")
        pre_layout = QVBoxLayout(pre_group)
        pre_layout.setSpacing(4)
        self.chk_clahe = QCheckBox("CLAHE")
        self.chk_bilateral = QCheckBox("Bilateral filter")
        self.chk_shadow = QCheckBox("Shadow reduction")
        pre_layout.addWidget(self.chk_clahe)
        pre_layout.addWidget(self.chk_bilateral)
        pre_layout.addWidget(self.chk_shadow)
        controls_layout.addWidget(pre_group)

        view_group = QGroupBox("View")
        view_layout = QVBoxLayout(view_group)
        view_layout.setSpacing(4)
        self.chk_overlay = QCheckBox("Show detection overlay")
        self.chk_overlay.setChecked(True)
        self.btn_reset_comparison = QPushButton("Reset comparison divider")
        self.btn_reset_comparison.setObjectName("textButton")
        view_layout.addWidget(self.chk_overlay)
        view_layout.addWidget(self.btn_reset_comparison)
        controls_layout.addWidget(view_group)

        controls_layout.addStretch()
        controls_scroll.setWidget(controls_panel)
        sidebar_layout.addWidget(controls_scroll)
        main_splitter.addWidget(sidebar)

        workspace = QWidget()
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(12, 0, 0, 0)
        workspace_layout.setSpacing(8)

        workspace_header = QHBoxLayout()
        workspace_title = QLabel("SCAN PREVIEW")
        workspace_title.setObjectName("sectionTitle")
        workspace_header.addWidget(workspace_title)
        workspace_header.addStretch()
        self.compare_hint = QLabel("Drag the divider to compare rectified and enhanced results")
        self.compare_hint.setObjectName("workspaceHint")
        workspace_header.addWidget(self.compare_hint)
        workspace_layout.addLayout(workspace_header)

        self.workspace_stack = QStackedWidget()
        self.empty_workspace = EmptyWorkspace()
        self.workspace_stack.addWidget(self.empty_workspace)

        viz_panel = QWidget()
        viz_layout = QVBoxLayout(viz_panel)
        viz_layout.setContentsMargins(0, 0, 0, 0)
        viz_layout.setSpacing(0)

        self.viz_tabs = QTabWidget()
        self.viz_tabs.setObjectName("workspaceTabs")
        self.comparison = ComparisonWidget()
        self.pipeline_viewer = PipelineViewer()
        self.viz_tabs.addTab(self.comparison, "Compare")
        self.viz_tabs.addTab(self.pipeline_viewer, "Pipeline")
        viz_layout.addWidget(self.viz_tabs, stretch=1)

        self.workspace_stack.addWidget(viz_panel)
        workspace_layout.addWidget(self.workspace_stack, stretch=1)

        main_splitter.addWidget(workspace)
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setSizes([280, 1160])

        status_bar = QWidget()
        status_bar.setObjectName("statusBar")
        status_bar.setFixedHeight(36)
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(20, 0, 20, 0)
        self.status_label = StatusBarLabel()
        status_layout.addWidget(self.status_label)
        root.addWidget(status_bar)

    def _connect_signals(self) -> None:
        self.upload_btn.clicked.connect(self._on_upload)
        self.empty_workspace.upload_requested.connect(self._on_upload)
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

        self._worker.stage_changed.connect(self._on_stage_changed)
        self._worker.finished.connect(self._on_scan_finished)

        self.viz_tabs.currentChanged.connect(self._on_viz_tab_changed)

    def _on_viz_tab_changed(self, index: int) -> None:
        self.compare_hint.setVisible(index == 0)

    def _on_stage_changed(self, message: str) -> None:
        friendly = _STAGE_STATUS.get(message, message)
        if message.startswith("Done"):
            return
        self.status_label.set_progress(friendly)

    def _update_workspace_state(self) -> None:
        has_image = self._full_image is not None
        self.workspace_stack.setCurrentIndex(1 if has_image else 0)
        self.compare_hint.setVisible(has_image and self.viz_tabs.currentIndex() == 0)

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
            enhancement_mode=self.enhancement_mode.currentData(Qt.UserRole),
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
        self._scanner.invalidate_cache()
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
        self._update_workspace_state()
        self.status_label.set_info(f"Image loaded — {self._source_path.name}")
        self._scan_generation += 1
        self._schedule_scan()

    def _schedule_scan(self) -> None:
        if self._full_image is None:
            return

        if self._processing:
            self._debounce.start()
            return

        if self._thread is None:
            return

        self._processing = True
        generation = self._scan_generation
        self.status_label.set_progress("Processing scan...")
        _diag(f"SCAN STARTED (generation={generation})")

        config = self._build_config()
        work_image = self._preview_image if self._preview_image is not None else self._full_image

        self._worker.prepare(work_image, config, generation)
        QMetaObject.invokeMethod(self._worker, "run", Qt.ConnectionType.QueuedConnection)

    def _on_scan_finished(self, generation: int, result: ScanResult) -> None:
        _diag(f"SCAN COMPLETED (generation={generation})")
        self._processing = False

        if generation != self._scan_generation:
            self._debounce.start()
            return

        self._scan_result = result
        self._apply_result(result)

        if self._scan_generation != generation:
            self._debounce.start()

    def closeEvent(self, event: QCloseEvent) -> None:
        thread = self._thread
        if thread is not None and thread.isRunning():
            thread.quit()
            thread.wait(3000)
            _diag("THREAD FINISHED")
        self._thread = None
        _diag("THREAD CLEANED UP")
        super().closeEvent(event)

    def _apply_result(self, result: ScanResult) -> None:
        if not result.success:
            self.comparison.set_images(None, None)
            self.pipeline_viewer.update_stages(
                self._full_image, result.stages, result.detection_overlay
            )
            self.save_btn.setEnabled(False)
            self.status_label.set_error(result.message)
            return

        warped = result.warped
        enhanced = result.enhanced if result.enhanced is not None else result.warped
        self.comparison.set_images(warped, enhanced)
        self._refresh_pipeline_overlay()
        self.save_btn.setEnabled(True)
        ms = result.elapsed_seconds * 1000
        self.status_label.set_success(f"Scan complete — {ms:.0f} ms")

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

            self.status_label.set_success("Saved successfully")
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
