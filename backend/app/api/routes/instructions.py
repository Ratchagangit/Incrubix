"""Instruction execution, timeline inspection, undo/redo, and rendering endpoints."""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Header, status
from pydantic import BaseModel, Field

from app.core.models import Project, InstructionResult
from app.services.instruction_service import InstructionService
from app.services.job_service import JobService
from app.api.dependencies import get_project, get_instruction_service, get_job_service


router = APIRouter(prefix="/projects", tags=["Instructions & Timeline"])


class InstructionRequest(BaseModel):
    instruction: str = Field(..., description="Natural language prompt describing desired video edit")
    answer: Optional[str] = Field(None, description="Optional answer to previous clarification question")


class RenderRequest(BaseModel):
    callback_url: Optional[str] = Field(None, description="Optional webhook URL to receive HMAC-signed job completion payload")


class RestoreRequest(BaseModel):
    step_index: int = Field(..., description="Step index to restore")


@router.post("/{project_id}/instructions", response_model=InstructionResult)
async def process_project_instruction(
    project_id: str,
    payload: InstructionRequest,
    project: Project = Depends(get_project),
    instruction_service: InstructionService = Depends(get_instruction_service)
):
    """
    Process natural language editing instruction on project timeline.
    Returns InstructionResult with status (APPLIED, NEEDS_CLARIFICATION, REJECTED).
    """
    result = await instruction_service.process_instruction(
        project=project,
        instruction=payload.instruction,
        answer=payload.answer
    )
    return result


@router.get("/{project_id}/timeline")
async def get_project_timeline(
    project_id: str,
    project: Project = Depends(get_project)
):
    """Retrieve current timeline state, segments, anchors, and active background music."""
    return project.timeline.model_dump()


@router.get("/{project_id}/history")
async def get_project_history(
    project_id: str,
    project: Project = Depends(get_project)
):
    """Retrieve full edit history stack and current position."""
    return {
        "history_position": project.history_position,
        "total_steps": len(project.history_stack),
        "history": [tx.model_dump() for tx in project.history_stack]
    }


@router.post("/{project_id}/undo", response_model=InstructionResult)
async def undo_project_step(
    project_id: str,
    project: Project = Depends(get_project),
    instruction_service: InstructionService = Depends(get_instruction_service)
):
    """Undo the last applied edit operation."""
    return instruction_service.handle_undo(project)


@router.post("/{project_id}/redo", response_model=InstructionResult)
async def redo_project_step(
    project_id: str,
    project: Project = Depends(get_project),
    instruction_service: InstructionService = Depends(get_instruction_service)
):
    """Redo the previously reversed edit operation."""
    return instruction_service.handle_redo(project)


@router.post("/{project_id}/restore", response_model=InstructionResult)
async def restore_project_step(
    project_id: str,
    payload: RestoreRequest,
    project: Project = Depends(get_project),
    instruction_service: InstructionService = Depends(get_instruction_service)
):
    """Restore timeline to state after a specific step index."""
    return instruction_service.handle_restore(project, payload.step_index)


@router.post("/{project_id}/render", status_code=status.HTTP_202_ACCEPTED)
async def render_project(
    project_id: str,
    payload: Optional[RenderRequest] = None,
    project: Project = Depends(get_project),
    job_service: JobService = Depends(get_job_service)
):
    """Queue background render job for current project timeline."""
    params = {}
    if payload and payload.callback_url:
        params["callback_url"] = payload.callback_url

    job_id = job_service.create_job("render", str(project.id), params)
    job_service.run_render_job(job_id, project)

    return {
        "status": "queued",
        "job_id": job_id,
        "project_id": str(project.id),
        "message": f"Render job {job_id} queued for processing."
    }
