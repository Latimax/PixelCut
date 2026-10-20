"""FastAPI API routes implementing the PixelCut Local API specification."""

from __future__ import annotations

import io
import json
import logging
from pathlib import Path
from typing import List, Optional
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from pixelcut_local import __app_name__, __version__
from pixelcut_local.config import Settings
from pixelcut_local.core.constants import (
    BACKGROUND_MODES,
    CANVAS_PRESETS,
    EXPORT_FORMATS,
    FIT_MODES,
    JOB_STATUS_CANCELLED,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
)
from pixelcut_local.core.jobs import (
    JobOptions,
    global_job_manager,
    process_job_synchronously,
)
from pixelcut_local.core.models import (
    MODEL_REGISTRY,
    get_available_execution_providers,
    is_model_downloaded,
)
from pixelcut_local.core.validation import ImageValidationError, validate_image_file
from pixelcut_local.server.auth import verify_client_access
from pixelcut_local.server.network_utils import generate_qr_code_image, get_lan_ip
from pixelcut_local.server.schemas import (
    CreateJobResponse,
    HealthResponse,
    JobStatusResponse,
    ModelDetailResponse,
    PublicSettingsResponse,
    ServerInfoResponse,
)

logger = logging.getLogger(__name__)

api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Return application and model status."""
    settings = Settings.load()
    ready = is_model_downloaded(settings.model_name)
    providers = get_available_execution_providers()
    return HealthResponse(
        status="ok",
        app_name=__app_name__,
        version=__version__,
        model_ready=ready,
        default_model=settings.model_name,
        providers=providers,
    )


@api_router.get("/settings/public", response_model=PublicSettingsResponse)
def get_public_settings() -> PublicSettingsResponse:
    """Return safe public configuration for web and mobile clients."""
    settings = Settings.load()
    return PublicSettingsResponse(
        max_upload_mb=settings.max_upload_mb,
        max_megapixels=settings.max_megapixels,
        default_model=settings.model_name,
        canvas_presets=list(CANVAS_PRESETS.keys()),
        background_modes=BACKGROUND_MODES,
        fit_modes=FIT_MODES,
        export_formats=EXPORT_FORMATS,
        lan_mode_enabled=settings.lan_mode_enabled,
    )


@api_router.get("/models", response_model=List[ModelDetailResponse])
def get_models() -> List[ModelDetailResponse]:
    """List available AI models with license terms and local status."""
    results = []
    for m in MODEL_REGISTRY.values():
        results.append(
            ModelDetailResponse(
                id=m.id,
                name=m.name,
                description=m.description,
                approx_size_mb=m.approx_size_mb,
                license_type=m.license_type,
                commercial_cleared=m.commercial_cleared,
                license_notice=m.license_notice,
                is_downloaded=is_model_downloaded(m.id),
            )
        )
    return results


@api_router.get("/server-info", response_model=ServerInfoResponse)
def get_server_info() -> ServerInfoResponse:
    """Safe connection status and reachable URL (no secrets)."""
    settings = Settings.load()
    lan_ip = get_lan_ip()
    port = settings.server_port
    lan_url = f"http://{lan_ip}:{port}" if lan_ip else None
    localhost_url = f"http://127.0.0.1:{port}"

    return ServerInfoResponse(
        running=True,
        host=settings.server_host,
        port=port,
        lan_mode_enabled=settings.lan_mode_enabled,
        lan_ip=lan_ip,
        lan_url=lan_url,
        localhost_url=localhost_url,
    )


@api_router.get("/qr-code")
def get_qr_code() -> Response:
    """Return QR code image for the server address."""
    settings = Settings.load()
    lan_ip = get_lan_ip()
    port = settings.server_port
    url = f"http://{lan_ip}:{port}" if (settings.lan_mode_enabled and lan_ip) else f"http://127.0.0.1:{port}"
    img_bytes = generate_qr_code_image(url)
    return Response(content=img_bytes, media_type="image/png")


@api_router.post(
    "/jobs",
    response_model=CreateJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_client_access)],
)
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    bg_file: Optional[UploadFile] = File(None),
    model_name: Optional[str] = Form(None),
    quality_mode: Optional[str] = Form("fast"),
    use_alpha_matting: Optional[bool] = Form(False),
    prefer_gpu: Optional[bool] = Form(False),
    bg_mode: Optional[str] = Form("transparent"),
    solid_color: Optional[str] = Form("#ffffff"),
    gradient_colors: Optional[str] = Form(None),  # JSON string e.g. [[255,255,255],[0,0,0]]
    gradient_angle: Optional[float] = Form(45.0),
    bg_fit_mode: Optional[str] = Form("cover"),
    bg_blur: Optional[float] = Form(0.0),
    bg_brightness: Optional[float] = Form(1.0),
    canvas_preset: Optional[str] = Form("original"),
    scale: Optional[float] = Form(1.0),
    offset_x: Optional[int] = Form(0),
    offset_y: Optional[int] = Form(0),
    rotation: Optional[float] = Form(0.0),
    padding: Optional[int] = Form(0),
    enable_shadow: Optional[bool] = Form(False),
    shadow_intensity: Optional[float] = Form(0.5),
    enable_outline: Optional[bool] = Form(False),
    outline_color: Optional[str] = Form(None),  # JSON string [255,255,255]
    outline_width: Optional[int] = Form(0),
    export_format: Optional[str] = Form("PNG"),
    export_quality: Optional[int] = Form(95),
) -> CreateJobResponse:
    """Accept an image file and processing parameters, creating an isolated asynchronous job."""
    settings = Settings.load()

    # 1. Read and validate uploaded file payload
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        validate_image_file(
            file_bytes,
            max_mb=settings.max_upload_mb,
            max_megapixels=settings.max_megapixels,
            filename_hint=file.filename or "",
        )
    except ImageValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Parse gradient colors JSON if present
    parsed_gradient = [[240, 240, 250], [180, 200, 240]]
    if gradient_colors:
        try:
            parsed_gradient = json.loads(gradient_colors)
        except Exception:
            pass

    # Parse outline color JSON if present
    parsed_outline_color = [255, 255, 255]
    if outline_color:
        try:
            parsed_outline_color = json.loads(outline_color)
        except Exception:
            pass

    # 2. Build JobOptions
    options = JobOptions(
        model_name=model_name or settings.model_name,
        quality_mode=quality_mode or "fast",
        use_alpha_matting=bool(use_alpha_matting),
        prefer_gpu=bool(prefer_gpu),
        bg_mode=bg_mode or "transparent",
        solid_color=solid_color or "#ffffff",
        gradient_colors=parsed_gradient,
        gradient_angle=float(gradient_angle or 45.0),
        bg_fit_mode=bg_fit_mode or "cover",
        bg_blur=float(bg_blur or 0.0),
        bg_brightness=float(bg_brightness or 1.0),
        canvas_preset=canvas_preset or "original",
        scale=float(scale or 1.0),
        offset_x=int(offset_x or 0),
        offset_y=int(offset_y or 0),
        rotation=float(rotation or 0.0),
        padding=int(padding or 0),
        enable_shadow=bool(enable_shadow),
        shadow_intensity=float(shadow_intensity or 0.5),
        enable_outline=bool(enable_outline),
        outline_color=parsed_outline_color,
        outline_width=int(outline_width or 0),
        export_format=export_format or "PNG",
        export_quality=int(export_quality or 95),
    )

    # 3. Create JobRecord in managed temp storage
    original_name = file.filename or "upload.png"
    record = global_job_manager.create_job(original_filename=original_name, options=options)

    # Save uploaded input image in isolated job directory
    job_dir = Path(record.job_dir)
    in_ext = Path(original_name).suffix or ".png"
    in_path = job_dir / f"input{in_ext}"
    with open(in_path, "wb") as f:
        f.write(file_bytes)
    record.input_path = str(in_path)

    # Handle background image upload if provided
    if bg_file and bg_file.filename:
        bg_bytes = await bg_file.read()
        if bg_bytes:
            bg_ext = Path(bg_file.filename).suffix or ".png"
            bg_path = job_dir / f"background{bg_ext}"
            with open(bg_path, "wb") as f:
                f.write(bg_bytes)
            record.bg_input_path = str(bg_path)

    global_job_manager._save_record_to_disk(record)

    # 4. Enqueue background execution task
    background_tasks.add_task(process_job_synchronously, record)

    return CreateJobResponse(
        job_id=record.id,
        status=record.status,
        created_at=record.created_at,
    )


@api_router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    dependencies=[Depends(verify_client_access)],
)
def get_job_status(job_id: str) -> JobStatusResponse:
    """Retrieve progress and current state for a job."""
    record = global_job_manager.get_job(job_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    return JobStatusResponse(
        id=record.id,
        original_filename=record.original_filename,
        status=record.status,
        progress=record.progress,
        created_at=record.created_at,
        updated_at=record.updated_at,
        error_code=record.error_code,
        error_message=record.error_message,
        has_result=bool(record.result_path and Path(record.result_path).exists()),
    )


@api_router.get(
    "/jobs/{job_id}/result",
    dependencies=[Depends(verify_client_access)],
)
def get_job_result(job_id: str) -> FileResponse:
    """Download the completed processed image for a job."""
    record = global_job_manager.get_job(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found.")

    if record.status != JOB_STATUS_COMPLETED or not record.result_path:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed yet (current status: {record.status}).",
        )

    res_path = Path(record.result_path)
    if not res_path.exists():
        raise HTTPException(status_code=404, detail="Result file missing from storage.")

    # Secure filename for download
    stem = Path(record.original_filename).stem
    ext = res_path.suffix
    download_name = f"{stem}_cutout{ext}"

    media_type = "image/png"
    if ext.lower() in (".jpg", ".jpeg"):
        media_type = "image/jpeg"
    elif ext.lower() == ".webp":
        media_type = "image/webp"

    return FileResponse(
        path=str(res_path),
        media_type=media_type,
        filename=download_name,
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )


@api_router.delete(
    "/jobs/{job_id}",
    dependencies=[Depends(verify_client_access)],
)
def delete_job(job_id: str) -> dict:
    """Cancel and delete a job."""
    success = global_job_manager.delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or already deleted.")
    return {"status": "deleted", "job_id": job_id}
