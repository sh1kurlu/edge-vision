from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from scanner.contour_detection import DocumentDetectionResult, draw_detection_overlay, find_document_corners
from scanner.edge_detection import detect_edges
from scanner.enhancement import EnhancementMode, enhance_document
from scanner.perspective import correct_perspective
from scanner.preprocessing import preprocess
from utils.image_utils import validate_image


@dataclass
class ScanConfig:
    canny_lower: int = 75
    canny_upper: int = 200
    blur_kernel: tuple[int, int] = (5, 5)
    morph_kernel_size: int = 5
    epsilon_ratio: float = 0.02
    min_area_ratio: float = 0.05
    enhancement_mode: EnhancementMode = EnhancementMode.ADAPTIVE
    adaptive_block_size: int = 11
    adaptive_c: int = 2


@dataclass
class ScanResult:
    success: bool
    message: str
    original: np.ndarray | None = None
    detection_overlay: np.ndarray | None = None
    warped: np.ndarray | None = None
    enhanced: np.ndarray | None = None
    corners: np.ndarray | None = None
    detection: DocumentDetectionResult | None = None
    perspective_success: bool = False
    elapsed_seconds: float = 0.0
    timings: dict[str, float] = field(default_factory=dict)


class DocumentScanner:
    def __init__(self, config: ScanConfig | None = None) -> None:
        self.config = config or ScanConfig()

    def scan(self, image: np.ndarray) -> ScanResult:
        start = time.perf_counter()
        timings: dict[str, float] = {}

        try:
            validate_image(image)
        except ValueError as exc:
            return ScanResult(success=False, message=str(exc))

        original = image.copy()
        t0 = time.perf_counter()

        try:
            gray_blur = preprocess(original, blur_kernel=self.config.blur_kernel)
            timings["preprocess"] = time.perf_counter() - t0

            t0 = time.perf_counter()
            edges = detect_edges(
                gray_blur,
                lower_threshold=self.config.canny_lower,
                upper_threshold=self.config.canny_upper,
            )
            timings["edge_detection"] = time.perf_counter() - t0

            t0 = time.perf_counter()
            detection = find_document_corners(
                edges,
                original.shape,
                morph_kernel_size=self.config.morph_kernel_size,
                epsilon_ratio=self.config.epsilon_ratio,
                min_area_ratio=self.config.min_area_ratio,
            )
            timings["contour_detection"] = time.perf_counter() - t0

            if not detection.success or detection.corners is None:
                elapsed = time.perf_counter() - start
                return ScanResult(
                    success=False,
                    message=detection.message,
                    original=original,
                    detection=detection,
                    elapsed_seconds=elapsed,
                    timings=timings,
                )

            overlay = draw_detection_overlay(original, detection.corners)

            t0 = time.perf_counter()
            try:
                warped = correct_perspective(original, detection.corners)
                perspective_success = True
            except (ValueError, Exception) as exc:
                elapsed = time.perf_counter() - start
                return ScanResult(
                    success=False,
                    message=f"Perspective correction failed: {exc}",
                    original=original,
                    detection_overlay=overlay,
                    corners=detection.corners,
                    detection=detection,
                    perspective_success=False,
                    elapsed_seconds=elapsed,
                    timings=timings,
                )
            timings["perspective"] = time.perf_counter() - t0

            t0 = time.perf_counter()
            enhanced = enhance_document(
                warped,
                mode=self.config.enhancement_mode,
                block_size=self.config.adaptive_block_size,
                c_constant=self.config.adaptive_c,
            )
            timings["enhancement"] = time.perf_counter() - t0

            elapsed = time.perf_counter() - start
            return ScanResult(
                success=True,
                message="Document scanned successfully.",
                original=original,
                detection_overlay=overlay,
                warped=warped,
                enhanced=enhanced,
                corners=detection.corners,
                detection=detection,
                perspective_success=True,
                elapsed_seconds=elapsed,
                timings=timings,
            )

        except Exception as exc:
            elapsed = time.perf_counter() - start
            return ScanResult(
                success=False,
                message=f"Processing error: {exc}",
                original=original,
                elapsed_seconds=elapsed,
                timings=timings,
            )
