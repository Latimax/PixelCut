"""Paths and directory resolution for PixelCut Local.

Handles path resolution for both standard development execution and
PyInstaller one-folder / one-file frozen executables.
User data and mutable caches are stored in the user's AppData directory
so that the application never writes to read-only installation directories.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """Return True if running inside a PyInstaller frozen bundle."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_bundle_dir() -> Path:
    """Get the base directory where application code and bundled resources live.

    In development: the repository root or package parent.
    In PyInstaller: sys._MEIPASS or directory containing executable.
    """
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))
    # In source development: parent of src/pixelcut_local
    return Path(__file__).resolve().parent.parent.parent.parent


def get_package_dir() -> Path:
    """Get the pixelcut_local package directory."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS")) / "pixelcut_local"
    return Path(__file__).resolve().parent.parent


def get_static_dir() -> Path:
    """Get the web static directory for the mobile web client."""
    pkg_dir = get_package_dir()
    static_candidate = pkg_dir / "server" / "static"
    if static_candidate.exists():
        return static_candidate
    
    # Fallback to bundle root / server / static
    bundle_candidate = get_bundle_dir() / "src" / "pixelcut_local" / "server" / "static"
    if bundle_candidate.exists():
        return bundle_candidate

    return static_candidate


def get_user_data_dir() -> Path:
    """Get the per-user data directory for config, logs, and caches.

    On Windows: %APPDATA%/PixelCutLocal
    Fallback: ~/.pixelcut_local
    """
    appdata = os.environ.get("APPDATA")
    if appdata:
        base = Path(appdata) / "PixelCutLocal"
    else:
        base = Path.home() / ".pixelcut_local"
    
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_logs_dir() -> Path:
    """Get the directory where rotating log files are saved."""
    d = get_user_data_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_temp_jobs_dir() -> Path:
    """Get the managed temporary directory for job uploads and intermediate files."""
    d = get_user_data_dir() / "temp_jobs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_models_dir() -> Path:
    """Get the directory where downloaded AI model weights are cached."""
    # Rembg by default uses U2NET_HOME env var or ~/.u2net.
    # We set U2NET_HOME to our user data models folder if not explicitly set.
    custom = os.environ.get("U2NET_HOME")
    if custom:
        p = Path(custom)
        p.mkdir(parents=True, exist_ok=True)
        return p
    d = get_user_data_dir() / "models"
    d.mkdir(parents=True, exist_ok=True)
    # Ensure U2NET_HOME points here
    os.environ.setdefault("U2NET_HOME", str(d))
    return d


def get_default_export_dir() -> Path:
    """Get the default user export directory (Pictures/PixelCut or user data)."""
    user_pictures = Path.home() / "Pictures" / "PixelCut"
    try:
        user_pictures.mkdir(parents=True, exist_ok=True)
        return user_pictures
    except Exception:
        fallback = get_user_data_dir() / "exports"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def get_config_file_path() -> Path:
    """Get the path to the user's persistent settings JSON file."""
    return get_user_data_dir() / "settings.json"
