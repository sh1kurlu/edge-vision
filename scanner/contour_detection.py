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
    confidence: float = 0.0
    strategy: str = "canny_contour"


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


def _angle_quality(corners: np.ndarray) -> float:
    pts = corners.reshape(4, 2).astype(np.float32)
    scores = []
    for i in range(4):
        p0 = pts[i]
        p1 = pts[(i + 1) % 4]
        p2 = pts[(i + 2) % 4]
        v1 = p0 - p1
        v2 = p2 - p1
        n1 = np.linalg.norm(v1)
        n2 = np.linalg.norm(v2)
        if n1 < 1e-6 or n2 < 1e-6:
            scores.append(0.0)
            continue
        cos_angle = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
        angle = np.degrees(np.arccos(cos_angle))
        scores.append(1.0 - min(abs(angle - 90.0) / 90.0, 1.0))
    return float(np.mean(scores))


def _edge_strength_along_quad(edges: np.ndarray, corners: np.ndarray) -> float:
    mask = np.zeros(edges.shape, dtype=np.uint8)
    pts = corners.astype(np.int32).reshape(-1, 1, 2)
    cv2.polylines(mask, [pts], isClosed=True, color=255, thickness=3)
    edge_pixels = edges[mask > 0]
    if edge_pixels.size == 0:
        return 0.0
    return float(np.mean(edge_pixels) / 255.0)


def compute_detection_confidence(
    corners: np.ndarray,
    image_shape: tuple[int, ...],
    contour_area: float,
    edges: np.ndarray | None = None,
) -> float:
    height, width = image_shape[:2]
    image_area = float(height * width)
    area_ratio = np.clip(contour_area / image_area, 0.0, 1.0)

    rect = cv2.minAreaRect(corners.astype(np.float32))
    box = cv2.boxPoints(rect)
    rect_area = max(cv2.contourArea(box), 1.0)
    rectangularity = np.clip(contour_area / rect_area, 0.0, 1.0)

    angle_score = _angle_quality(corners)
    edge_score = _edge_strength_along_quad(edges, corners) if edges is not None else 0.5

    confidence = (
        0.30 * area_ratio
        + 0.25 * rectangularity
        + 0.25 * angle_score
        + 0.20 * edge_score
    )
    return float(np.clip(confidence * 100.0, 0.0, 100.0))


def _find_quad_from_contours(
    contours: list,
    min_area: float,
    epsilon_ratio: float,
) -> tuple[np.ndarray | None, float]:
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
            return approx.reshape(4, 2).astype(np.float32), float(area)
    return None, 0.0


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
    corners, area = _find_quad_from_contours(contours, min_area, epsilon_ratio)

    if corners is not None:
        confidence = compute_detection_confidence(corners, image_shape, area, closed_edges)
        return DocumentDetectionResult(
            corners=corners,
            success=True,
            message="Document detected successfully.",
            contour_area=area,
            confidence=confidence,
            strategy="canny_contour",
        )

    return DocumentDetectionResult(
        corners=None,
        success=False,
        message=(
            "No valid document quadrilateral found. "
            "Try adjusting Canny thresholds or use a clearer photograph."
        ),
    )


def find_document_corners_adaptive(
    gray: np.ndarray,
    image_shape: tuple[int, ...],
    epsilon_ratio: float = 0.02,
    min_area_ratio: float = 0.05,
) -> DocumentDetectionResult:
    height, width = image_shape[:2]
    image_area = float(height * width)
    min_area = image_area * min_area_ratio

    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    binary = cv2.bitwise_not(binary)
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    corners, area = _find_quad_from_contours(contours, min_area, epsilon_ratio)

    if corners is not None:
        confidence = compute_detection_confidence(corners, image_shape, area, None)
        return DocumentDetectionResult(
            corners=corners,
            success=True,
            message="Document detected via adaptive threshold.",
            contour_area=area,
            confidence=confidence * 0.9,
            strategy="adaptive_threshold",
        )

    return DocumentDetectionResult(
        corners=None,
        success=False,
        message="Adaptive threshold detection failed.",
    )


def find_document_corners_largest_rect(
    edges: np.ndarray,
    image_shape: tuple[int, ...],
    min_area_ratio: float = 0.05,
) -> DocumentDetectionResult:
    height, width = image_shape[:2]
    image_area = float(height * width)
    min_area = image_area * min_area_ratio

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best_corners = None
    best_area = 0.0

    for contour in sorted(contours, key=cv2.contourArea, reverse=True):
        area = cv2.contourArea(contour)
        if area < min_area:
            break
        rect = cv2.minAreaRect(contour)
        box = cv2.boxPoints(rect).astype(np.float32)
        box_area = cv2.contourArea(box)
        if box_area > best_area:
            best_area = box_area
            best_corners = box

    if best_corners is not None:
        confidence = compute_detection_confidence(best_corners, image_shape, best_area, edges)
        return DocumentDetectionResult(
            corners=best_corners,
            success=True,
            message="Document detected via largest rectangle search.",
            contour_area=best_area,
            confidence=confidence * 0.85,
            strategy="largest_rect",
        )

    return DocumentDetectionResult(
        corners=None,
        success=False,
        message="Largest rectangle search failed.",
    )


def find_document_corners_multi(
    gray_blur: np.ndarray,
    edges: np.ndarray,
    closed_edges: np.ndarray,
    image_shape: tuple[int, ...],
    morph_kernel_size: int = 5,
    epsilon_ratio: float = 0.02,
    min_area_ratio: float = 0.05,
) -> DocumentDetectionResult:
    primary = find_document_corners(
        edges, image_shape, morph_kernel_size, epsilon_ratio, min_area_ratio
    )
    if primary.success:
        return primary

    adaptive = find_document_corners_adaptive(
        gray_blur, image_shape, epsilon_ratio, min_area_ratio
    )
    if adaptive.success:
        return adaptive

    return find_document_corners_largest_rect(closed_edges, image_shape, min_area_ratio)


def draw_detection_overlay(
    image: np.ndarray,
    corners: np.ndarray | None,
    contour: np.ndarray | None = None,
) -> np.ndarray:
    overlay = image.copy()
    if corners is None:
        return overlay

    if contour is not None:
        cv2.drawContours(overlay, [contour.astype(np.int32)], -1, (255, 128, 0), 2)

    pts = corners.astype(np.int32).reshape(-1, 1, 2)
    cv2.polylines(overlay, [pts], isClosed=True, color=(0, 255, 128), thickness=3)

    for i, (x, y) in enumerate(corners.astype(int)):
        cv2.circle(overlay, (int(x), int(y)), 10, (0, 128, 255), -1)
        cv2.circle(overlay, (int(x), int(y)), 10, (255, 255, 255), 2)
        cv2.putText(
            overlay,
            str(i),
            (int(x) + 12, int(y) - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 80, 80),
            2,
        )

    return overlay
