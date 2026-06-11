from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class DocumentDetectionResult:
    corners: np.ndarray | None
    success: bool
    message: str
    contour_area: float = 0.0


def apply_morphological_closing(
    edges: np.ndarray,
    kernel_size: int = 5,
) -> np.ndarray:
    if kernel_size <= 0 or kernel_size % 2 == 0:
        raise ValueError("Morphological kernel size must be a positive odd integer.")

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    return cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)


def _is_valid_quadrilateral(approx: np.ndarray, min_area: float) -> bool:
    if approx is None or len(approx) != 4:
        return False

    area = cv2.contourArea(approx)
    if area < min_area:
        return False

    return cv2.isContourConvex(approx)


def find_document_corners(
    edges: np.ndarray,
    image_shape: tuple[int, ...],
    morph_kernel_size: int = 5,
    epsilon_ratio: float = 0.02,
    min_area_ratio: float = 0.05,
) -> DocumentDetectionResult:
    height, width = image_shape[:2]
    image_area = float(height * width)
    min_area = image_area * min_area_ratio

    closed_edges = apply_morphological_closing(edges, kernel_size=morph_kernel_size)

    contours, _ = cv2.findContours(
        closed_edges,
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    if not contours:
        return DocumentDetectionResult(
            corners=None,
            success=False,
            message="No contours found. Ensure the document edges are visible.",
        )

    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        perimeter = cv2.arcLength(contour, True)
        if perimeter <= 0:
            continue

        epsilon = epsilon_ratio * perimeter
        approx = cv2.approxPolyDP(contour, epsilon, True)

        if _is_valid_quadrilateral(approx, min_area):
            corners = approx.reshape(4, 2).astype(np.float32)
            return DocumentDetectionResult(
                corners=corners,
                success=True,
                message="Document detected successfully.",
                contour_area=float(area),
            )

    return DocumentDetectionResult(
        corners=None,
        success=False,
        message=(
            "No valid document quadrilateral found. "
            "Try adjusting Canny thresholds or use a clearer photograph."
        ),
    )


def draw_detection_overlay(
    image: np.ndarray,
    corners: np.ndarray | None,
) -> np.ndarray:
    overlay = image.copy()
    if corners is None:
        return overlay

    pts = corners.astype(np.int32).reshape(-1, 1, 2)
    cv2.polylines(overlay, [pts], isClosed=True, color=(0, 255, 0), thickness=3)

    for i, (x, y) in enumerate(corners.astype(int)):
        cv2.circle(overlay, (int(x), int(y)), 8, (0, 0, 255), -1)
        cv2.putText(
            overlay,
            str(i),
            (int(x) + 10, int(y) - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 0, 0),
            2,
        )

    return overlay
