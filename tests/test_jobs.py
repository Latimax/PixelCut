"""Unit tests for JobManager, status lifecycle, cancellation, and cleanup."""

from __future__ import annotations

import time
from pathlib import Path
import pytest

from pixelcut_local.core.jobs import (
    JOB_STATUS_CANCELLED,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_QUEUED,
    JobManager,
    JobOptions,
)
from pixelcut_local.storage.cleanup import cleanup_expired_jobs


def test_job_lifecycle():
    mgr = JobManager()
    job = mgr.create_job("test_photo.jpg", options=JobOptions(model_name="u2netp"))

    assert job.id
    assert job.status == JOB_STATUS_QUEUED
    assert Path(job.job_dir).exists()

    # Update progress
    mgr.update_status(job.id, status="processing", progress=50)
    fetched = mgr.get_job(job.id)
    assert fetched.status == "processing"
    assert fetched.progress == 50

    # Cancel
    assert mgr.cancel_job(job.id)
    assert mgr.get_job(job.id).status == JOB_STATUS_CANCELLED

    # Delete
    assert mgr.delete_job(job.id)
    assert mgr.get_job(job.id) is None


def test_cleanup_expired_jobs():
    # Calling cleanup should run without errors
    count = cleanup_expired_jobs(max_age_hours=0.0001)
    assert isinstance(count, int)
