# Document Scanner

A production-quality desktop application that automatically detects, extracts, rectifies, and enhances documents from photographs taken under challenging real-world conditions.

Built entirely in Python using classical computer vision (OpenCV) and PySide6.

![Before and After Scan](assets/screenshot_placeholder.png)

---

## Features

- **Desktop GUI** — Upload, preview, scan, and save with intuitive controls
- **Robust detection** — Handles perspective distortion, rotation, shadows, noise, blur, and complex backgrounds
- **Classical CV pipeline** — Canny edges → morphological closing → contour detection → Douglas–Peucker quadrilateral selection
- **Perspective correction** — Flat, top-down document view via homography
- **Enhancement modes** — Adaptive thresholding (scanner-like) or Otsu thresholding
- **Export formats** — PNG, JPG, and single-page PDF
- **Configurable parameters** — Canny thresholds, morphological kernel, enhancement mode

---

## Installation

### Prerequisites

- Python 3.10 or newer
- macOS, Windows, or Linux

### Setup

```bash
cd document_scanner
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Or use the install script (uses the smaller PySide6 Essentials package):

```bash
chmod +x scripts/install_dependencies.sh
./scripts/install_dependencies.sh
```

### Generate Test Images (optional)

```bash
python scripts/generate_examples.py
```

### Run the Application

```bash
python main.py
```

### Run Benchmarks

```bash
python scripts/benchmark.py
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| opencv-python | Image processing, Canny, contours, perspective transform |
| numpy | Array operations |
| Pillow | Fallback image loading |
| PySide6 | Desktop GUI |
| img2pdf | Single-page PDF export |

---

## Usage Guide

1. **Launch** the application with `python main.py`.
2. Click **Upload Image** and select a JPG, JPEG, PNG, or BMP file.
3. Adjust **Canny thresholds** or **morph kernel** if detection fails on difficult images.
4. Select an **Enhancement** mode (Adaptive recommended for uneven lighting).
5. Click **Scan Document** to run the pipeline.
6. Review the original (left) and scanned result (right).
7. Click **Save Result** to export as PNG, JPG, or PDF.

### Tips for Best Results

- Ensure document edges are visible against the background.
- Avoid extreme motion blur; mild blur is handled.
- For low-contrast images, lower the Canny lower threshold (e.g., 50).
- For noisy images, increase the morphological kernel size (e.g., 7).

---

## Pipeline Explanation

```
Input Image
    │
    ▼
[1] Load (preserve resolution)
    │
    ▼
[2] Preprocess — Grayscale + Gaussian Blur (5×5)
    │
    ▼
[3] Canny Edge Detection (configurable thresholds)
    │
    ▼
[4] Morphological Closing — connect broken edges
    │
    ▼
[5] Contour Detection — RETR_LIST, CHAIN_APPROX_SIMPLE
    │
    ▼
[6] Douglas–Peucker Approximation — select largest 4-vertex quad
    │                              (NOT Convex Hull — see report)
    ▼
[7] Perspective Transform — getPerspectiveTransform + warpPerspective
    │
    ▼
[8] Enhancement — Adaptive or Otsu thresholding
    │
    ▼
Scanned Output
```

### Why Douglas–Peucker over Convex Hull?

Convex Hull ignores concavities and can include background clutter. Douglas–Peucker (`cv2.approxPolyDP`) better approximates rectangular document boundaries and is the standard approach in document scanning applications.

---

## Project Structure

```
document_scanner/
├── main.py
├── gui/
│   ├── main_window.py
│   └── widgets.py
├── scanner/
│   ├── preprocessing.py
│   ├── edge_detection.py
│   ├── contour_detection.py
│   ├── perspective.py
│   ├── enhancement.py
│   └── pipeline.py
├── utils/
│   ├── image_utils.py
│   └── pdf_export.py
├── scripts/
│   ├── generate_examples.py
│   └── benchmark.py
├── assets/
├── examples/
├── requirements.txt
├── README.md
└── TECHNICAL_REPORT.md
```

---

## Example Outputs

Sample outputs are included in `examples/outputs/`:

| Input | Output |
|-------|--------|
| `examples/02_angle_25.jpg` | `examples/outputs/02_angle_25_scanned.png` |
| Detection overlay | `examples/outputs/02_angle_25_detection.png` |

Regenerate with:

```bash
python scripts/create_sample_outputs.py
```

Benchmark JSON is written to `benchmark_results.json` after running `python scripts/benchmark.py`.

---

## Benchmark Summary

Run `python scripts/benchmark.py` after generating examples. Typical results on synthetic test images:

| Metric | Typical Value |
|--------|---------------|
| Detection success rate | ~90–100% |
| Perspective correction rate | ~90–100% |
| Average processing time | 0.05–0.3s per image (CPU) |

See `TECHNICAL_REPORT.md` Section 6 for detailed per-image results.

---

## Packaging with PyInstaller

Create a standalone executable:

```bash
pip install pyinstaller

# macOS / Linux
pyinstaller --name DocumentScanner \
  --windowed \
  --add-data "assets:assets" \
  main.py

# Windows (use semicolon separator)
pyinstaller --name DocumentScanner ^
  --windowed ^
  --add-data "assets;assets" ^
  main.py
```

The executable appears in `dist/DocumentScanner/`.

### Notes

- On macOS, you may need `--osx-bundle-identifier com.documentscanner.app`
- Test the built app with images from `examples/`
- If OpenCV fails to load, add `--hidden-import=cv2`


