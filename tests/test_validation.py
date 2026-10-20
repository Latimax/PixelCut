"""Unit tests for image validation, size limits, corrupt files, and security."""

from __future__ import annotations

import io
from PIL import Image
import pytest

from pixelcut_local.core.validation import ImageValidationError, validate_image_file


def test_validate_valid_image(sample_image_bytes):
    w, h, fmt = validate_image_file(sample_image_bytes)
    assert w == 128
    assert h == 128
    assert fmt.upper() == "PNG"


def test_validate_empty_bytes():
    with pytest.raises(ImageValidationError) as exc_info:
        validate_image_file(b"")
    assert "empty" in str(exc_info.value).lower()


def test_validate_corrupt_data():
    corrupt_bytes = b"NOT_A_REAL_IMAGE_DATA_12345678"
    with pytest.raises(ImageValidationError) as exc_info:
        validate_image_file(corrupt_bytes)
    assert exc_info.value.code == "CORRUPT_OR_UNSUPPORTED"


def test_validate_file_too_large():
    # Test rejecting payload larger than limit
    dummy = b"0" * (2 * 1024 * 1024)
    with pytest.raises(ImageValidationError) as exc_info:
        validate_image_file(dummy, max_mb=1)
    assert exc_info.value.code == "FILE_TOO_LARGE"


def test_validate_decompression_bomb_megapixels():
    # Create image that claims huge dimensions
    large_img = Image.new("RGB", (2000, 2000))
    buf = io.BytesIO()
    large_img.save(buf, format="PNG")
    # Set limit to 2 megapixels (2000x2000 is 4 megapixels)
    with pytest.raises(ImageValidationError) as exc_info:
        validate_image_file(buf.getvalue(), max_megapixels=2)
    assert "exceeds" in str(exc_info.value).lower()
