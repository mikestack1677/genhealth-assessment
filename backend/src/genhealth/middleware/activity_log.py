from __future__ import annotations

import asyncio
import re
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog
from starlette.middleware.base import BaseHTTPMiddleware

from genhealth.core.database import get_session_factory
from genhealth.schemas.activity_log import ActivityLogCreate
from genhealth.services.activity_service import ActivityService

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response
    from starlette.types import ASGIApp

logger = structlog.get_logger()

# Matches /orders/{uuid}/... to extract order_id from path
_ORDER_ID_RE = re.compile(r"/orders/([0-9a-fA-F-]{36})")

# Strong references to background tasks to prevent premature GC
_background_tasks: set[asyncio.Task[None]] = set()


def _extract_order_id(path: str) -> uuid.UUID | None:
    """Extract order UUID from a path like /api/v1/orders/{id}/document."""
    match = _ORDER_ID_RE.search(path)
    if match:
        try:
            return uuid.UUID(match.group(1))
        except ValueError:
            return None
    return None


def _build_request_summary(request: Request) -> str | None:
    """Build a sanitized summary of the request (never include raw file bytes)."""
    parts: list[str] = []
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        parts.append("multipart upload")
        content_length = request.headers.get("content-length")
        if content_length:
            parts.append(f"size={content_length}B")
    elif "application/json" in content_type:
        content_length = request.headers.get("content-length")
        if content_length:
            parts.append(f"json body size={content_length}B")

    return "; ".join(parts) if parts else None


class ActivityLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: object) -> Response:
        start = time.monotonic()
        response: Response = await call_next(request)  # type: ignore[operator]
        duration_ms = int((time.monotonic() - start) * 1000)

        path = request.url.path
        entry = ActivityLogCreate(
            method=request.method,
            path=path,
            status_code=response.status_code,
            request_summary=_build_request_summary(request),
            order_id=_extract_order_id(path),
            duration_ms=duration_ms,
            timestamp=datetime.now(UTC),
        )

        # Fire-and-forget: write to DB without blocking the response.
        # Keep a strong reference so the task isn't GC'd before completion.
        task = asyncio.create_task(_persist_log(entry))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

        return response


async def _persist_log(entry: ActivityLogCreate) -> None:
    """Write an activity log entry to the database."""
    try:
        async with get_session_factory()() as session, session.begin():
            service = ActivityService(session)
            await service.log(entry)
    except Exception:
        logger.exception("activity_log_write_failed", path=entry.path, method=entry.method)
