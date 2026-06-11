from __future__ import annotations

import cv2
import numpy as np


def detect_edges(
    preprocessed: np.ndarray,
    lower_threshold: int = 75,
    upper_threshold: int = 200,
    aperture_size: int = 3,
) -> np.ndarray:
    if lower_threshold < 0 or upper_threshold < 0:
        raise ValueError("Canny thresholds must be non-negative.")

    if lower_threshold >= upper_threshold:
        raise ValueError("Lower Canny threshold must be less than upper threshold.")

    return cv2.Canny(
        preprocessed,
        lower_threshold,
        upper_threshold,
        apertureSize=aperture_size,
    )
