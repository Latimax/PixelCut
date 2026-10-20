"""Background removal engine and ONNX session management."""

from __future__ import annotations

import logging
import threading
from typing import Dict, Optional, Tuple
from PIL import Image
import numpy as np

# rembg imports
from rembg import new_session, remove
from rembg.session_factory import BaseSession

from pixelcut_local.core.models import (
    MODEL_REGISTRY,
    get_available_execution_providers,
    is_gpu_available,
)

logger = logging.getLogger(__name__)

# Session cache: key=(model_name, provider_str) -> BaseSession
_SESSION_CACHE: Dict[Tuple[str, str], BaseSession] = {}
_SESSION_LOCK = threading.Lock()


class BackgroundRemovalError(Exception):
    """User-facing error raised when inference or model initialization fails."""

    def __init__(self, message: str, code: str = "INFERENCE_FAILED"):
        super().__init__(message)
        self.message = message
        self.code = code


def get_inference_session(
    model_name: str = "u2netp",
    prefer_gpu: bool = False,
) -> BaseSession:
    """Retrieve or initialize a cached ONNX inference session for the given model.

    Reuses sessions across batch jobs so the weights are not re-read from disk
    for each processed image.
    """
    if model_name not in MODEL_REGISTRY:
        logger.warning("Model '%s' not recognized in registry; using 'u2netp'", model_name)
        model_name = "u2netp"

    # Determine providers
    providers = ["CPUExecutionProvider"]
    provider_key = "CPU"

    if prefer_gpu and is_gpu_available():
        avail = get_available_execution_providers()
        # Prefer CUDA or DirectML if available
        gpu_cands = [p for p in avail if p != "CPUExecutionProvider"]
        if gpu_cands:
            providers = gpu_cands + ["CPUExecutionProvider"]
            provider_key = gpu_cands[0]

    cache_key = (model_name, provider_key)

    with _SESSION_LOCK:
        if cache_key in _SESSION_CACHE:
            return _SESSION_CACHE[cache_key]

        logger.info(
            "Initializing ONNX session for model '%s' with providers: %s",
            model_name,
            providers,
        )

        try:
            session = new_session(model_name=model_name, providers=providers)
            _SESSION_CACHE[cache_key] = session
            return session
        except Exception as exc:
            # If GPU failed, attempt fallback to CPUExecutionProvider
            if provider_key != "CPU":
                logger.warning("GPU session failed (%s); attempting fallback to CPU...", exc)
                try:
                    cpu_session = new_session(
                        model_name=model_name,
                        providers=["CPUExecutionProvider"],
                    )
                    _SESSION_CACHE[(model_name, "CPU")] = cpu_session
                    return cpu_session
                except Exception as cpu_exc:
                    raise BackgroundRemovalError(
                        f"Failed to load AI model '{model_name}': {cpu_exc}. "
                        "Please verify your network connection if downloading weights on first run.",
                        code="MODEL_LOAD_FAILED",
                    ) from cpu_exc

            raise BackgroundRemovalError(
                f"Failed to load AI model '{model_name}': {exc}. "
                "Check your internet connection if weights need to be downloaded.",
                code="MODEL_LOAD_FAILED",
            ) from exc


def clear_session_cache() -> None:
    """Clear cached inference sessions to free memory."""
    with _SESSION_LOCK:
        _SESSION_CACHE.clear()
        logger.info("Cleared model inference session cache.")


def remove_background(
    image: Image.Image,
    model_name: str = "u2netp",
    use_alpha_matting: bool = False,
    prefer_gpu: bool = False,
    session: Optional[BaseSession] = None,
) -> Tuple[Image.Image, Image.Image]:
    """Execute background removal on a PIL Image.

    Returns:
        A tuple of (rgba_cutout, alpha_mask):
        - rgba_cutout: Image in 'RGBA' mode with the transparent background.
        - alpha_mask: Grayscale Image in 'L' mode representing the 8-bit alpha matte (0-255).
    """
    orig_w, orig_h = image.size

    # Ensure input image is RGBA or RGB
    if image.mode not in ("RGB", "RGBA"):
        input_image = image.convert("RGBA")
    else:
        input_image = image

    # Get or reuse session
    if session is None:
        session = get_inference_session(model_name=model_name, prefer_gpu=prefer_gpu)

    try:
        # Perform removal
        cutout = remove(
            input_image,
            session=session,
            alpha_matting=use_alpha_matting,
            alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10,
            alpha_matting_erode_size=10,
            post_process_mask=True,
        )

        # Ensure output is RGBA
        if cutout.mode != "RGBA":
            cutout = cutout.convert("RGBA")

        # Preserve original dimensions if model altered them
        if cutout.size != (orig_w, orig_h):
            cutout = cutout.resize((orig_w, orig_h), Image.Resampling.LANCZOS)

        # Extract alpha mask
        alpha_channel = cutout.split()[3]  # mode 'L'

        return cutout, alpha_channel
    except Exception as exc:
        logger.error("Background removal inference error: %s", exc)
        raise BackgroundRemovalError(
            f"Background removal failed: {exc}",
            code="INFERENCE_EXECUTION_ERROR",
        ) from exc
