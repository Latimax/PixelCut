"""Job management, lifecycle tracking, background execution, and isolation."""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from PIL import Image

from pixelcut_local.core.constants import (
    JOB_STATUS_CANCELLED,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_COMPOSITING,
    JOB_STATUS_FAILED,
    JOB_STATUS_LOADING_MODEL,
    JOB_STATUS_PROCESSING,
    JOB_STATUS_QUEUED,
    JOB_STATUS_VALIDATING,
)
from pixelcut_local.storage.paths import get_temp_jobs_dir

logger = logging.getLogger(__name__)


@dataclass
class JobOptions:
    """Configurable processing parameters for a single job."""

    model_name: str = "u2netp"
    quality_mode: str = "fast"
    use_alpha_matting: bool = False
    prefer_gpu: bool = False

    # Composition
    bg_mode: str = "transparent"  # "transparent", "solid", "gradient", "image"
    solid_color: str = "#ffffff"
    gradient_colors: List[List[int]] = field(default_factory=lambda: [[240, 240, 250], [180, 200, 240]])
    gradient_angle: float = 45.0
    bg_fit_mode: str = "cover"
    bg_blur: float = 0.0
    bg_brightness: float = 1.0

    # Transformations
    canvas_preset: str = "original"
    scale: float = 1.0
    offset_x: int = 0
    offset_y: int = 0
    rotation: float = 0.0
    padding: int = 0
    enable_shadow: bool = False
    shadow_intensity: float = 0.5
    enable_outline: bool = False
    outline_color: List[int] = field(default_factory=lambda: [255, 255, 255])
    outline_width: int = 0

    # Export
    export_format: str = "PNG"
    export_quality: int = 95


@dataclass
class JobRecord:
    """State and metadata for a single background removal / composition job."""

    id: str
    original_filename: str
    status: str = JOB_STATUS_QUEUED
    progress: int = 0  # 0 to 100
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    client_ip: Optional[str] = None

    # Paths inside managed temp directory
    job_dir: Optional[str] = None
    input_path: Optional[str] = None
    bg_input_path: Optional[str] = None
    cutout_path: Optional[str] = None
    alpha_mask_path: Optional[str] = None
    result_path: Optional[str] = None

    # Options
    options: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to public dictionary representation (excluding internal server paths)."""
        return {
            "id": self.id,
            "original_filename": self.original_filename,
            "status": self.status,
            "progress": self.progress,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "has_result": bool(self.result_path and Path(self.result_path).exists()),
        }


class JobManager:
    """Thread-safe manager for all local and server-initiated processing jobs."""

    def __init__(self):
        self._jobs: Dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    def create_job(
        self,
        original_filename: str,
        options: Optional[JobOptions] = None,
        client_ip: Optional[str] = None,
    ) -> JobRecord:
        """Create a new job record with its own isolated managed directory."""
        job_id = str(uuid.uuid4())
        job_dir = get_temp_jobs_dir() / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        opts_dict = asdict(options) if options else asdict(JobOptions())

        record = JobRecord(
            id=job_id,
            original_filename=Path(original_filename).name,
            job_dir=str(job_dir),
            options=opts_dict,
            client_ip=client_ip,
        )

        with self._lock:
            self._jobs[job_id] = record

        self._save_record_to_disk(record)
        logger.debug("Created job %s for file %s", job_id, record.original_filename)
        return record

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        """Fetch job record by ID."""
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self) -> List[JobRecord]:
        """List all active jobs ordered by creation time descending."""
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def update_status(
        self,
        job_id: str,
        status: str,
        progress: Optional[int] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update job progress and state."""
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return

            # Prevent updating a cancelled job
            if record.status == JOB_STATUS_CANCELLED and status != JOB_STATUS_CANCELLED:
                return

            record.status = status
            record.updated_at = time.time()
            if progress is not None:
                record.progress = max(0, min(100, progress))
            if error_code:
                record.error_code = error_code
            if error_message:
                record.error_message = error_message

        self._save_record_to_disk(record)

    def cancel_job(self, job_id: str) -> bool:
        """Mark job as cancelled."""
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return False
            if record.status in (JOB_STATUS_COMPLETED, JOB_STATUS_FAILED):
                return False
            record.status = JOB_STATUS_CANCELLED
            record.updated_at = time.time()

        self._save_record_to_disk(record)
        logger.info("Cancelled job %s", job_id)
        return True

    def delete_job(self, job_id: str) -> bool:
        """Cancel and delete job record and clean its directory."""
        with self._lock:
            record = self._jobs.pop(job_id, None)

        if record and record.job_dir:
            p = Path(record.job_dir)
            if p.exists():
                import shutil
                shutil.rmtree(p, ignore_errors=True)
            return True
        return False

    def _save_record_to_disk(self, record: JobRecord) -> None:
        """Save job state metadata file inside job's directory."""
        if not record.job_dir:
            return
        meta_path = Path(record.job_dir) / "job.json"
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(asdict(record), f, indent=2)
        except Exception as exc:
            logger.debug("Could not write job metadata to %s: %s", meta_path, exc)


def process_job_synchronously(job_record: JobRecord) -> Path:
    """Execute background removal and composition for a JobRecord.

    Unified pipeline called by both FastAPI background workers and desktop workers.
    """
    from pixelcut_local.core.background_removal import remove_background
    from pixelcut_local.core.composition import composite_image
    from pixelcut_local.core.export import export_image
    from pixelcut_local.core.image_io import load_image
    from pixelcut_local.core.validation import ImageValidationError

    mgr = global_job_manager
    job_id = job_record.id

    try:
        if job_record.status == JOB_STATUS_CANCELLED:
            raise RuntimeError("Job was cancelled before processing started.")

        # 1. Validation
        mgr.update_status(job_id, status=JOB_STATUS_VALIDATING, progress=10)
        if not job_record.input_path or not Path(job_record.input_path).exists():
            raise ImageValidationError("Input image file is missing.", code="INPUT_MISSING")

        input_img = load_image(job_record.input_path, ensure_rgba=True)

        # 2. Model Loading
        mgr.update_status(job_id, status=JOB_STATUS_LOADING_MODEL, progress=25)
        opts = job_record.options
        model_name = opts.get("model_name", "u2netp")
        use_matting = opts.get("use_alpha_matting", False)
        prefer_gpu = opts.get("prefer_gpu", False)

        # 3. AI Inference
        mgr.update_status(job_id, status=JOB_STATUS_PROCESSING, progress=40)
        cutout, alpha_mask = remove_background(
            input_img,
            model_name=model_name,
            use_alpha_matting=use_matting,
            prefer_gpu=prefer_gpu,
        )

        job_dir = Path(job_record.job_dir)
        cutout_path = job_dir / "cutout.png"
        cutout.save(cutout_path, format="PNG")
        job_record.cutout_path = str(cutout_path)

        # 4. Composition
        mgr.update_status(job_id, status=JOB_STATUS_COMPOSITING, progress=75)
        bg_mode = opts.get("bg_mode", "transparent")
        bg_image_loaded = None
        if bg_mode == "image" and job_record.bg_input_path and Path(job_record.bg_input_path).exists():
            try:
                bg_image_loaded = load_image(job_record.bg_input_path, ensure_rgba=True)
            except Exception as exc:
                logger.warning("Could not load custom background image: %s", exc)

        grad_colors = opts.get("gradient_colors", [[240, 240, 250], [180, 200, 240]])
        c1 = tuple(grad_colors[0]) if len(grad_colors) > 0 else (240, 240, 250)
        c2 = tuple(grad_colors[1]) if len(grad_colors) > 1 else (180, 200, 240)

        composite = composite_image(
            cutout=cutout,
            bg_mode=bg_mode,
            solid_color=opts.get("solid_color", "#ffffff"),
            gradient_colors=(c1, c2),
            gradient_angle=float(opts.get("gradient_angle", 45.0)),
            bg_image=bg_image_loaded,
            bg_fit_mode=opts.get("bg_fit_mode", "cover"),
            bg_blur=float(opts.get("bg_blur", 0.0)),
            bg_brightness=float(opts.get("bg_brightness", 1.0)),
            canvas_preset=opts.get("canvas_preset", "original"),
            scale=float(opts.get("scale", 1.0)),
            offset_x=int(opts.get("offset_x", 0)),
            offset_y=int(opts.get("offset_y", 0)),
            rotation=float(opts.get("rotation", 0.0)),
            padding=int(opts.get("padding", 0)),
            enable_shadow=bool(opts.get("enable_shadow", False)),
            shadow_intensity=float(opts.get("shadow_intensity", 0.5)),
            enable_outline=bool(opts.get("enable_outline", False)),
            outline_color=tuple(opts.get("outline_color", [255, 255, 255])),
            outline_width=int(opts.get("outline_width", 0)),
        )

        # 5. Export Result in Job Dir
        export_fmt = opts.get("export_format", "PNG")
        export_quality = int(opts.get("export_quality", 95))
        ext = ".jpg" if export_fmt.upper() in ("JPEG", "JPG") else f".{export_fmt.lower()}"
        res_path = job_dir / f"result{ext}"

        export_image(
            image=composite,
            destination_path=res_path,
            format_name=export_fmt,
            quality=export_quality,
        )
        job_record.result_path = str(res_path)

        mgr.update_status(job_id, status=JOB_STATUS_COMPLETED, progress=100)
        return res_path

    except Exception as exc:
        logger.error("Job %s execution failed: %s", job_id, exc)
        code = getattr(exc, "code", "EXECUTION_ERROR")
        mgr.update_status(
            job_id,
            status=JOB_STATUS_FAILED,
            progress=0,
            error_code=code,
            error_message=str(exc),
        )
        raise


# Global job manager singleton
global_job_manager = JobManager()
