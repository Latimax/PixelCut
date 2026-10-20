"""Unit tests for background removal model registry, provider queries, and inference."""

from __future__ import annotations

import pytest

from pixelcut_local.core.models import (
    MODEL_REGISTRY,
    get_available_execution_providers,
    is_model_downloaded,
)


def test_model_registry_entries():
    assert "u2netp" in MODEL_REGISTRY
    assert "u2net" in MODEL_REGISTRY
    assert "isnet-general-use" in MODEL_REGISTRY
    assert "bria-rmbg" in MODEL_REGISTRY

    # Check that licenses are documented
    for m in MODEL_REGISTRY.values():
        assert m.license_type
        assert m.license_notice
        assert m.approx_size_mb > 0


def test_execution_providers_contains_cpu():
    providers = get_available_execution_providers()
    assert "CPUExecutionProvider" in providers
