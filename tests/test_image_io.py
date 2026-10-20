"""Unit tests for image loading, color conversion, and thumbnails."""

from __future__ import annotations

import io
from PIL import Image
import pytest

from pixelcut_local.core.image_io import create_thumbnail, load_image


def test_load_image_converts_to_rgba(sample_image_file):
    img = load_image(sample_image_file, ensure_rgba=True)
    assert img.mode == "RGBA"
    assert img.size == (128, 128)


def test_load_cmyk_image(tmp_path):
    cmyk_img = Image.new("CMYK", (64, 64), (100, 50, 0, 0))
    p = tmp_path / "test_cmyk.jpg"
    cmyk_img.save(p, format="JPEG")

    loaded = load_image(p, ensure_rgba=True)
    assert loaded.mode == "RGBA"
    assert loaded.size == (64, 64)


def test_create_thumbnail(sample_rgb_image):
    thumb = create_thumbnail(sample_rgb_image, max_size=(32, 32))
    assert thumb.width <= 32
    assert thumb.height <= 32
