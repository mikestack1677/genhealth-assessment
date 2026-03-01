from __future__ import annotations

import uuid  # noqa: TC003 — Pydantic resolves field types at runtime via get_type_hints()
from datetime import datetime  # noqa: TC003 — Pydantic resolves field types at runtime via get_type_hints()

from pydantic import BaseModel


class ActivityLogCreate(BaseModel):
    method: str
    path: str
    status_code: int
    request_summary: str | None
    order_id: uuid.UUID | None
    duration_ms: int
    timestamp: datetime


class ActivityLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    method: str
    path: str
    status_code: int
    request_summary: str | None
    order_id: uuid.UUID | None
    duration_ms: int
    timestamp: datetime
