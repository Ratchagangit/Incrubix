"""Job polling and asset download routes."""
import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.services.job_service import JobService
from app.api.dependencies import get_job_service
from app.api.errors import JobNotFoundError


router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("")
async def list_jobs(job_service: JobService = Depends(get_job_service)):
    """List all registered background jobs."""
    return {"jobs": job_service.db.list_jobs()}


@router.get("/{job_id}")
async def get_job_status(job_id: str, job_service: JobService = Depends(get_job_service)):
    """Retrieve current status, progress, and result for a background job."""
    return job_service.get_job(job_id)


@router.get("/{job_id}/download")
async def download_job_result(job_id: str, job_service: JobService = Depends(get_job_service)):
    """Download output file produced by a succeeded render job."""
    job = job_service.get_job(job_id)
    if job.get("status") != "succeeded":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job '{job_id}' has not succeeded (current status: {job.get('status')})"
        )

    result = job.get("result") or {}
    output_path = result.get("output_path")
    if not output_path or not os.path.exists(output_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Render output file not found on disk: {output_path}"
        )

    filename = os.path.basename(output_path)
    return FileResponse(
        path=output_path,
        filename=filename,
        media_type="video/mp4"
    )
