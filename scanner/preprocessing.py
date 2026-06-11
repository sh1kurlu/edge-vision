from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class PreprocessOptions:
    use_clahe: bool = False
    use_bilateral: bool = False
    use_shadow_reduction: bool = False
    clahe_clip_limit: float = 2.0
    clahe_grid_size: int = 8
    bilateral_d: int = 9
    bilateral_sigma_color: float = 75.0
    bilateral_sigma_space: float = 75.0


def to_grayscale(image: np.ndarray) -> np.ndarray:
    if image is None or image.size == 0:
        raise ValueError("Cannot preprocess an empty image.")

    if len(image.shape) == 2:
        return image.copy()

    if len(image.shape) == 3 and image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if len(image.shape) == 3 and image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)

    raise ValueError(f"Unsupported image shape: {image.shape}")


def apply_gaussian_blur(
    gray: np.ndarray,
    kernel_size: tuple[int, int] = (5, 5),
    sigma_x: float = 0,
) -> np.ndarray:
    kx, ky = kernel_size
    if kx <= 0 or ky <= 0 or kx % 2 == 0 or ky % 2 == 0:
        raise ValueError("Gaussian kernel size must be positive and odd.")

    return cv2.GaussianBlur(gray, (kx, ky), sigma_x)


def apply_clahe(gray: np.ndarray, clip_limit: float = 2.0, grid_size: int = 8) -> np.ndarray:
    grid = max(grid_size, 2)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid, grid))
    return clahe.apply(gray)


def apply_bilateral_filter(
    gray: np.ndarray,
    d: int = 9,
    sigma_color: float = 75.0,
    sigma_space: float = 75.0,
) -> np.ndarray:
    return cv2.bilateralFilter(gray, d, sigma_color, sigma_space)


def apply_shadow_reduction(gray: np.ndarray) -> np.ndarray:
    dilated = cv2.dilate(gray, np.ones((7, 7), np.uint8))
    bg = cv2.medianBlur(dilated, 21)
    diff = 255 - cv2.absdiff(gray, bg)
    return cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)


def apply_optional_preprocessing(gray: np.ndarray, options: PreprocessOptions) -> np.ndarray:
    result = gray.copy()
    if options.use_shadow_reduction:
        result = apply_shadow_reduction(result)
    if options.use_clahe:
        result = apply_clahe(result, options.clahe_clip_limit, options.clahe_grid_size)
    if options.use_bilateral:
        result = apply_bilateral_filter(
            result,
            options.bilateral_d,
            options.bilateral_sigma_color,
            options.bilateral_sigma_space,
        )
    return result


def preprocess(
    image: np.ndarray,
    blur_kernel: tuple[int, int] = (5, 5),
    options: PreprocessOptions | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    gray = to_grayscale(image)
    if options is not None:
        gray = apply_optional_preprocessing(gray, options)
    blurred = apply_gaussian_blur(gray, kernel_size=blur_kernel)
    return gray, blurred
