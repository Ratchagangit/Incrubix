"""FastAPI dependency injection providers."""
from fastapi import Depends
from app.config import get_settings, Settings
from app.db.database import get_db, DataStore
from app.core.models import Project
from app.services.storage_service import StorageService, create_storage_service
from app.services.video_service import VideoService
from app.services.job_service import JobService
from app.services.instruction_service import InstructionService
from app.api.errors import ProjectNotFoundError


def get_storage(settings: Settings = Depends(get_settings)) -> StorageService:
    return create_storage_service(settings)


def get_video_service(
    storage: StorageService = Depends(get_storage),
    settings: Settings = Depends(get_settings)
) -> VideoService:
    return VideoService(storage_service=storage, settings=settings)


def get_job_service(
    settings: Settings = Depends(get_settings)
) -> JobService:
    db = get_db()
    return JobService(db=db, settings=settings)


def get_instruction_service(
    job_service: JobService = Depends(get_job_service),
    settings: Settings = Depends(get_settings)
) -> InstructionService:
    db = get_db()
    return InstructionService(job_service=job_service, db=db, settings=settings)


def get_project(project_id: str) -> Project:
    db = get_db()
    project = db.get_project(project_id)
    if not project:
        raise ProjectNotFoundError(f"Project '{project_id}' not found")
    return project
