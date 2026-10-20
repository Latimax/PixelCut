"""Application configuration, defaults, and user settings persistence."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Literal, Optional
from pydantic import BaseModel, Field

from pixelcut_local.storage.paths import get_config_file_path, get_default_export_dir

logger = logging.getLogger(__name__)


class Settings(BaseModel):
    """User-configurable settings persisted to disk."""

    # Model and Inference Settings
    model_name: str = Field(
        default="u2netp",
        description="Default AI model name (e.g. u2netp for fast, u2net for standard quality, isnet-general-use).",
    )
    quality_mode: Literal["fast", "quality"] = Field(
        default="fast",
        description="Preset inference mode: fast (lighter model) or quality (full resolution/standard model).",
    )
    use_alpha_matting: bool = Field(
        default=False,
        description="Whether to apply alpha matting post-processing to soften hair/fur boundaries.",
    )
    prefer_gpu: bool = Field(
        default=False,
        description="Whether to attempt GPU provider if ONNX Runtime detects a compatible CUDA/DirectML backend.",
    )

    # Server Settings
    server_host: str = Field(
        default="127.0.0.1",
        description="IP to bind local server: 127.0.0.1 for localhost only, 0.0.0.0 for LAN access.",
    )
    server_port: int = Field(
        default=8765,
        ge=1024,
        le=65535,
        description="TCP port for local web server and API.",
    )
    lan_mode_enabled: bool = Field(
        default=False,
        description="Whether LAN mode is permitted. Explicit user confirmation required.",
    )
    pairing_token: str = Field(
        default="",
        description="Random security token / PIN required for LAN client authentication.",
    )

    # Export Defaults
    default_export_dir: str = Field(
        default_factory=lambda: str(get_default_export_dir()),
        description="Default folder for saved files.",
    )
    export_format: Literal["PNG", "JPEG", "WEBP"] = Field(
        default="PNG",
        description="Default export format.",
    )
    export_quality: int = Field(
        default=95,
        ge=1,
        le=100,
        description="Default compression quality for JPEG and WebP.",
    )
    naming_template: str = Field(
        default="{original_name}_cutout",
        description="Naming template for exported files. Supported variable: {original_name}.",
    )
    overwrite_policy: Literal["auto_number", "overwrite", "skip"] = Field(
        default="auto_number",
        description="Action when output file already exists: auto_number (safe suffix), overwrite, or skip.",
    )

    # Resource and Safety Limits
    max_upload_mb: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Maximum allowed input image size in megabytes.",
    )
    max_megapixels: int = Field(
        default=40,
        ge=1,
        le=100,
        description="Maximum decoded image size in megapixels to prevent decompression bombs.",
    )
    max_batch_count: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of images queued at once.",
    )
    max_concurrent_jobs: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Maximum simultaneous AI inference tasks (1 recommended for CPU stability).",
    )
    temp_retention_hours: float = Field(
        default=12.0,
        ge=0.5,
        le=168.0,
        description="Hours to keep temporary job files before automatic cleanup.",
    )

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from user JSON file or return defaults.

        Also inspects PIXELCUT_* environment variables for overrides.
        """
        path = get_config_file_path()
        data = {}
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as exc:
                logger.warning("Could not read settings file %s: %s; using defaults", path, exc)

        # Apply environment variable overrides if provided
        if "PIXELCUT_SERVER_HOST" in os.environ:
            data["server_host"] = os.environ["PIXELCUT_SERVER_HOST"]
        if "PIXELCUT_SERVER_PORT" in os.environ:
            try:
                data["server_port"] = int(os.environ["PIXELCUT_SERVER_PORT"])
            except ValueError:
                pass
        if "PIXELCUT_LAN_MODE" in os.environ:
            data["lan_mode_enabled"] = os.environ["PIXELCUT_LAN_MODE"].lower() in ("true", "1", "yes")
        if "PIXELCUT_DEFAULT_MODEL" in os.environ:
            data["model_name"] = os.environ["PIXELCUT_DEFAULT_MODEL"]

        try:
            settings = cls.model_validate(data)
        except Exception as exc:
            logger.warning("Invalid settings data: %s; falling back to default settings", exc)
            settings = cls()

        return settings

    def save(self) -> None:
        """Persist current settings to user JSON file."""
        path = get_config_file_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.model_dump_json(indent=2))
            logger.debug("Settings successfully saved to %s", path)
        except Exception as exc:
            logger.error("Failed to save settings to %s: %s", path, exc)
