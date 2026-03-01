.PHONY: lint lint-backend lint-backend-fix lint-frontend lint-frontend-fix \
        format format-backend format-backend-check format-frontend format-frontend-check \
        typecheck typecheck-backend typecheck-frontend \
        test test-backend test-frontend \
        check dev up down clean migrate migrate-create

# ── Backend ──────────────────────────────────────────────────────────────────

lint-backend:
	cd backend && uv run ruff check .

lint-backend-fix:
	cd backend && uv run ruff check --fix .

format-backend:
	cd backend && uv run ruff format .

format-backend-check:
	cd backend && uv run ruff format --check .

typecheck-backend:
	cd backend && uv run ty check

test-backend:
	cd backend && uv run pytest --cov=src/genhealth --cov-report=term-missing --cov-fail-under=90

# ── Frontend ──────────────────────────────────────────────────────────────────

lint-frontend:
	cd frontend && pnpm biome ci .

lint-frontend-fix:
	cd frontend && pnpm biome check --write .

format-frontend:
	cd frontend && pnpm biome check --write .

format-frontend-check:
	cd frontend && pnpm biome ci .

typecheck-frontend:
	cd frontend && pnpm tsc --noEmit

test-frontend:
	cd frontend && pnpm vitest run --coverage

# ── Aggregates ────────────────────────────────────────────────────────────────

lint: lint-backend lint-frontend

format: format-backend format-frontend

typecheck: typecheck-backend typecheck-frontend

test: test-backend test-frontend

check: lint format-backend-check format-frontend-check typecheck test

# ── Infrastructure ────────────────────────────────────────────────────────────

up:
	docker compose up -d

down:
	docker compose down

dev: up
	@echo "PostgreSQL is up. Start services separately:"
	@echo "  cd backend && uv run uvicorn genhealth.main:app --reload --port 8000"
	@echo "  cd frontend && pnpm dev"

clean:
	docker compose down -v
	rm -rf backend/.venv frontend/node_modules

# ── Database ──────────────────────────────────────────────────────────────────

migrate:
	cd backend && uv run alembic upgrade head

migrate-create:
	cd backend && uv run alembic revision --autogenerate -m "$(name)"
