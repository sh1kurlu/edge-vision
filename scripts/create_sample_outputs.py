#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scanner.pipeline import DocumentScanner
from utils.image_utils import load_image

EXAMPLES = ROOT / "examples"
OUTPUT = EXAMPLES / "outputs"
ASSETS = ROOT / "assets"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)

    scanner = DocumentScanner()
    sample = EXAMPLES / "02_angle_25.jpg"
    if not sample.exists():
        print("Run generate_examples.py first.")
        return

    image = load_image(sample)
    result = scanner.scan(image)

    if result.success and result.enhanced is not None:
        cv2.imwrite(str(OUTPUT / "02_angle_25_scanned.png"), result.enhanced)

    if result.detection_overlay is not None:
        cv2.imwrite(str(OUTPUT / "02_angle_25_detection.png"), result.detection_overlay)

    if result.enhanced is not None:
        h = 400
        orig = cv2.resize(image, (int(image.shape[1] * h / image.shape[0]), h))
        proc = cv2.resize(result.enhanced, (int(result.enhanced.shape[1] * h / result.enhanced.shape[0]), h))
        pad = np.ones((h, 20, 3), dtype=np.uint8) * 40
        combined = np.hstack([orig, pad, proc])
        cv2.imwrite(str(ASSETS / "screenshot_placeholder.png"), combined)
        print(f"Created {ASSETS / 'screenshot_placeholder.png'}")


if __name__ == "__main__":
    main()
