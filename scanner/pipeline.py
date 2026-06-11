from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

import cv2
import numpy as np

from scanner.contour_detection import (
    DocumentDetectionResult,
    apply_morphological_closing,
    draw_detection_overlay,
    find_document_corners,
    find_document_corners_multi,
)
from scanner.corner_refinement import refine_corners
from scanner.edge_detection import detect_edges
from scanner.enhancement import EnhancementMode, enhance_document
from scanner.perspective import correct_perspective
from scanner.preprocessing import PreprocessOptions, preprocess, to_grayscale
from utils.image_utils import resize_for_preview, scale_corners_to_full, validate_image


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
    preprocess_options: PreprocessOptions = field(default_factory=PreprocessOptions)
    refine_corners: bool = True
    multi_strategy: bool = True
    preview_max_dimension: int | None = 1200


@dataclass
class PipelineStages:
    grayscale: np.ndarray | None = None
    preprocessed: np.ndarray | None = None
    edges: np.ndarray | None = None
    morphology: np.ndarray | None = None
    contour_overlay: np.ndarray | None = None
    final: np.ndarray | None = None


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
    confidence: float = 0.0
    stages: PipelineStages | None = None
    input_resolution: tuple[int, int] | None = None
    output_resolution: tuple[int, int] | None = None
    preview_mode: bool = False
    preview_scale: float = 1.0


class DocumentScanner:
    def __init__(self, config: ScanConfig | None = None) -> None:
        self.config = config or ScanConfig()
        self._cache_image_id: int | None = None
        self._cache_preprocess_key: str | None = None
        self._cached_gray: np.ndarray | None = None
        self._cached_blur: np.ndarray | None = None

    def _preprocess_key(self) -> str:
        opts = self.config.preprocess_options
        return (
            f"{opts.use_clahe}_{opts.use_bilateral}_{opts.use_shadow_reduction}_"
            f"{self.config.blur_kernel}"
        )

    def _get_preprocessed(
        self,
        image: np.ndarray,
        use_cache: bool,
    ) -> tuple[np.ndarray, np.ndarray]:
        image_id = id(image)
        key = self._preprocess_key()

        if (
            use_cache
            and self._cache_image_id == image_id
            and self._cache_preprocess_key == key
            and self._cached_gray is not None
            and self._cached_blur is not None
        ):
            return self._cached_gray, self._cached_blur

        gray, blurred = preprocess(
            image,
            blur_kernel=self.config.blur_kernel,
            options=self.config.preprocess_options,
        )
        self._cache_image_id = image_id
        self._cache_preprocess_key = key
        self._cached_gray = gray
        self._cached_blur = blurred
        return gray, blurred

    def invalidate_cache(self) -> None:
        self._cache_image_id = None
        self._cache_preprocess_key = None
        self._cached_gray = None
        self._cached_blur = None

    def scan(
        self,
        image: np.ndarray,
        *,
        manual_corners: np.ndarray | None = None,
        status_callback: Callable[[str], None] | None = None,
        use_cache: bool = True,
        force_full_resolution: bool = False,
    ) -> ScanResult:
        def emit(msg: str) -> None:
            if status_callback:
                status_callback(msg)

        start = time.perf_counter()
        timings: dict[str, float] = {}
        stages = PipelineStages()

        try:
            validate_image(image)
        except ValueError as exc:
            return ScanResult(success=False, message=str(exc))

        full_original = image.copy()
        input_h, input_w = full_original.shape[:2]
        preview_scale = 1.0
        preview_mode = False

        work_image = full_original
        if not force_full_resolution and self.config.preview_max_dimension:
            work_image, preview_scale = resize_for_preview(
                full_original, self.config.preview_max_dimension
            )
            preview_mode = preview_scale < 1.0

        original = work_image.copy()
        emit("Processing...")

        try:
            t0 = time.perf_counter()
            emit("Preprocessing...")
            gray, gray_blur = self._get_preprocessed(original, use_cache=use_cache)
            stages.grayscale = gray
            stages.preprocessed = gray_blur
            timings["preprocess"] = time.perf_counter() - t0

            t0 = time.perf_counter()
            emit("Detecting edges...")
            edges = detect_edges(
                gray_blur,
                lower_threshold=self.config.canny_lower,
                upper_threshold=self.config.canny_upper,
            )
            stages.edges = edges
            timings["edge_detection"] = time.perf_counter() - t0

            closed_edges = apply_morphological_closing(
                edges, kernel_size=self.config.morph_kernel_size
            )
            stages.morphology = closed_edges

            t0 = time.perf_counter()
            emit("Finding contours...")
            if manual_corners is not None:
                corners = manual_corners.astype(np.float32)
                if preview_scale < 1.0:
                    corners = corners.copy()
                detection = DocumentDetectionResult(
                    corners=corners,
                    success=True,
                    message="Using manual corners.",
                    confidence=100.0,
                    strategy="manual",
                )
            elif self.config.multi_strategy:
                detection = find_document_corners_multi(
                    gray_blur,
                    edges,
                    closed_edges,
                    original.shape,
                    morph_kernel_size=self.config.morph_kernel_size,
                    epsilon_ratio=self.config.epsilon_ratio,
                    min_area_ratio=self.config.min_area_ratio,
                )
            else:
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
                overlay = draw_detection_overlay(original, None)
                stages.contour_overlay = overlay
                return ScanResult(
                    success=False,
                    message=detection.message,
                    original=full_original,
                    detection=detection,
                    confidence=detection.confidence,
                    stages=stages,
                    input_resolution=(input_w, input_h),
                    preview_mode=preview_mode,
                    preview_scale=preview_scale,
                    elapsed_seconds=elapsed,
                    timings=timings,
                )

            corners = detection.corners.copy()
            if self.config.refine_corners and manual_corners is None:
                corners = refine_corners(gray_blur, corners)

            overlay = draw_detection_overlay(original, corners)
            stages.contour_overlay = overlay

            t0 = time.perf_counter()
            emit("Applying perspective correction...")
            try:
                warped = correct_perspective(original, corners)
                perspective_success = True
            except (ValueError, Exception) as exc:
                elapsed = time.perf_counter() - start
                return ScanResult(
                    success=False,
                    message=f"Perspective correction failed: {exc}",
                    original=full_original,
                    detection_overlay=overlay,
                    corners=corners,
                    detection=detection,
                    confidence=detection.confidence,
                    perspective_success=False,
                    stages=stages,
                    input_resolution=(input_w, input_h),
                    preview_mode=preview_mode,
                    preview_scale=preview_scale,
                    elapsed_seconds=elapsed,
                    timings=timings,
                )
            timings["perspective"] = time.perf_counter() - t0

            t0 = time.perf_counter()
            emit("Enhancing document...")
            enhanced = enhance_document(
                warped,
                mode=self.config.enhancement_mode,
                block_size=self.config.adaptive_block_size,
                c_constant=self.config.adaptive_c,
            )
            stages.final = enhanced
            timings["enhancement"] = time.perf_counter() - t0

            out_h, out_w = enhanced.shape[:2]
            elapsed = time.perf_counter() - start
            emit(f"Done ({elapsed * 1000:.0f} ms)")

            full_corners = scale_corners_to_full(corners, preview_scale) if preview_scale < 1.0 else corners

            return ScanResult(
                success=True,
                message="Document scanned successfully.",
                original=full_original,
                detection_overlay=overlay,
                warped=warped,
                enhanced=enhanced,
                corners=full_corners,
                detection=detection,
                confidence=detection.confidence,
                perspective_success=True,
                stages=stages,
                input_resolution=(input_w, input_h),
                output_resolution=(out_w, out_h),
                preview_mode=preview_mode,
                preview_scale=preview_scale,
                elapsed_seconds=elapsed,
                timings=timings,
            )

        except Exception as exc:
            elapsed = time.perf_counter() - start
            return ScanResult(
                success=False,
                message=f"Processing error: {exc}",
                original=full_original,
                stages=stages,
                input_resolution=(input_w, input_h),
                preview_mode=preview_mode,
                preview_scale=preview_scale,
                elapsed_seconds=elapsed,
                timings=timings,
            )

    def scan_for_export(
        self,
        image: np.ndarray,
        corners: np.ndarray | None = None,
        status_callback: Callable[[str], None] | None = None,
    ) -> ScanResult:
        saved_preview = self.config.preview_max_dimension
        self.config.preview_max_dimension = None
        try:
            return self.scan(
                image,
                manual_corners=corners,
                status_callback=status_callback,
                use_cache=False,
                force_full_resolution=True,
            )
        finally:
            self.config.preview_max_dimension = saved_preview
