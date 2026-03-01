from __future__ import annotations

import base64
from typing import TYPE_CHECKING

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from genhealth.core.config import get_settings

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.types import ASGIApp

logger = structlog.get_logger()

# Paths that bypass auth (Railway healthcheck must stay accessible)
_EXEMPT_PATHS = frozenset(["/api/v1/health"])


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """HTTP Basic Auth gate. Active only when BASIC_AUTH_PASSWORD is configured."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()

        if not settings.basic_auth_password or request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                username, _, password = decoded.partition(":")
                if username == settings.basic_auth_user and password == settings.basic_auth_password:
                    return await call_next(request)
            except (UnicodeDecodeError, ValueError):
                pass  # malformed credentials — fall through to 401

        logger.info("basic_auth_rejected", path=request.url.path)
        return Response(
            content="Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="GenHealth"'},
        )
