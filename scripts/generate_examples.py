#!/usr/bin/env python3

from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def _make_document_content(width: int = 600, height: int = 800) -> np.ndarray:
    page = np.ones((height, width, 3), dtype=np.uint8) * 245

    cv2.rectangle(page, (40, 40), (width - 40, height - 40), (200, 200, 200), 2)
    cv2.putText(page, "DOCUMENT SCANNER TEST", (80, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (30, 30, 30), 2)

    for i, y in enumerate(range(180, height - 100, 35)):
        line_w = width - 120 - (i % 3) * 40
        cv2.line(page, (80, y), (80 + line_w, y), (60, 60, 60), 2)

    cv2.putText(page, "Sample paragraph for OCR testing.", (80, height - 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 40, 40), 1)
    return page


def _warp_perspective(doc: np.ndarray, angle_deg: float, scale: float = 0.7) -> np.ndarray:
    h, w = doc.shape[:2]
    canvas = np.random.randint(80, 140, (900, 1200, 3), dtype=np.uint8)

    src = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]])

    cx, cy = 600, 450
    rad = math.radians(angle_deg)
    offset_x = int(200 * math.cos(rad))
    offset_y = int(150 * math.sin(rad))

    dst = np.float32([
        [cx - w * scale // 2 + offset_x, cy - h * scale // 2],
        [cx + w * scale // 2 + offset_x // 2, cy - h * scale // 2 - offset_y // 3],
        [cx + w * scale // 2, cy + h * scale // 2 + offset_y // 2],
        [cx - w * scale // 2 - offset_x // 3, cy + h * scale // 2],
    ])

    matrix = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(doc, matrix, (canvas.shape[1], canvas.shape[0]),
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
    mask = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY) > 10
    canvas[mask] = warped[mask]
    return canvas


def _add_shadow(img: np.ndarray, strength: float = 0.4) -> np.ndarray:
    h, w = img.shape[:2]
    shadow = np.zeros((h, w), dtype=np.float32)
    cv2.ellipse(shadow, (w // 3, h // 2), (w // 2, h), 0, 0, 360, 1.0, -1)
    shadow = cv2.GaussianBlur(shadow, (101, 101), 0)
    result = img.astype(np.float32)
    for c in range(3):
        result[:, :, c] *= 1.0 - shadow * strength
    return np.clip(result, 0, 255).astype(np.uint8)


def _add_noise(img: np.ndarray, sigma: float = 12) -> np.ndarray:
    noise = np.random.normal(0, sigma, img.shape).astype(np.float32)
    return np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def _add_blur(img: np.ndarray, k: int = 5) -> np.ndarray:
    return cv2.GaussianBlur(img, (k, k), 0)


def _low_contrast(img: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.normalize(l, None, 80, 200, cv2.NORM_MINMAX)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


def generate_all() -> list[Path]:
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    doc = _make_document_content()
    configs = [
        ("01_straight.jpg", lambda d: _warp_perspective(d, 5)),
        ("02_angle_25.jpg", lambda d: _warp_perspective(d, 25)),
        ("03_angle_neg20.jpg", lambda d: _warp_perspective(d, -20)),
        ("04_shadow.jpg", lambda d: _add_shadow(_warp_perspective(d, 15))),
        ("05_low_contrast.jpg", lambda d: _low_contrast(_warp_perspective(d, 18))),
        ("06_noise.jpg", lambda d: _add_noise(_warp_perspective(d, 12))),
        ("07_blur.jpg", lambda d: _add_blur(_warp_perspective(d, 10))),
        ("08_shadow_noise.jpg", lambda d: _add_noise(_add_shadow(_warp_perspective(d, 22)))),
        ("09_complex_bg.jpg", lambda d: _warp_perspective(d, 30, scale=0.55)),
        ("10_steep_angle.jpg", lambda d: _warp_perspective(d, 35)),
        ("11_mild_blur_shadow.jpg", lambda d: _add_blur(_add_shadow(_warp_perspective(d, 8)), 3)),
        ("12_heavy_noise.jpg", lambda d: _add_noise(_warp_perspective(d, -15), sigma=20)),
    ]

    paths = []
    for name, transform in configs:
        img = transform(doc.copy())
        path = EXAMPLES_DIR / name
        cv2.imwrite(str(path), img)
        paths.append(path)
        print(f"Created {path}")

    return paths


if __name__ == "__main__":
    generate_all()
