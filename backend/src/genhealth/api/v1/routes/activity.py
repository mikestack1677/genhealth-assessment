from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 — FastAPI resolves Annotated[AsyncSession, Depends(...)] via get_type_hints() at runtime
)

from genhealth.core.database import get_session
from genhealth.schemas.activity_log import ActivityLogResponse
from genhealth.schemas.common import PaginatedResponse
from genhealth.services.activity_service import ActivityService

router = APIRouter()


@router.get("/activity", response_model=PaginatedResponse[ActivityLogResponse])
async def list_activity(
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PaginatedResponse[ActivityLogResponse]:
    """List activity log entries with pagination."""
    service = ActivityService(session)
    logs, total = await service.list_activity(page=page, page_size=page_size)
    return PaginatedResponse[ActivityLogResponse].build(
        items=[ActivityLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )
