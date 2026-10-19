"""Main FastAPI application entry point for IncuBrix."""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.api.routes import api_v1_router, health_router
from app.api.middleware import CorrelationIdMiddleware, LoggingMiddleware, IdempotencyMiddleware
from app.api.errors import (
    IncuBrixError,
    incrubix_error_handler,
    validation_error_handler,
    http_exception_handler,
    general_exception_handler
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure storage directories exist and validate config
    settings = get_settings()
    storage_dir = Path(settings.STORAGE_PATH).resolve()
    storage_dir.mkdir(parents=True, exist_ok=True)
    (storage_dir / "sources").mkdir(parents=True, exist_ok=True)
    (storage_dir / "renders").mkdir(parents=True, exist_ok=True)
    (storage_dir / "audio").mkdir(parents=True, exist_ok=True)

    yield
    # Shutdown logic if any


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        description="Deterministic Prompt-Based Video Editing Platform API with Content Anchors",
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )

    # 1. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-Id", "Idempotency-Key", "X-Cache-Lookup"]
    )

    # 2. Custom Middlewares (Correlation ID, Logging, Idempotency)
    # In Starlette, middlewares are executed in reverse order of addition:
    # Incoming: CorrelationId -> Logging -> Idempotency -> Route
    app.add_middleware(IdempotencyMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    # 3. Exception Handlers
    app.add_exception_handler(IncuBrixError, incrubix_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # 4. Include Routers
    app.include_router(health_router)
    app.include_router(api_v1_router)

    # 5. Mount Static Files for direct downloads if directory exists
    storage_dir = Path(settings.STORAGE_PATH).resolve()
    storage_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/downloads", StaticFiles(directory=str(storage_dir), check_dir=False), name="downloads")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
