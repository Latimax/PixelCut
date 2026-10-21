"""Pytest test fixtures providing synthetic test images and API client."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from PIL import Image, ImageDraw
import pytest
from fastapi.testclient import TestClient

# Ensure src is on sys.path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from pixelcut_local.config import Settings
from pixelcut_local.server.app import create_app


@pytest.fixture
def sample_rgba_image() -> Image.Image:
    """Create a 128x128 synthetic RGBA image with a circular cutout subject."""
    img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Draw green circle in center
    draw.ellipse([32, 32, 96, 96], fill=(34, 197, 94, 255))
    return img


@pytest.fixture
def sample_rgb_image() -> Image.Image:
    """Create a 128x128 synthetic RGB image with red subject on white background."""
    img = Image.new("RGB", (128, 128), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([32, 32, 96, 96], fill=(239, 68, 68))
    return img


@pytest.fixture
def sample_image_bytes(sample_rgb_image) -> bytes:
    """Bytes of a valid PNG image."""
    buf = io.BytesIO()
    sample_rgb_image.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def sample_image_file(tmp_path, sample_rgb_image) -> Path:
    """Save a sample image to a temporary file path."""
    p = tmp_path / "test_sample.png"
    sample_rgb_image.save(p, format="PNG")
    return p


@pytest.fixture(autouse=True)
def isolate_test_settings(monkeypatch):
    """Ensure all tests run against clean default settings without side-effects from disk."""
    clean = Settings()
    monkeypatch.setattr(Settings, "load", lambda: clean)


@pytest.fixture
def test_client() -> TestClient:
    """FastAPI TestClient fixture."""
    app = create_app()
    return TestClient(app)

