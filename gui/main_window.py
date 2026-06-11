from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from gui.widgets import ImagePreview, StatusBarLabel
from scanner.enhancement import EnhancementMode
from scanner.pipeline import DocumentScanner, ScanConfig, ScanResult
from utils.image_utils import is_supported_format, load_image, save_image
from utils.pdf_export import save_as_pdf


class ScanWorker(QObject):
    finished = Signal(object)
    progress = Signal(str)

    def __init__(self, image: np.ndarray, config: ScanConfig) -> None:
        super().__init__()
        self._image = image
        self._config = config

    @Slot()
    def run(self) -> None:
        self.progress.emit("Preprocessing image...")
        scanner = DocumentScanner(self._config)
        self.progress.emit("Detecting document edges...")
        result = scanner.scan(self._image)
        self.finished.emit(result)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Document Scanner")
        self.resize(1200, 720)

        self._original_image: np.ndarray | None = None
        self._scan_result: ScanResult | None = None
        self._source_path: Path | None = None
        self._thread: QThread | None = None
        self._worker: ScanWorker | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        splitter = QSplitter()
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("Original Image"))
        self.original_preview = ImagePreview("Upload an image to preview")
        left_panel.addWidget(self.original_preview)

        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("Scanned Result"))
        self.result_preview = ImagePreview("Processed result will appear here")
        right_panel.addWidget(self.result_preview)

        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 600])
        root.addWidget(splitter, stretch=1)

        settings_group = QGroupBox("Detection & Enhancement Settings")
        settings_layout = QFormLayout(settings_group)

        self.canny_lower = QSpinBox()
        self.canny_lower.setRange(0, 500)
        self.canny_lower.setValue(75)
        settings_layout.addRow("Canny Lower:", self.canny_lower)

        self.canny_upper = QSpinBox()
        self.canny_upper.setRange(1, 500)
        self.canny_upper.setValue(200)
        settings_layout.addRow("Canny Upper:", self.canny_upper)

        self.morph_kernel = QSpinBox()
        self.morph_kernel.setRange(3, 31)
        self.morph_kernel.setSingleStep(2)
        self.morph_kernel.setValue(5)
        settings_layout.addRow("Morph Kernel:", self.morph_kernel)

        self.enhancement_mode = QComboBox()
        self.enhancement_mode.addItem("Adaptive Threshold", EnhancementMode.ADAPTIVE)
        self.enhancement_mode.addItem("Otsu Threshold", EnhancementMode.OTSU)
        self.enhancement_mode.addItem("No Enhancement", EnhancementMode.NONE)
        settings_layout.addRow("Enhancement:", self.enhancement_mode)

        root.addWidget(settings_group)

        btn_row = QHBoxLayout()
        self.upload_btn = QPushButton("Upload Image")
        self.upload_btn.clicked.connect(self._on_upload)
        btn_row.addWidget(self.upload_btn)

        self.scan_btn = QPushButton("Scan Document")
        self.scan_btn.setEnabled(False)
        self.scan_btn.clicked.connect(self._on_scan)
        btn_row.addWidget(self.scan_btn)

        self.save_btn = QPushButton("Save Result")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self.save_btn)

        root.addLayout(btn_row)

        self.status_label = StatusBarLabel()
        root.addWidget(self.status_label)

    def _build_config(self) -> ScanConfig:
        morph = self.morph_kernel.value()
        if morph % 2 == 0:
            morph += 1
            self.morph_kernel.setValue(morph)

        lower = self.canny_lower.value()
        upper = self.canny_upper.value()
        if lower >= upper:
            upper = lower + 1
            self.canny_upper.setValue(upper)

        return ScanConfig(
            canny_lower=lower,
            canny_upper=upper,
            morph_kernel_size=morph,
            enhancement_mode=self.enhancement_mode.currentData(),
        )

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
            QMessageBox.warning(
                self,
                "Unsupported Format",
                "Please select a JPG, JPEG, PNG, or BMP image.",
            )
            return

        try:
            image = load_image(path)
        except ValueError as exc:
            QMessageBox.critical(self, "Load Error", str(exc))
            self.status_label.set_error(str(exc))
            return

        self._original_image = image
        self._source_path = Path(path)
        self._scan_result = None
        self.original_preview.set_image(image)
        self.result_preview.set_image(None)
        self.scan_btn.setEnabled(True)
        self.save_btn.setEnabled(False)
        self.status_label.set_success(f"Loaded: {self._source_path.name}")

    def _on_scan(self) -> None:
        if self._original_image is None:
            self.status_label.set_error("No image loaded.")
            return

        self.scan_btn.setEnabled(False)
        self.upload_btn.setEnabled(False)
        self.status_label.set_progress("Scanning document...")

        config = self._build_config()
        self._thread = QThread()
        self._worker = ScanWorker(self._original_image.copy(), config)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.status_label.set_progress)
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_scan_finished(self, result: ScanResult) -> None:
        self._scan_result = result
        self.scan_btn.setEnabled(True)
        self.upload_btn.setEnabled(True)

        if not result.success:
            self.result_preview.set_image(result.detection_overlay or result.original)
            self.save_btn.setEnabled(False)
            self.status_label.set_error(result.message)
            QMessageBox.warning(self, "Detection Failed", result.message)
            return

        display = result.enhanced if result.enhanced is not None else result.warped
        self.result_preview.set_image(display)
        self.save_btn.setEnabled(True)

        timing = f"{result.elapsed_seconds:.2f}s"
        self.status_label.set_success(f"{result.message} ({timing})")

    def _on_save(self) -> None:
        if self._scan_result is None or not self._scan_result.success:
            self.status_label.set_error("No scanned result to save.")
            return

        image = self._scan_result.enhanced or self._scan_result.warped
        if image is None:
            self.status_label.set_error("No processed image available.")
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

            if path.lower().endswith(".pdf"):
                save_as_pdf(image, path)
            else:
                save_image(image, path)

            self.status_label.set_success(f"Saved to {path}")
        except (ValueError, RuntimeError, OSError) as exc:
            QMessageBox.critical(self, "Save Error", str(exc))
            self.status_label.set_error(str(exc))
