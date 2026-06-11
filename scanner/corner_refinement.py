from __future__ import annotations

import cv2
import numpy as np


def refine_corners(gray: np.ndarray, corners: np.ndarray, window_size: int = 5) -> np.ndarray:
    if corners is None or len(corners) != 4:
        return corners

    ws = max(window_size, 3)
    if ws % 2 == 0:
        ws += 1

    pts = corners.reshape(-1, 1, 2).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.1)
    refined = cv2.cornerSubPix(gray, pts, (ws, ws), (-1, -1), criteria)
    return refined.reshape(4, 2).astype(np.float32)
