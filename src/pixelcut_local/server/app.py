"""FastAPI application factory and static file serving for PixelCut Local."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pixelcut_local import __app_name__, __version__
from pixelcut_local.server.routes import api_router
from pixelcut_local.storage.cleanup import cleanup_expired_jobs
from pixelcut_local.storage.paths import get_static_dir

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for server startup and graceful shutdown."""
    logger.info("PixelCut Local server starting up...")
    try:
        cleanup_expired_jobs(max_age_hours=12.0)
    except Exception as exc:
        logger.warning("Startup cleanup failed: %s", exc)
    yield
    logger.info("PixelCut Local server shutting down gracefully...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI web application instance."""
    app = FastAPI(
        title=__app_name__,
        version=__version__,
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )

    # Restrictive CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Local LAN origins
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Mount API routes
    app.include_router(api_router)

    # Static Web UI Assets
    static_dir = get_static_dir()
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/", include_in_schema=False)
        async def serve_index():
            index_path = static_dir / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
            return {"message": "PixelCut Local Mobile Web UI is not installed."}

    return app
