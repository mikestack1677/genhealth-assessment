from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from genhealth.api.v1.routes.activity import router as activity_router
from genhealth.api.v1.routes.documents import router as documents_router
from genhealth.api.v1.routes.health import router as health_router
from genhealth.api.v1.routes.orders import router as orders_router
from genhealth.core.logging import setup_logging
from genhealth.middleware.activity_log import ActivityLogMiddleware

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    from genhealth.core.database import dispose_engine, init_engine

    logger = structlog.get_logger()
    logger.info("starting_up")
    await init_engine()
    yield
    await dispose_engine()
    logger.info("shutting_down")


def create_app() -> FastAPI:
    from genhealth.core.config import get_settings

    settings = get_settings()
    setup_logging(log_level=settings.log_level)

    limiter = Limiter(key_func=get_remote_address)

    application = FastAPI(
        title="GenHealth",
        description="GenHealth assessment: document extraction API",
        version="0.1.0",
        lifespan=lifespan,
    )

    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # CORS — allow all origins for assessment
    application.add_middleware(
        CORSMiddleware,  # type: ignore[arg-type]
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.add_middleware(ActivityLogMiddleware)  # type: ignore[arg-type]

    application.include_router(health_router, prefix="/api/v1", tags=["health"])
    application.include_router(orders_router, prefix="/api/v1", tags=["orders"])
    application.include_router(documents_router, prefix="/api/v1", tags=["documents"])
    application.include_router(activity_router, prefix="/api/v1", tags=["activity"])

    return application


app = create_app()
