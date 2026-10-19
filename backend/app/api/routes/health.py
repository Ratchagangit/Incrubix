"""Health check and readiness probe endpoints."""
import datetime
import os
import shutil
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.config import get_settings, Settings
from app.services.storage_service import StorageService
from app.api.dependencies import get_storage


router = APIRouter(tags=["Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(settings: Settings = Depends(get_settings)):
    """Liveness probe: returns 200 OK if service is up and running."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }


@router.get("/ready")
async def readiness_check(
    settings: Settings = Depends(get_settings),
    storage: StorageService = Depends(get_storage)
):
    """Readiness probe: checks storage, ffmpeg binaries, and backend dependencies."""
    checks = {}
    is_ready = True

    # 1. Storage check
    try:
        test_path = "health_check_probe.tmp"
        storage.save_file(b"ready", test_path)
        storage.delete_file(test_path)
        checks["storage"] = "ok"
    except Exception as e:
        checks["storage"] = f"error: {str(e)}"
        is_ready = False

    # 2. FFmpeg / FFprobe check
    ffmpeg_found = bool(shutil.which(settings.FFMPEG_PATH) or os.path.exists(settings.FFMPEG_PATH))
    ffprobe_found = bool(shutil.which(settings.FFPROBE_PATH) or os.path.exists(settings.FFPROBE_PATH))
    checks["ffmpeg"] = "ok" if ffmpeg_found else "not_found (using fallback)"
    checks["ffprobe"] = "ok" if ffprobe_found else "not_found (using fallback)"

    # 3. Adapters check
    checks["transcription_provider"] = settings.TRANSCRIPTION_PROVIDER
    checks["llm_provider"] = settings.LLM_PROVIDER
    checks["time_policy"] = settings.TIME_POLICY

    response_body = {
        "status": "ready" if is_ready else "degraded",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "checks": checks,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=response_body)
