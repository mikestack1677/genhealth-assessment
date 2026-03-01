from __future__ import annotations

from typing import TYPE_CHECKING

from genhealth.repositories.activity_repository import ActivityRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from genhealth.models.activity_log import ActivityLog
    from genhealth.schemas.activity_log import ActivityLogCreate


class ActivityService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ActivityRepository(session)

    async def list_activity(self, *, page: int = 1, page_size: int = 50) -> tuple[list[ActivityLog], int]:
        """Return a paginated list of activity log entries."""
        return await self._repo.paginate(page=page, page_size=page_size)

    async def log(self, payload: ActivityLogCreate) -> ActivityLog:
        """Persist a new activity log entry."""
        return await self._repo.create(payload)
