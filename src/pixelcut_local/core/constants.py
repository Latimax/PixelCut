"""Constants, presets, and enums for PixelCut Local."""

from __future__ import annotations
from typing import Dict, Tuple

SUPPORTED_INPUT_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}

OPTIONAL_INPUT_EXTENSIONS = {
    ".heic",
    ".heif",
}

# Aspect Ratio Presets (width_ratio, height_ratio)
CANVAS_PRESETS: Dict[str, Tuple[Optional[int], Optional[int]]] = {
    "original": (None, None),
    "1:1 (Square)": (1, 1),
    "4:5 (Portrait)": (4, 5),
    "3:4 (Portrait)": (3, 4),
    "9:16 (Story/Reel)": (9, 16),
    "16:9 (Landscape)": (16, 9),
    "4:3 (Landscape)": (4, 3),
}

BACKGROUND_MODES = ["transparent", "solid", "gradient", "image"]
FIT_MODES = ["cover", "contain", "stretch"]
EXPORT_FORMATS = ["PNG", "JPEG", "WEBP"]

JOB_STATUS_QUEUED = "queued"
JOB_STATUS_VALIDATING = "validating"
JOB_STATUS_LOADING_MODEL = "loading_model"
JOB_STATUS_PROCESSING = "processing"
JOB_STATUS_COMPOSITING = "compositing"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"
JOB_STATUS_CANCELLED = "cancelled"
