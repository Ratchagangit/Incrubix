"""API routes aggregation module."""
from fastapi import APIRouter

from app.api.routes.videos import router as videos_router
from app.api.routes.instructions import router as instructions_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.health import router as health_router

# Core API v1 router
api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(videos_router)
api_v1_router.include_router(instructions_router)
api_v1_router.include_router(jobs_router)

__all__ = ["api_v1_router", "health_router", "videos_router", "instructions_router", "jobs_router"]
