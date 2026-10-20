"""Unit tests for exporting PNG, JPEG flattening, naming templates, overwrite rules, and ZIP."""

from __future__ import annotations

import zipfile
from pathlib import Path
from PIL import Image
import pytest

from pixelcut_local.core.export import (
    export_image,
    export_images_to_zip,
    generate_safe_output_path,
)


def test_export_png_preserves_alpha(sample_rgba_image, tmp_path):
    dest = tmp_path / "output.png"
    export_image(sample_rgba_image, dest, format_name="PNG")
    assert dest.exists()

    with Image.open(dest) as exported:
        assert exported.mode == "RGBA"
        assert exported.getpixel((0, 0))[3] == 0  # alpha preserved


def test_export_jpeg_flattens_transparency(sample_rgba_image, tmp_path):
    dest = tmp_path / "output.jpg"
    export_image(sample_rgba_image, dest, format_name="JPEG", matte_color=(255, 255, 255))
    assert dest.exists()

    with Image.open(dest) as exported:
        assert exported.mode == "RGB"
        # Flattened corner should be white matte
        r, g, b = exported.getpixel((0, 0))
        assert r == 255 and g == 255 and b == 255


def test_generate_safe_output_path_auto_number(tmp_path):
    # Existing file
    existing = tmp_path / "photo_cutout.png"
    existing.write_text("dummy")

    path, is_skipped = generate_safe_output_path(
        output_dir=tmp_path,
        original_filename="photo.jpg",
        naming_template="{original_name}_cutout",
        extension=".png",
        overwrite_policy="auto_number",
    )
    assert not is_skipped
    assert path.name == "photo_cutout_1.png"


def test_generate_safe_output_path_skip(tmp_path):
    existing = tmp_path / "test_cutout.png"
    existing.write_text("dummy")

    path, is_skipped = generate_safe_output_path(
        output_dir=tmp_path,
        original_filename="test.png",
        naming_template="{original_name}_cutout",
        extension=".png",
        overwrite_policy="skip",
    )
    assert is_skipped


def test_export_images_to_zip(sample_rgba_image, tmp_path):
    zip_dest = tmp_path / "archive.zip"
    items = [(sample_rgba_image, "item1.png"), (sample_rgba_image, "item2.png")]
    export_images_to_zip(items, zip_dest, format_name="PNG")

    assert zip_dest.exists()
    with zipfile.ZipFile(zip_dest, "r") as zf:
        namelist = zf.namelist()
        assert "item1.png" in namelist
        assert "item2.png" in namelist
