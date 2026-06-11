#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scanner.pipeline import DocumentScanner
from utils.image_utils import load_image

EXAMPLES_DIR = ROOT / "examples"
REPORT_PATH = ROOT / "benchmark_results.json"


def run_benchmark() -> dict:
    scanner = DocumentScanner()
    image_paths = sorted(EXAMPLES_DIR.glob("*.jpg")) + sorted(EXAMPLES_DIR.glob("*.png"))

    if not image_paths:
        print("No example images found. Run: python scripts/generate_examples.py")
        return {"images": [], "summary": {}}

    results = []
    successes = 0
    perspective_ok = 0
    total_time = 0.0

    print(f"\n{'Image':<30} {'Detect':<8} {'Persp.':<8} {'Time (s)':<10} Message")
    print("-" * 80)

    for path in image_paths:
        try:
            image = load_image(path)
            result = scanner.scan(image)
            detected = result.success
            persp = result.perspective_success
            elapsed = result.elapsed_seconds

            if detected:
                successes += 1
            if persp:
                perspective_ok += 1
            total_time += elapsed

            row = {
                "image": path.name,
                "detection_success": detected,
                "perspective_success": persp,
                "processing_time_seconds": round(elapsed, 4),
                "message": result.message,
            }
            results.append(row)

            print(
                f"{path.name:<30} "
                f"{'YES' if detected else 'NO':<8} "
                f"{'YES' if persp else 'NO':<8} "
                f"{elapsed:<10.3f} "
                f"{result.message[:40]}"
            )
        except Exception as exc:
            results.append({
                "image": path.name,
                "detection_success": False,
                "perspective_success": False,
                "processing_time_seconds": 0,
                "message": str(exc),
            })
            print(f"{path.name:<30} ERROR    ERROR    0.000      {exc}")

    n = len(results)
    summary = {
        "total_images": n,
        "detection_success_count": successes,
        "detection_success_rate": round(successes / n * 100, 1) if n else 0,
        "perspective_success_count": perspective_ok,
        "perspective_success_rate": round(perspective_ok / n * 100, 1) if n else 0,
        "average_processing_time_seconds": round(total_time / n, 4) if n else 0,
        "total_processing_time_seconds": round(total_time, 4),
    }

    print("-" * 80)
    print(f"Detection success:   {successes}/{n} ({summary['detection_success_rate']}%)")
    print(f"Perspective success: {perspective_ok}/{n} ({summary['perspective_success_rate']}%)")
    print(f"Average time:        {summary['average_processing_time_seconds']}s")

    report = {"images": results, "summary": summary}
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    print(f"\nResults saved to {REPORT_PATH}")

    return report


if __name__ == "__main__":
    run_benchmark()
