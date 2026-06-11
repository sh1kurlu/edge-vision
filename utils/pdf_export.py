from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

try:
    import img2pdf
except ImportError:
    img2pdf = None


def save_as_pdf(image: np.ndarray, path: str | Path) -> None:
    if img2pdf is None:
        raise RuntimeError("img2pdf is not installed. Install with: pip install img2pdf")

    path = Path(path)
    if path.suffix.lower() != ".pdf":
        raise ValueError("PDF export path must end with .pdf")

    if image is None or image.size == 0:
        raise ValueError("No image to export.")

    if len(image.shape) == 2:
        encode_img = image
    else:
        encode_img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    success, buffer = cv2.imencode(".png", encode_img)
    if not success:
        raise ValueError("Failed to encode image for PDF export.")

    pdf_bytes = img2pdf.convert(buffer.tobytes())
    path.write_bytes(pdf_bytes)
