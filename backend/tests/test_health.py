from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient) -> None:
    """Health endpoint returns status ok."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "environment" in data


@pytest.mark.asyncio
async def test_health_returns_environment(client: AsyncClient) -> None:
    """Health endpoint includes the configured environment."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["environment"], str)
    assert len(data["environment"]) > 0
