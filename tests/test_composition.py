"""Unit tests for background generation, foreground transforms, effects, and composition."""

from __future__ import annotations

from PIL import Image
import numpy as np
import pytest

from pixelcut_local.core.composition import (
    composite_image,
    compute_canvas_dimensions,
    create_checkerboard_pattern,
    create_gradient_background,
    create_solid_background,
    fit_background_image,
    generate_drop_shadow,
    generate_outline,
)


def test_create_solid_background():
    bg = create_solid_background(100, 80, "#FF0000")
    assert bg.size == (100, 80)
    assert bg.mode == "RGBA"
    # Center pixel should be red
    r, g, b, a = bg.getpixel((50, 40))
    assert r == 255 and g == 0 and b == 0 and a == 255


def test_create_gradient_background():
    grad = create_gradient_background(100, 100, (255, 0, 0), (0, 0, 255), angle_degrees=0.0)
    assert grad.size == (100, 100)
    assert grad.mode == "RGBA"


def test_fit_background_image_modes():
    src_bg = Image.new("RGB", (200, 100), (50, 100, 150))
    
    # Cover
    bg_cover = fit_background_image(src_bg, 100, 100, fit_mode="cover")
    assert bg_cover.size == (100, 100)

    # Contain
    bg_contain = fit_background_image(src_bg, 100, 100, fit_mode="contain")
    assert bg_contain.size == (100, 100)

    # Stretch
    bg_stretch = fit_background_image(src_bg, 100, 100, fit_mode="stretch")
    assert bg_stretch.size == (100, 100)


def test_canvas_presets():
    orig_size = (800, 600)
    # 1:1
    w, h = compute_canvas_dimensions(orig_size, preset="1:1 (Square)")
    assert w == h == 800

    # 16:9
    w, h = compute_canvas_dimensions(orig_size, preset="16:9 (Landscape)")
    assert abs((w / h) - (16 / 9)) < 0.05


def test_composite_image_transparent(sample_rgba_image):
    result = composite_image(sample_rgba_image, bg_mode="transparent")
    assert result.size == sample_rgba_image.size
    assert result.mode == "RGBA"
    # Corner pixel must remain transparent (0 alpha)
    assert result.getpixel((0, 0))[3] == 0
    # Center circle pixel must remain opaque (255 alpha)
    assert result.getpixel((64, 64))[3] == 255


def test_composite_image_solid_color(sample_rgba_image):
    result = composite_image(sample_rgba_image, bg_mode="solid", solid_color="#0000FF")
    assert result.size == sample_rgba_image.size
    # Corner pixel should have the solid blue background with full alpha
    r, g, b, a = result.getpixel((0, 0))
    assert b == 255 and a == 255


def test_generate_effects(sample_rgba_image):
    # Test shadow
    shadow_img = generate_drop_shadow(sample_rgba_image, opacity=0.5)
    assert shadow_img.size == sample_rgba_image.size

    # Test outline
    outline_img = generate_outline(sample_rgba_image, outline_width=4)
    assert outline_img.size == sample_rgba_image.size
