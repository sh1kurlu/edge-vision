#!/usr/bin/env python3

from __future__ import annotations

import copy
import sys
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QMetaObject, QObject, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scanner.enhancement import EnhancementMode
from scanner.pipeline import DocumentScanner, ScanConfig, ScanResult
from utils.image_utils import load_image, resize_for_preview

IMAGE = ROOT / "examples" / "02_angle_25.jpg"
SCAN_COUNT = 60


class ScanWorker(QObject):
    finished = Signal(int, object)

    def __init__(self) -> None:
        super().__init__()
        self._image: np.ndarray | None = None
        self._config: ScanConfig | None = None
        self._generation = 0

    def prepare(self, image: np.ndarray, config: ScanConfig, generation: int) -> None:
        self._image = image
        self._config = copy.deepcopy(config)
        self._generation = generation

    @Slot()
    def run(self) -> None:
        cv2.setNumThreads(1)
        assert self._image is not None and self._config is not None
        scanner = DocumentScanner(self._config)
        result = scanner.scan(self._image, use_cache=True)
        self.finished.emit(self._generation, result)


class RescanHarness(QObject):
    def __init__(self, image: np.ndarray) -> None:
        super().__init__()
        self._full_image = image
        self._preview_image, _ = resize_for_preview(image, 1200)
        self._thread = QThread(self)
        self._worker = ScanWorker()
        self._worker.moveToThread(self._thread)
        self._worker.finished.connect(self._on_scan_finished)
        self._thread.start()
        print("[EdgeVision] THREAD CREATED", flush=True)

        self._processing = False
        self._generation = 0
        self._completed = 0
        self._errors: list[str] = []
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(50)
        self._debounce.timeout.connect(self._schedule_scan)

        self._configs = self._build_config_sequence()

    def _build_config_sequence(self) -> list[ScanConfig]:
        configs: list[ScanConfig] = []
        canny_pairs = [(5, 50), (250, 400), (75, 200), (120, 300)]
        morph_sizes = [3, 31, 5, 15, 21]
        modes = [EnhancementMode.ADAPTIVE, EnhancementMode.OTSU, EnhancementMode.NONE]

        for i in range(SCAN_COUNT):
            lower, upper = canny_pairs[i % len(canny_pairs)]
            morph = morph_sizes[i % len(morph_sizes)]
            mode = modes[i % len(modes)]
            configs.append(
                ScanConfig(
                    canny_lower=lower,
                    canny_upper=upper,
                    morph_kernel_size=morph,
                    enhancement_mode=mode,
                    preview_max_dimension=1200,
                )
            )
        return configs

    def start(self) -> None:
        self._generation = 1
        self._schedule_scan()

    def _schedule_scan(self) -> None:
        if self._processing:
            self._debounce.start()
            return

        if self._completed >= SCAN_COUNT:
            self._thread.quit()
            self._thread.wait(3000)
            print("[EdgeVision] THREAD FINISHED", flush=True)
            self._thread = None
            print("[EdgeVision] THREAD CLEANED UP", flush=True)
            QApplication.instance().quit()
            return

        self._processing = True
        generation = self._generation
        config = self._configs[self._completed]
        print(f"[EdgeVision] SCAN STARTED (generation={generation})", flush=True)

        self._worker.prepare(self._preview_image, config, generation)
        QMetaObject.invokeMethod(self._worker, "run", Qt.ConnectionType.QueuedConnection)

    def _on_scan_finished(self, generation: int, result: ScanResult) -> None:
        print(f"[EdgeVision] SCAN COMPLETED (generation={generation})", flush=True)
        self._processing = False

        if generation != self._generation:
            self._debounce.start()
            return

        if not result.success or result.stages is None:
            self._errors.append(f"scan {self._completed} failed: {result.message}")

        self._completed += 1
        self._generation += 1
        self._debounce.start()

    def report(self) -> int:
        if self._errors:
            print("\nStress test FAILED:")
            for err in self._errors[:10]:
                print(f"  - {err}")
            if len(self._errors) > 10:
                print(f"  ... and {len(self._errors) - 10} more")
            return 1
        print(f"\nStress test PASSED: {SCAN_COUNT} rescans, no thread errors.")
        return 0


def _diff_ratio(a: np.ndarray | None, b: np.ndarray | None) -> float:
    if a is None or b is None:
        return 1.0
    if a.shape != b.shape:
        return 1.0
    return float(np.mean(a != b))


def _extreme_diff_tests(image: np.ndarray) -> int:
    scanner = DocumentScanner()
    preview, _ = resize_for_preview(image, 1200)
    failed = 0

    def scan(cfg: ScanConfig) -> ScanResult:
        scanner.config = cfg
        scanner.invalidate_cache()
        return scanner.scan(preview, use_cache=False)

    base = scan(ScanConfig(canny_lower=75, canny_upper=200, morph_kernel_size=5))
    assert base.success and base.stages is not None

    a = scan(ScanConfig(canny_lower=5, canny_upper=50, morph_kernel_size=5))
    b = scan(ScanConfig(canny_lower=250, canny_upper=400, morph_kernel_size=5))
    edge_diff = _diff_ratio(a.stages.edges, b.stages.edges)
    print(f"Canny extreme edge diff: {edge_diff:.4f}")
    if edge_diff <= 0.001:
        print("FAIL: Canny extreme values did not change edge output")
        failed += 1

    m3 = scan(ScanConfig(morph_kernel_size=3))
    m31 = scan(ScanConfig(morph_kernel_size=31))
    morph_diff = _diff_ratio(m3.stages.morphology, m31.stages.morphology)
    print(f"Morph 3 vs 31 diff: {morph_diff:.4f}")
    if morph_diff <= 0.001:
        print("FAIL: Morph kernel extreme values did not change morphology output")
        failed += 1

    adapt = scan(ScanConfig(enhancement_mode=EnhancementMode.ADAPTIVE))
    otsu = scan(ScanConfig(enhancement_mode=EnhancementMode.OTSU))
    none = scan(ScanConfig(enhancement_mode=EnhancementMode.NONE))
    adapt_otsu = _diff_ratio(adapt.enhanced, otsu.enhanced)
    adapt_none = _diff_ratio(adapt.enhanced, none.enhanced)
    print(f"Adaptive vs Otsu final diff: {adapt_otsu:.4f}")
    print(f"Adaptive vs None final diff: {adapt_none:.4f}")
    if adapt_otsu <= 0.001 or adapt_none <= 0.001:
        print("FAIL: Enhancement modes did not change final output")
        failed += 1

    return failed


def main() -> int:
    if not IMAGE.exists():
        print("Run: python scripts/generate_examples.py")
        return 1

    image = load_image(IMAGE)
    extreme_failures = _extreme_diff_tests(image)
    if extreme_failures:
        return 1

    app = QApplication(sys.argv)
    harness = RescanHarness(image)
    harness.start()
    exit_code = app.exec()
    return harness.report() if exit_code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
