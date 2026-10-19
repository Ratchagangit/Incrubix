"""Video upload, ingestion, and metadata retrieval API routes."""
import os
import uuid
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, status
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, HttpUrl

from app.core.models import Project, Timeline
from app.core.timeline import TimelineEngine
from app.services.video_service import VideoService
from app.services.job_service import JobService
from app.services.storage_service import StorageService
from app.db.database import get_db, DataStore
from app.api.dependencies import get_video_service, get_job_service, get_storage
from app.api.errors import VideoError, VideoNotFoundError


router = APIRouter(prefix="/videos", tags=["Videos"])


class IngestUrlRequest(BaseModel):
    url: str
    callback_url: Optional[str] = None


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_video(
    file: UploadFile = File(...),
    video_service: VideoService = Depends(get_video_service),
    job_service: JobService = Depends(get_job_service),
    storage: StorageService = Depends(get_storage)
):
    """Upload video file, initialize Project, and start background transcription job."""
    if not file.filename:
        raise VideoError("Uploaded file must have a filename")

    file_bytes = await file.read()
    source_media = video_service.ingest_upload(file_bytes, file.filename)

    # Initialize timeline with single segment covering full source media
    initial_timeline = TimelineEngine.create_initial(source_media)

    # Create and persist project
    db = get_db()
    project = Project(
        id=str(source_media.id),
        source_media=source_media,
        timeline=initial_timeline,
        history_stack=[],
        history_position=-1,
        time_policy="current",
        timeline_snapshots={}
    )
    db.save_project(project)

    # Create transcription background job
    job_id = job_service.create_job(
        job_type="transcription",
        project_id=str(project.id),
        params={"filename": file.filename, "file_path": source_media.file_path}
    )
    job_service.run_transcription_job(
        job_id=job_id,
        project_id=str(project.id),
        file_path=storage.get_local_path(source_media.file_path)
    )

    return {
        "status": "queued",
        "job_id": job_id,
        "video_id": str(source_media.id),
        "project_id": str(project.id),
        "source_media": source_media.model_dump(),
        "message": "Video successfully uploaded. Transcription job queued."
    }


@router.post("/url", status_code=status.HTTP_202_ACCEPTED)
async def ingest_video_url(
    payload: IngestUrlRequest,
    video_service: VideoService = Depends(get_video_service),
    job_service: JobService = Depends(get_job_service),
    storage: StorageService = Depends(get_storage)
):
    """Ingest video from URL, initialize Project, and trigger transcription."""
    source_media = video_service.ingest_url(payload.url)
    initial_timeline = TimelineEngine.create_initial(source_media)

    db = get_db()
    project = Project(
        id=str(source_media.id),
        source_media=source_media,
        timeline=initial_timeline,
        history_stack=[],
        history_position=-1,
        time_policy="current",
        timeline_snapshots={}
    )
    db.save_project(project)

    params = {"url": payload.url}
    if payload.callback_url:
        params["callback_url"] = payload.callback_url

    job_id = job_service.create_job(
        job_type="transcription",
        project_id=str(project.id),
        params=params
    )
    job_service.run_transcription_job(
        job_id=job_id,
        project_id=str(project.id),
        file_path=storage.get_local_path(source_media.file_path)
    )

    return {
        "status": "queued",
        "job_id": job_id,
        "video_id": str(source_media.id),
        "project_id": str(project.id),
        "source_media": source_media.model_dump(),
        "message": "Video ingestion started. Transcription job queued."
    }


@router.get("/{video_id}")
async def get_video(video_id: str, video_service: VideoService = Depends(get_video_service)):
    """Retrieve video metadata, project details, and transcript if available."""
    db = get_db()
    project = db.get_project(video_id)
    if project:
        return {
            "id": project.id,
            "source_media": project.source_media.model_dump(),
            "has_transcript": project.transcript is not None,
            "transcript_summary": {
                "word_count": len(project.transcript.words) if project.transcript else 0,
                "speakers": project.transcript.speakers if project.transcript else []
            }
        }

    # Fallback to source media cache
    media = video_service.get_source_media(video_id)
    return {
        "id": media.id,
        "source_media": media.model_dump(),
        "has_transcript": False,
        "transcript_summary": None
    }


@router.get("/{video_id}/transcript")
async def get_video_transcript(video_id: str):
    """Retrieve structured transcript for a video."""
    db = get_db()
    project = db.get_project(video_id)
    if not project or not project.transcript:
        raise VideoNotFoundError(f"Transcript not found for video '{video_id}'")
    return project.transcript.model_dump()


@router.get("/{video_id}/download")
async def download_video(
    video_id: str,
    video_service: VideoService = Depends(get_video_service),
    storage: StorageService = Depends(get_storage)
):
    """Download original video media file."""
    db = get_db()
    project = db.get_project(video_id)
    if project:
        source_path = project.source_media.file_path
        filename = project.source_media.filename
    else:
        media = video_service.get_source_media(video_id)
        source_path = media.file_path
        filename = media.filename

    local_path = storage.get_local_path(source_path)
    if not os.path.exists(local_path):
        raise VideoNotFoundError(f"File for video '{video_id}' not found on storage")

    return FileResponse(
        path=local_path,
        filename=filename,
        media_type="video/mp4"
    )
