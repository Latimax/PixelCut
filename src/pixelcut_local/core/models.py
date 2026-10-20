"""AI model metadata, license notices, and execution provider detection."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import onnxruntime as ort

from pixelcut_local.storage.paths import get_models_dir

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelInfo:
    """Metadata and license details for a background removal model."""

    id: str
    name: str
    description: str
    approx_size_mb: float
    license_type: str
    commercial_cleared: bool
    license_notice: str
    weight_filename: str
    recommended_mode: str  # "fast" or "quality"


MODEL_REGISTRY: Dict[str, ModelInfo] = {
    "u2netp": ModelInfo(
        id="u2netp",
        name="U2-Net Light (Fast)",
        description="Lightweight and fast portrait/object cutout model. Best for fast CPU batch workflows.",
        approx_size_mb=4.7,
        license_type="Apache-2.0",
        commercial_cleared=True,
        license_notice="Apache License 2.0. Permitted for commercial use and redistribution with attribution.",
        weight_filename="u2netp.onnx",
        recommended_mode="fast",
    ),
    "u2net": ModelInfo(
        id="u2net",
        name="U2-Net Standard (Quality)",
        description="Full-sized U2-Net model providing high-quality edge segmentation on general subjects.",
        approx_size_mb=176.3,
        license_type="Apache-2.0",
        commercial_cleared=True,
        license_notice="Apache License 2.0. Permitted for commercial use and redistribution with attribution.",
        weight_filename="u2net.onnx",
        recommended_mode="quality",
    ),
    "isnet-general-use": ModelInfo(
        id="isnet-general-use",
        name="DIS IS-Net (High Precision)",
        description="Dichotomous Image Segmentation model trained for fine hair, fur, and intricate boundaries.",
        approx_size_mb=174.5,
        license_type="Apache-2.0",
        commercial_cleared=True,
        license_notice="Apache License 2.0. Permitted for commercial use with attribution.",
        weight_filename="isnet-general-use.onnx",
        recommended_mode="quality",
    ),
    "bria-rmbg": ModelInfo(
        id="bria-rmbg",
        name="BRIA RMBG (Research Only)",
        description="State of the art edge segmentation model from BRIA AI.",
        approx_size_mb=176.0,
        license_type="Non-Commercial Creative Commons / BRIA Agreement",
        commercial_cleared=False,
        license_notice="ATTENTION: BRIA model weights are restricted to non-commercial research use only. "
                       "Commercial deployment requires an explicit commercial agreement with BRIA AI.",
        weight_filename="bria-rmbg.onnx",
        recommended_mode="quality",
    ),
}


def get_available_execution_providers() -> List[str]:
    """Return all execution providers available in current ONNX Runtime installation."""
    try:
        return ort.get_available_providers()
    except Exception as exc:
        logger.warning("Could not query ONNX Runtime execution providers: %s", exc)
        return ["CPUExecutionProvider"]


def is_gpu_available() -> bool:
    """Check if any hardware acceleration provider (CUDA, DirectML, TensorRT) is available."""
    providers = get_available_execution_providers()
    gpu_providers = {"CUDAExecutionProvider", "DmlExecutionProvider", "TensorrtExecutionProvider", "ROCMExecutionProvider"}
    return any(p in gpu_providers for p in providers)


def get_model_file_path(model_id: str) -> Optional[Path]:
    """Return path to downloaded model weights if present locally."""
    info = MODEL_REGISTRY.get(model_id)
    if not info:
        return None

    models_dir = get_models_dir()
    candidate = models_dir / info.weight_filename
    if candidate.exists() and candidate.stat().st_size > 1000:
        return candidate

    # Also check user home .u2net directory (default rembg cache)
    u2net_home = Path.home() / ".u2net" / info.weight_filename
    if u2net_home.exists() and u2net_home.stat().st_size > 1000:
        return u2net_home

    return None


def is_model_downloaded(model_id: str) -> bool:
    """Check whether model weight file is cached locally."""
    return get_model_file_path(model_id) is not None
