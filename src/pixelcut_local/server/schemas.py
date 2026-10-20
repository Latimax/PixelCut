"""Pydantic request and response schemas for PixelCut Local API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    app_name: str = "PixelCut Local"
    version: str = "1.0.0"
    model_ready: bool
    default_model: str
    providers: List[str]


class PublicSettingsResponse(BaseModel):
    max_upload_mb: int
    max_megapixels: int
    default_model: str
    canvas_presets: List[str]
    background_modes: List[str]
    fit_modes: List[str]
    export_formats: List[str]
    lan_mode_enabled: bool


class ModelDetailResponse(BaseModel):
    id: str
    name: str
    description: str
    approx_size_mb: float
    license_type: str
    commercial_cleared: bool
    license_notice: str
    is_downloaded: bool


class CreateJobResponse(BaseModel):
    job_id: str
    status: str
    created_at: float
    message: str = "Job created and queued for processing"


class JobStatusResponse(BaseModel):
    id: str
    original_filename: str
    status: str
    progress: int
    created_at: float
    updated_at: float
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    has_result: bool


class ServerInfoResponse(BaseModel):
    running: bool
    host: str
    port: int
    lan_mode_enabled: bool
    lan_ip: Optional[str] = None
    lan_url: Optional[str] = None
    localhost_url: str
