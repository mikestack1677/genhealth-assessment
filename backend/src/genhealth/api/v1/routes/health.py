from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from genhealth.core.config import Settings, get_settings

router = APIRouter()


@router.get("/health")
async def health(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, str]:
    """Liveness probe. Returns 200 if the service is running."""
    return {"status": "ok", "environment": settings.environment}
