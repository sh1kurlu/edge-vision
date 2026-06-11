#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scanner.enhancement import EnhancementMode
from scanner.pipeline import DocumentScanner, ScanConfig
from scanner.preprocessing import PreprocessOptions
from utils.image_utils import load_image

IMAGE = ROOT / "examples" / "02_angle_25.jpg"


def _diff_ratio(a: np.ndarray, b: np.ndarray) -> float:
    if a is None or b is None:
        return 1.0
    if a.shape != b.shape:
        return 1.0
    return float(np.mean(a != b))


def _scan(config: ScanConfig):
    scanner = DocumentScanner(config)
    scanner.invalidate_cache()
    return scanner.scan(load_image(IMAGE), use_cache=False)


def main() -> int:
    if not IMAGE.exists():
        print("Run: python scripts/generate_examples.py")
        return 1

    base = ScanConfig()
    r_base = _scan(base)
    assert r_base.success and r_base.stages is not None

    tests: list[tuple[str, ScanConfig, str, float]] = []

    cfg = ScanConfig(canny_lower=20, canny_upper=80)
    r = _scan(cfg)
    tests.append(("Canny Lower/Upper", cfg, "stages.edges", _diff_ratio(r_base.stages.edges, r.stages.edges)))

    cfg = ScanConfig(morph_kernel_size=15)
    r = _scan(cfg)
    tests.append(("Morph Kernel", cfg, "stages.morphology", _diff_ratio(r_base.stages.morphology, r.stages.morphology)))

    cfg = ScanConfig(enhancement_mode=EnhancementMode.OTSU)
    r = _scan(cfg)
    tests.append(("Enhancement Otsu", cfg, "enhanced", _diff_ratio(r_base.enhanced, r.enhanced)))

    cfg = ScanConfig(enhancement_mode=EnhancementMode.NONE)
    r = _scan(cfg)
    tests.append(("Enhancement None", cfg, "enhanced", _diff_ratio(r_base.enhanced, r.enhanced)))

    cfg = ScanConfig(preprocess_options=PreprocessOptions(use_clahe=True))
    r = _scan(cfg)
    tests.append(("CLAHE", cfg, "stages.grayscale", _diff_ratio(r_base.stages.grayscale, r.stages.grayscale)))

    cfg = ScanConfig(preprocess_options=PreprocessOptions(use_bilateral=True))
    r = _scan(cfg)
    tests.append(("Bilateral", cfg, "stages.preprocessed", _diff_ratio(r_base.stages.preprocessed, r.stages.preprocessed)))

    cfg = ScanConfig(preprocess_options=PreprocessOptions(use_shadow_reduction=True))
    r = _scan(cfg)
    tests.append(("Shadow Reduction", cfg, "stages.grayscale", _diff_ratio(r_base.stages.grayscale, r.stages.grayscale)))

    print(f"\n{'Parameter':<22} {'Stage':<22} {'Diff Ratio':<12} {'Status'}")
    print("-" * 70)
    failed = 0
    for name, cfg, stage, ratio in tests:
        ok = ratio > 0.001
        status = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"{name:<22} {stage:<22} {ratio:<12.4f} {status}")

    print("-" * 70)
    if failed:
        print(f"{failed} parameter test(s) failed.")
        return 1
    print("All parameter connections verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
