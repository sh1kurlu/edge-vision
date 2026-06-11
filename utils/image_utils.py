from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
MIN_IMAGE_DIMENSION = 32


def is_supported_format(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def validate_image(image: np.ndarray) -> None:
    if image is None:
        raise ValueError("No image loaded. Please upload an image first.")

    if not isinstance(image, np.ndarray):
        raise ValueError("Invalid image data.")

    if image.size == 0:
        raise ValueError("Image is empty or corrupted.")

    if len(image.shape) < 2:
        raise ValueError("Image has invalid dimensions.")

    height, width = image.shape[:2]
    if height < MIN_IMAGE_DIMENSION or width < MIN_IMAGE_DIMENSION:
        raise ValueError(
            f"Image too small for processing (minimum {MIN_IMAGE_DIMENSION}x"
            f"{MIN_IMAGE_DIMENSION} pixels)."
        )


def resize_for_preview(image: np.ndarray, max_dimension: int) -> tuple[np.ndarray, float]:
    height, width = image.shape[:2]
    longest = max(height, width)
    if longest <= max_dimension:
        return image.copy(), 1.0

    scale = max_dimension / longest
    new_w = int(width * scale)
    new_h = int(height * scale)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized, scale


def scale_corners_to_full(corners: np.ndarray, scale: float) -> np.ndarray:
    if scale >= 1.0 or scale <= 0:
        return corners.copy()
    return (corners / scale).astype(np.float32)


def load_image(path: str | Path) -> np.ndarray:
    path = Path(path)

    if not path.exists():
        raise ValueError(f"File not found: {path}")

    if not is_supported_format(path):
        raise ValueError(
            f"Unsupported file format '{path.suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is not None and image.size > 0:
        validate_image(image)
        return image

    try:
        with Image.open(path) as pil_img:
            pil_img = pil_img.convert("RGB")
            rgb = np.array(pil_img)
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            validate_image(bgr)
            return bgr
    except Exception as exc:
        raise ValueError(f"Could not load image (corrupted or invalid): {exc}") from exc


def save_image(image: np.ndarray, path: str | Path) -> None:
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix not in {".png", ".jpg", ".jpeg"}:
        raise ValueError(f"Unsupported save format: {suffix}")

    if image is None or image.size == 0:
        raise ValueError("No image to save.")

    if not cv2.imwrite(str(path), image):
        raise ValueError(f"Failed to save image to {path}")


def numpy_to_qimage_rgb(image: np.ndarray):
    from PySide6.QtGui import QImage

    if image is None or image.size == 0:
        return QImage()

    if len(image.shape) == 2:
        h, w = image.shape
        bytes_per_line = w
        qimage = QImage(image.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
        return qimage.copy()

    if len(image.shape) == 3 and image.shape[2] == 3:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qimage = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return qimage.copy()

    raise ValueError(f"Unsupported image shape for display: {image.shape}")


def gray_to_bgr(gray: np.ndarray) -> np.ndarray:
    if len(gray.shape) == 2:
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    return gray
