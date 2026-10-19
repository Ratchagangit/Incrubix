"""Custom exception classes and error handlers for IncuBrix API."""
from typing import Any, Dict, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


def format_error_response(
    code: str,
    message: str,
    retryable: bool = False,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
            "details": details or {}
        }
    }


class IncuBrixError(Exception):
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.retryable = retryable
        self.details = details or {}


class VideoError(IncuBrixError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, retryable: bool = False):
        super().__init__(
            message=message,
            code="INVALID_VIDEO",
            status_code=status.HTTP_400_BAD_REQUEST,
            retryable=retryable,
            details=details
        )


class VideoNotFoundError(IncuBrixError):
    def __init__(self, message: str = "Video not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VIDEO_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            retryable=False,
            details=details
        )


class ProjectNotFoundError(IncuBrixError):
    def __init__(self, message: str = "Project not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="PROJECT_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            retryable=False,
            details=details
        )


class TimelineError(IncuBrixError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="TIMELINE_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            retryable=False,
            details=details
        )


class InstructionError(IncuBrixError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="INSTRUCTION_REJECTED",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            retryable=False,
            details=details
        )


class RenderError(IncuBrixError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, retryable: bool = True):
        super().__init__(
            message=message,
            code="RENDER_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            retryable=retryable,
            details=details
        )


class StorageError(IncuBrixError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, retryable: bool = True):
        super().__init__(
            message=message,
            code="STORAGE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            retryable=retryable,
            details=details
        )


class JobNotFoundError(IncuBrixError):
    def __init__(self, message: str = "Job not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="JOB_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            retryable=False,
            details=details
        )


class InvalidRequestError(IncuBrixError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="INVALID_REQUEST",
            status_code=status.HTTP_400_BAD_REQUEST,
            retryable=False,
            details=details
        )


class IdempotencyConflictError(IncuBrixError):
    def __init__(self, message: str = "Concurrent or conflicting request with same idempotency key", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="IDEMPOTENCY_CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            retryable=False,
            details=details
        )


async def incrubix_error_handler(request: Request, exc: IncuBrixError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            details=exc.details
        )
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = {"errors": exc.errors()}
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=format_error_response(
            code="INVALID_REQUEST",
            message="Request validation error",
            retryable=False,
            details=details
        )
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code_map = {
        400: "INVALID_REQUEST",
        404: "NOT_FOUND",
        409: "IDEMPOTENCY_CONFLICT",
        422: "INVALID_REQUEST",
        500: "INTERNAL_ERROR"
    }
    code = code_map.get(exc.status_code, "ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(
            code=code,
            message=str(exc.detail),
            retryable=(exc.status_code >= 500),
            details={}
        )
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=format_error_response(
            code="INTERNAL_ERROR",
            message=str(exc) or "Internal server error",
            retryable=True,
            details={"type": exc.__class__.__name__}
        )
    )
