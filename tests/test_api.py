"""API endpoint and security tests for FastAPI server."""

from __future__ import annotations

import io
from fastapi.testclient import TestClient
import pytest

from pixelcut_local.config import Settings


def test_health_endpoint(test_client: TestClient):
    resp = test_client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "default_model" in data


def test_public_settings_endpoint(test_client: TestClient):
    resp = test_client.get("/api/v1/settings/public")
    assert resp.status_code == 200
    data = resp.json()
    assert "max_upload_mb" in data
    assert "canvas_presets" in data
    assert "background_modes" in data


def test_models_endpoint(test_client: TestClient):
    resp = test_client.get("/api/v1/models")
    assert resp.status_code == 200
    models = resp.json()
    assert isinstance(models, list)
    assert any(m["id"] == "u2netp" for m in models)


def test_server_info_endpoint(test_client: TestClient):
    resp = test_client.get("/api/v1/server-info")
    assert resp.status_code == 200
    info = resp.json()
    assert "running" in info
    assert "localhost_url" in info


def test_create_and_fetch_job(test_client: TestClient, sample_image_bytes):
    # Post job with multipart file
    files = {"file": ("test.png", sample_image_bytes, "image/png")}
    data = {"bg_mode": "solid", "solid_color": "#ff0000"}

    resp = test_client.post("/api/v1/jobs", files=files, data=data)
    assert resp.status_code == 202
    created = resp.json()
    job_id = created["job_id"]
    assert job_id

    # Query status
    status_resp = test_client.get(f"/api/v1/jobs/{job_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["id"] == job_id


def test_nonexistent_job_returns_404(test_client: TestClient):
    resp = test_client.get("/api/v1/jobs/nonexistent-uuid-1234")
    assert resp.status_code == 404


def test_path_traversal_protection(test_client: TestClient):
    resp = test_client.get("/api/v1/jobs/../../etc/passwd")
    assert resp.status_code in (404, 422)


def test_lan_mode_rejection_without_token(test_client: TestClient, monkeypatch):
    # Emulate LAN mode enabled with pairing token set
    settings = Settings.load()
    settings.lan_mode_enabled = True
    settings.pairing_token = "SECRET_PIN_123"
    monkeypatch.setattr(Settings, "load", lambda: settings)

    # Make request simulating non-localhost client IP
    headers = {"X-Forwarded-For": "192.168.1.50"}
    # Note: TestClient by default connects as "testclient", which is verified in verify_client_access
    resp = test_client.get("/api/v1/jobs/test-id", headers={"x-pairing-token": "WRONG_TOKEN"})
    assert resp.status_code == 401
