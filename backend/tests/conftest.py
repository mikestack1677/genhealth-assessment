from __future__ import annotations

import os
import subprocess
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from genhealth.models.order import Order, OrderStatus

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Iterator

# Default matches our isolated postgres container on port 5433; override via TEST_DATABASE_URL env var
_base_url = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://genhealth:genhealth_dev@localhost:5433/genhealth",
)
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", _base_url.rsplit("/genhealth", 1)[0] + "/genhealth_test")


@pytest.fixture(scope="session")
async def test_engine() -> AsyncIterator[AsyncEngine]:
    """Session-scoped engine shared across all tests."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _run_migrations(test_engine: AsyncEngine) -> Iterator[None]:
    """Run Alembic migrations once per test session, then downgrade after.

    Sync fixture using subprocess to avoid asyncio.run() conflict.
    """
    backend_dir = Path(__file__).parent.parent
    env = {**os.environ, "DATABASE_URL": TEST_DATABASE_URL}
    uv = "uv"

    subprocess.run(  # noqa: S603
        [uv, "run", "alembic", "upgrade", "head"],
        cwd=str(backend_dir),
        env=env,
        check=True,
    )
    yield
    subprocess.run(  # noqa: S603
        [uv, "run", "alembic", "downgrade", "base"],
        cwd=str(backend_dir),
        env=env,
        check=True,
    )


@pytest.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Per-test session that rolls back after each test."""
    async with test_engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest.fixture
async def client(test_engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    """HTTP test client with database and LLM provider dependency overrides."""
    from unittest.mock import AsyncMock

    from genhealth.core.database import get_session
    from genhealth.main import app
    from genhealth.services.llm_providers import get_llm_provider
    from genhealth.services.llm_providers.base import LLMProvider

    test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with test_session_factory() as session:
            try:
                yield session
            finally:
                await session.rollback()

    def override_get_llm_provider() -> LLMProvider:
        """Return a no-op mock provider so tests don't need real API credentials."""
        return AsyncMock(spec=LLMProvider)

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_llm_provider] = override_get_llm_provider

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed data factories
# ---------------------------------------------------------------------------


def _make_order(
    *,
    patient_first_name: str | None = "Jane",
    patient_last_name: str | None = "Doe",
    patient_dob: date | None = date(1985, 6, 15),
    status: OrderStatus = OrderStatus.PENDING,
    notes: str | None = None,
) -> Order:
    return Order(
        patient_first_name=patient_first_name,
        patient_last_name=patient_last_name,
        patient_dob=patient_dob,
        status=status,
        notes=notes,
    )


@pytest.fixture
def make_order() -> Callable[..., Order]:
    """Factory fixture for creating Order instances (not persisted)."""
    return _make_order


@pytest.fixture
async def persisted_order(db_session: AsyncSession) -> Order:
    """A persisted Order for testing."""
    order = _make_order()
    db_session.add(order)
    await db_session.flush()
    await db_session.refresh(order)
    return order
