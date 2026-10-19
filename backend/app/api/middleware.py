"""Custom FastAPI middlewares: Correlation ID, Structured JSON Logging, and Idempotency."""
import datetime
import json
import logging
import sys
import time
import uuid
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.db.database import get_db

logger = logging.getLogger("incubrix.api")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Extracts or generates an X-Correlation-Id header for end-to-end request tracing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        correlation_id = request.headers.get("X-Correlation-Id") or request.headers.get("X-Request-Id")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-Id"] = correlation_id
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs structured JSON line for each incoming request and its completion metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        log_record = {
            "timestamp": now,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "correlation_id": correlation_id,
            "client_ip": request.client.host if request.client else "unknown"
        }
        logger.info(json.dumps(log_record))

        return response


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Caches and deduplicates POST requests that supply an Idempotency-Key header."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method != "POST":
            return await call_next(request)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return await call_next(request)

        db = get_db()
        cached = db.get_idempotency(idempotency_key)
        if cached:
            headers = dict(cached["headers"])
            headers["X-Cache-Lookup"] = "HIT"
            return Response(
                content=cached["body"],
                status_code=cached["status_code"],
                headers=headers,
                media_type=cached.get("media_type", "application/json")
            )

        # Execute downstream request and capture response
        response = await call_next(request)

        # Only cache successful or intentional client error responses (don't cache 500s)
        if response.status_code < 500:
            body = [chunk async for chunk in response.body_iterator]
            full_body = b"".join(body)

            headers_dict = dict(response.headers)
            headers_dict["X-Cache-Lookup"] = "MISS"

            db.save_idempotency(
                idempotency_key,
                {
                    "status_code": response.status_code,
                    "body": full_body,
                    "headers": headers_dict,
                    "media_type": response.media_type
                }
            )

            return Response(
                content=full_body,
                status_code=response.status_code,
                headers=headers_dict,
                media_type=response.media_type
            )

        return response
