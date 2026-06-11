# Parameter Validation Checklist

Every visible GUI control is wired into the processing pipeline. Run automated verification:

```bash
python scripts/validate_parameters.py
```

Debug logging prints active values on every scan (console + `edgevision.processing` logger):

```
Processing:
  Canny Lower = 75
  Canny Upper = 200
  Morph Kernel = 5
  Enhancement = Adaptive Threshold
  CLAHE = False
  ...
```

---

## Validation Table

| Parameter Name | GUI Control | Data Flow | OpenCV Function | Verification Status |
|----------------|-------------|-----------|-----------------|---------------------|
| Canny Lower Threshold | `LabeledSlider` `canny_lower` | `_build_config()` → `ScanConfig.canny_lower` → `detect_edges()` | `cv2.Canny(lower_threshold=...)` | **VERIFIED** — Edge Detection tab changes measurably |
| Canny Upper Threshold | `LabeledSlider` `canny_upper` | `_build_config()` → `ScanConfig.canny_upper` → `detect_edges()` | `cv2.Canny(upper_threshold=...)` | **VERIFIED** — Edge Detection tab changes measurably |
| Morphological Kernel Size | `LabeledSlider` `morph_kernel` | `_build_config()` → `ScanConfig.morph_kernel_size` → `apply_morphological_closing()` | `cv2.morphologyEx(..., MORPH_CLOSE, kernel)` | **VERIFIED** — Morphology tab changes measurably |
| Enhancement Mode | `QComboBox` `enhancement_mode` | `_build_config()` → `ScanConfig.enhancement_mode` → `enhance_document()` | `cv2.adaptiveThreshold` / `cv2.threshold(OTSU)` / pass-through | **VERIFIED** — Final Enhanced Scan tab changes measurably |
| CLAHE | `QCheckBox` `chk_clahe` | `_build_config()` → `PreprocessOptions.use_clahe` → `apply_clahe()` | `cv2.createCLAHE().apply()` | **VERIFIED** — Grayscale tab changes when enabled |
| Bilateral Filter | `QCheckBox` `chk_bilateral` | `_build_config()` → `PreprocessOptions.use_bilateral` → `apply_bilateral_filter()` | `cv2.bilateralFilter()` | **VERIFIED** — Preprocessed grayscale changes when enabled |
| Shadow Reduction | `QCheckBox` `chk_shadow` | `_build_config()` → `PreprocessOptions.use_shadow_reduction` → `apply_shadow_reduction()` | `cv2.dilate` / `cv2.medianBlur` / `cv2.normalize` | **VERIFIED** — Grayscale tab changes when enabled |
| Multi-Strategy Detection | `QCheckBox` `chk_multi` | `_build_config()` → `ScanConfig.multi_strategy` → `find_document_corners_multi()` vs `find_document_corners()` | Contour fallback chain | **VERIFIED** — Affects detection strategy when primary fails |
| Corner Refinement | `QCheckBox` `chk_refine` | `_build_config()` → `ScanConfig.refine_corners` → `refine_corners()` | `cv2.cornerSubPix()` | **VERIFIED** — Sub-pixel corner adjustment before warp |

---

## Data Flow Summary

```
GUI Widget
    ↓  valueChanged / stateChanged (400 ms debounce)
MainWindow._build_config()
    ↓  ScanConfig (deep-copied to worker thread)
ScanWorker.run() → DocumentScanner.config
    ↓
pipeline.scan()
    ├─ preprocess()           ← PreprocessOptions (CLAHE, bilateral, shadow)
    ├─ detect_edges()       ← canny_lower, canny_upper
    ├─ apply_morphological_closing()  ← morph_kernel_size
    ├─ find_document_corners*()       ← morph_kernel_size (on closed edges)
    ├─ refine_corners()       ← refine_corners flag
    └─ enhance_document()     ← enhancement_mode
```

---

## Non-Processing Controls (intentionally not in pipeline)

| Control | Purpose |
|---------|---------|
| Show Detection Overlay | Display only — selects overlay image in Pipeline tab |
| Reset Comparison | Display only — resets comparison divider position |
| Export Original Resolution | Export path — full-res scan on save when checked |
| Upload / Save | File I/O |

---

## Manual Visual Verification

1. Upload `examples/02_angle_25.jpg`
2. Open **Pipeline → Edge Detection** — move Canny Lower from 75 to 20 → edges increase
3. Open **Pipeline → Morphology** — move Morph Kernel from 5 to 21 → closing width changes
4. Switch Enhancement to **Otsu** → **Final Enhanced Scan** binarization changes
5. Enable **CLAHE** → **Grayscale** contrast changes
6. Check console for `Processing:` log block matching GUI values
