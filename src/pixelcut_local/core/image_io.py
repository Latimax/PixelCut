"""Image loading, EXIF orientation correction, color conversion, and thumbnails."""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Union
from PIL import Image, ImageOps

from pixelcut_local.core.validation import validate_image_file

logger = logging.getLogger(__name__)


def load_image(
    source: Union[str, Path, bytes, io.BytesIO],
    ensure_rgba: bool = True,
    max_mb: int = 25,
    max_megapixels: int = 40,
) -> Image.Image:
    """Load an image, validate it, apply EXIF orientation transpose, and normalize mode.

    If ensure_rgba is True, converts to 'RGBA'. Otherwise, converts to 'RGB' or 'RGBA'.
    """
    validate_image_file(source, max_mb=max_mb, max_megapixels=max_megapixels)

    raw_bytes: bytes
    if isinstance(source, (str, Path)):
        with open(source, "rb") as f:
            raw_bytes = f.read()
    elif isinstance(source, io.BytesIO):
        raw_bytes = source.getvalue()
    elif isinstance(source, bytes):
        raw_bytes = source
    else:
        raise ValueError("Invalid image source type")

    # Open from bytes
    image = Image.open(io.BytesIO(raw_bytes))

    # Apply EXIF rotation if tag exists
    try:
        transposed = ImageOps.exif_transpose(image)
        if transposed is not None:
            image = transposed
    except Exception as exc:
        logger.debug("EXIF transposition skipped: %s", exc)

    # Normalize image mode safely
    mode = image.mode
    if ensure_rgba:
        if mode != "RGBA":
            if mode == "RGB":
                image = image.convert("RGBA")
            elif mode == "P":
                # Palette image might have transparency
                image = image.convert("RGBA")
            elif mode in ("L", "LA", "1"):
                image = image.convert("RGBA")
            elif mode == "CMYK":
                # Convert CMYK to RGB first to avoid color distortion
                image = image.convert("RGB").convert("RGBA")
            else:
                image = image.convert("RGBA")
    else:
        if mode not in ("RGB", "RGBA"):
            if mode == "CMYK":
                image = image.convert("RGB")
            elif mode in ("P", "L", "1"):
                image = image.convert("RGB")
            else:
                image = image.convert("RGB")

    return image


def create_thumbnail(image: Image.Image, max_size: tuple[int, int] = (256, 256)) -> Image.Image:
    """Generate a high-quality thumbnail preserving aspect ratio."""
    thumb = image.copy()
    thumb.thumbnail(max_size, Image.Resampling.LANCZOS)
    return thumb


def image_to_png_bytes(image: Image.Image) -> bytes:
    """Encode an image to PNG bytes."""
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
