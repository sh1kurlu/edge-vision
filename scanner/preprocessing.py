from __future__ import annotations

import cv2
import numpy as np


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


def preprocess(
    image: np.ndarray,
    blur_kernel: tuple[int, int] = (5, 5),
) -> np.ndarray:
    gray = to_grayscale(image)
    return apply_gaussian_blur(gray, kernel_size=blur_kernel)
