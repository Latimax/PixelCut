"""Unit tests for MaskEditor brush painting, edge filtering, and undo/redo."""

from __future__ import annotations

from PIL import Image
import numpy as np
import pytest

from pixelcut_local.core.mask_refinement import MaskEditor


@pytest.fixture
def mask_editor(sample_rgb_image):
    # Initial mask with 0 in top half, 255 in bottom half
    mask = Image.new("L", (128, 128), 0)
    for y in range(64, 128):
        for x in range(128):
            mask.putpixel((x, y), 255)
    return MaskEditor(sample_rgb_image, mask)


def test_brush_paint_keep(mask_editor):
    assert mask_editor.current_mask.getpixel((10, 10)) == 0

    # Paint keep (255) at (10, 10)
    mask_editor.apply_brush_stroke([(10, 10)], radius=5, mode="keep")
    assert mask_editor.current_mask.getpixel((10, 10)) == 255
    assert mask_editor.can_undo


def test_brush_paint_remove(mask_editor):
    assert mask_editor.current_mask.getpixel((10, 100)) == 255

    # Paint remove (0) at (10, 100)
    mask_editor.apply_brush_stroke([(10, 100)], radius=5, mode="remove")
    assert mask_editor.current_mask.getpixel((10, 100)) == 0


def test_undo_redo_stack(mask_editor):
    initial_val = mask_editor.current_mask.getpixel((20, 20))
    mask_editor.apply_brush_stroke([(20, 20)], radius=5, mode="keep")
    assert mask_editor.current_mask.getpixel((20, 20)) == 255

    # Undo
    assert mask_editor.undo()
    assert mask_editor.current_mask.getpixel((20, 20)) == initial_val
    assert mask_editor.can_redo

    # Redo
    assert mask_editor.redo()
    assert mask_editor.current_mask.getpixel((20, 20)) == 255


def test_mask_overlay(mask_editor):
    overlay = mask_editor.get_mask_overlay()
    assert overlay.size == mask_editor.original_image.size
    assert overlay.mode == "RGBA"
