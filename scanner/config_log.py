from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from scanner.enhancement import EnhancementMode

if TYPE_CHECKING:
    from scanner.pipeline import ScanConfig

logger = logging.getLogger("edgevision.processing")

_ENHANCEMENT_LABELS = {
    EnhancementMode.ADAPTIVE: "Adaptive Threshold",
    EnhancementMode.OTSU: "Otsu Threshold",
    EnhancementMode.NONE: "No Enhancement",
}


def format_active_config(config: ScanConfig) -> str:
    opts = config.preprocess_options
    enhancement = _ENHANCEMENT_LABELS.get(
        config.enhancement_mode,
        str(config.enhancement_mode),
    )
    lines = [
        "Processing:",
        f"  Canny Lower = {config.canny_lower}",
        f"  Canny Upper = {config.canny_upper}",
        f"  Morph Kernel = {config.morph_kernel_size}",
        f"  Enhancement = {enhancement}",
        f"  CLAHE = {opts.use_clahe}",
        f"  Bilateral Filter = {opts.use_bilateral}",
        f"  Shadow Reduction = {opts.use_shadow_reduction}",
        f"  Multi-Strategy Detection = {config.multi_strategy}",
        f"  Corner Refinement = {config.refine_corners}",
    ]
    return "\n".join(lines)


def log_active_config(config: ScanConfig) -> None:
    text = format_active_config(config)
    logger.info("\n%s", text)
    print(text, flush=True)
