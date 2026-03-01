from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from genhealth.models.activity_log import ActivityLog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from genhealth.schemas.activity_log import ActivityLogCreate


class ActivityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def paginate(self, *, page: int = 1, page_size: int = 50) -> tuple[list[ActivityLog], int]:
        """Return a page of activity logs and the total count."""
        offset = (page - 1) * page_size
        count_result = await self._session.execute(select(func.count()).select_from(ActivityLog))
        total = count_result.scalar_one()
        result = await self._session.execute(
            select(ActivityLog).order_by(ActivityLog.timestamp.desc()).offset(offset).limit(page_size)
        )
        return list(result.scalars().all()), total

    async def create(self, payload: ActivityLogCreate) -> ActivityLog:
        """Persist a new activity log entry."""
        log = ActivityLog(
            method=payload.method,
            path=payload.path,
            status_code=payload.status_code,
            request_summary=payload.request_summary,
            order_id=payload.order_id,
            duration_ms=payload.duration_ms,
            timestamp=payload.timestamp,
        )
        self._session.add(log)
        await self._session.flush()
        return log
