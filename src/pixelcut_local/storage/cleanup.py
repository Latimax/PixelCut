"""Temporary file cleanup and retention manager."""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

from pixelcut_local.storage.paths import get_temp_jobs_dir

logger = logging.getLogger(__name__)


def cleanup_expired_jobs(max_age_hours: float = 12.0) -> int:
    """Remove job directories older than max_age_hours.

    Returns the number of cleaned job directories.
    """
    temp_dir = get_temp_jobs_dir()
    if not temp_dir.exists():
        return 0

    now = time.time()
    cutoff = now - (max_age_hours * 3600.0)
    cleaned_count = 0

    for item in temp_dir.iterdir():
        if item.is_dir():
            try:
                mtime = item.stat().st_mtime
                if mtime < cutoff:
                    shutil.rmtree(item, ignore_errors=True)
                    cleaned_count += 1
                    logger.debug("Cleaned up expired job directory: %s", item.name)
            except Exception as exc:
                logger.warning("Could not remove temp job dir %s: %s", item.name, exc)

    if cleaned_count > 0:
        logger.info("Cleaned up %d expired job directory(ies)", cleaned_count)
    return cleaned_count


def clear_all_temporary_files() -> int:
    """Manually remove all temporary job directories.

    Returns the number of removed directories.
    """
    temp_dir = get_temp_jobs_dir()
    if not temp_dir.exists():
        return 0

    cleaned_count = 0
    for item in temp_dir.iterdir():
        if item.is_dir():
            try:
                shutil.rmtree(item, ignore_errors=True)
                cleaned_count += 1
            except Exception as exc:
                logger.warning("Could not clear temp job dir %s: %s", item.name, exc)

    logger.info("Manual temp file cleanup removed %d directory(ies)", cleaned_count)
    return cleaned_count
