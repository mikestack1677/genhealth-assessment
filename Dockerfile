# ─── Frontend build ───────────────────────────────────────────────────────────
FROM node:22-slim AS frontend-builder

RUN npm install -g pnpm@10
WORKDIR /frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

# ─── Backend build ────────────────────────────────────────────────────────────
FROM python:3.12-slim AS backend-builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/src/ src/
RUN uv sync --frozen --no-dev --no-editable

# ─── Runtime ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim

RUN groupadd --gid 1000 appuser && useradd --uid 1000 --gid appuser --no-create-home appuser

WORKDIR /app

COPY --from=backend-builder /app/.venv /app/.venv
COPY --from=backend-builder /app/src /app/src
COPY --from=frontend-builder /frontend/dist /app/static
COPY backend/alembic.ini ./
COPY backend/alembic/ alembic/

ENV PATH="/app/.venv/bin:$PATH"
ENV STATIC_DIR=/app/static

# Startup script — handles Railway's $PORT injection and migration
RUN printf '#!/bin/sh\nset -e\nalembic upgrade head\nexec uvicorn genhealth.main:app --host 0.0.0.0 --port "${PORT:-8000}"\n' > /app/start.sh \
    && chmod +x /app/start.sh

USER appuser

CMD ["/bin/sh", "/app/start.sh"]
