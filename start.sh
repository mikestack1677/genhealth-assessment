#!/bin/sh
set -e
echo "Running migrations..."
alembic upgrade head
echo "Starting server on port ${PORT:-8000}..."
exec uvicorn genhealth.main:app --host 0.0.0.0 --port "${PORT:-8000}"
