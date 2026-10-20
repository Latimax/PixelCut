"""Image validation, decompression-bomb checks, and corrupt-image detection."""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Tuple, Union
from PIL import Image

from pixelcut_local.core.constants import (
    OPTIONAL_INPUT_EXTENSIONS,
    SUPPORTED_INPUT_EXTENSIONS,
)

logger = logging.getLogger(__name__)


class ImageValidationError(Exception):
    """User-facing validation error with clean actionable description."""

    def __init__(self, message: str, code: str = "INVALID_IMAGE"):
        super().__init__(message)
        self.message = message
        self.code = code


def validate_image_file(
    file_source: Union[str, Path, bytes, io.BytesIO],
    max_mb: int = 25,
    max_megapixels: int = 40,
    filename_hint: str = "",
) -> Tuple[int, int, str]:
    """Validate image file size, integrity, and dimensions.

    Returns (width, height, format_name).
    Raises ImageValidationError if file is invalid or unsafe.
    """
    # 1. Check byte size if reading from path
    raw_bytes: bytes = b""
    path_obj: Union[Path, None] = None

    if isinstance(file_source, (str, Path)):
        path_obj = Path(file_source)
        filename_hint = filename_hint or path_obj.name
        if not path_obj.exists():
            raise ImageValidationError(f"File not found: {path_obj.name}", code="FILE_NOT_FOUND")
        
        file_size_bytes = path_obj.stat().st_size
        if file_size_bytes == 0:
            raise ImageValidationError("File is empty (0 bytes).", code="EMPTY_FILE")
        if file_size_bytes > max_mb * 1024 * 1024:
            raise ImageValidationError(
                f"File size ({file_size_bytes / (1024 * 1024):.1f} MB) exceeds maximum allowed limit of {max_mb} MB.",
                code="FILE_TOO_LARGE",
            )
        try:
            with open(path_obj, "rb") as f:
                raw_bytes = f.read()
        except Exception as exc:
            raise ImageValidationError(f"Could not read file: {exc}", code="READ_ERROR")
    elif isinstance(file_source, io.BytesIO):
        raw_bytes = file_source.getvalue()
    elif isinstance(file_source, bytes):
        raw_bytes = file_source
    else:
        raise ImageValidationError("Unsupported image source type.", code="INVALID_SOURCE")

    if len(raw_bytes) == 0:
        raise ImageValidationError("Image data is empty.", code="EMPTY_FILE")

    if len(raw_bytes) > max_mb * 1024 * 1024:
        raise ImageValidationError(
            f"Image payload ({len(raw_bytes) / (1024 * 1024):.1f} MB) exceeds limit of {max_mb} MB.",
            code="FILE_TOO_LARGE",
        )

    # 2. Check extension hint for special unsupported formats like HEIC
    if filename_hint:
        ext = Path(filename_hint).suffix.lower()
        if ext in OPTIONAL_INPUT_EXTENSIONS:
            # Check if pillow-heif or similar is installed
            try:
                import pillow_heif  # noqa: F401
            except ImportError:
                raise ImageValidationError(
                    f"HEIC/HEIF images ({ext}) require the optional 'pillow-heif' decoder, which is not installed. "
                    "Please convert the file to PNG or JPEG first.",
                    code="UNSUPPORTED_HEIC",
                )

    # 3. Configure Pillow DecompressionBomb protections
    max_pixels = max_megapixels * 1_000_000
    Image.MAX_IMAGE_PIXELS = max_pixels

    # 4. Open and decode verification
    try:
        bio = io.BytesIO(raw_bytes)
        with Image.open(bio) as img:
            fmt = img.format or "UNKNOWN"
            width, height = img.size

            if width <= 0 or height <= 0:
                raise ImageValidationError(
                    f"Invalid image dimensions: {width}x{height}",
                    code="INVALID_DIMENSIONS",
                )

            pixel_count = width * height
            if pixel_count > max_pixels:
                raise ImageValidationError(
                    f"Image resolution ({width}x{height} = {pixel_count / 1_000_000:.1f} MP) "
                    f"exceeds maximum allowed limit of {max_megapixels} megapixels.",
                    code="DECOMPRESSION_BOMB_LIMIT",
                )

            # Fully decode pixel raster to ensure image is not corrupt/truncated
            img.load()

            return width, height, fmt
    except Image.DecompressionBombError:
        raise ImageValidationError(
            f"Image exceeds safe decompression limits ({max_megapixels} MP). Decompression aborted for security.",
            code="DECOMPRESSION_BOMB",
        )
    except ImageValidationError:
        raise
    except Exception as exc:
        logger.debug("Image decode failure: %s", exc)
        raise ImageValidationError(
            "The file could not be decoded as a valid image. It may be corrupt or an unsupported format.",
            code="CORRUPT_OR_UNSUPPORTED",
        )
