from __future__ import annotations

from enum import Enum

import cv2
import numpy as np

from scanner.preprocessing import to_grayscale


class EnhancementMode(str, Enum):
    ADAPTIVE = "adaptive"
    OTSU = "otsu"
    NONE = "none"


def enhance_document(
    image: np.ndarray,
    mode: EnhancementMode = EnhancementMode.ADAPTIVE,
    block_size: int = 11,
    c_constant: int = 2,
) -> np.ndarray:
    if mode == EnhancementMode.NONE:
        if len(image.shape) == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        return image.copy()

    gray = to_grayscale(image)

    if mode == EnhancementMode.ADAPTIVE:
        bs = block_size if block_size % 2 == 1 else block_size + 1
        bs = max(bs, 3)
        enhanced = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            bs,
            c_constant,
        )
    elif mode == EnhancementMode.OTSU:
        _, enhanced = cv2.threshold(
            gray,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )
    else:
        raise ValueError(f"Unknown enhancement mode: {mode}")

    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
