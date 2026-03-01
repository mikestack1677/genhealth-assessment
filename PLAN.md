# GenHealth Assessment — Implementation Plan

## Assignment Summary

Build and publicly deploy a REST API (with optional frontend) that:
- Performs CRUD operations on an **Order** entity
- Accepts uploaded PDFs and extracts patient **first name**, **last name**, and **date of birth** via LLM
- Logs all user activity to the database
- Is accessible via a public URL (hard requirement — no URL = disqualified)

---

## Technology Decisions

### Backend

| Concern | Choice | Rationale |
|---|---|---|
| Language / framework | Python 3.12 + FastAPI | Required by assessment |
| Package manager | uv | Fast, deterministic, lockfile-based |
| ORM | SQLAlchemy 2.0 (async, `Mapped[]` style) | Type-safe, async-native, db-agnostic schema |
| Migrations | Alembic | First-class SQLAlchemy integration |
| Database (local + prod) | PostgreSQL 16 | Same engine everywhere — no SQLite-to-Postgres surprises |
| PDF extraction | Anthropic Claude API (`claude-sonnet-4-6`) | Native PDF understanding; robust against unseen document formats |
| Structured logging | structlog (JSON output) | Machine-readable, consistent log shape |
| Linting | ruff (50+ rule categories) | Replaces black + isort + flake8 in one binary |
| Type checking | ty | Fast, strict |
| Testing | pytest + pytest-asyncio + pytest-cov | Real PostgreSQL in tests; 90% coverage enforced |

### Frontend

| Concern | Choice | Rationale |
|---|---|---|
| Framework | Vite + React 19 + TypeScript (strict) | Required by assessment; strict mode catches bugs early |
| Package manager | pnpm | Fast, disk-efficient |
| Linting / formatting | Biome | Single Rust binary, replaces ESLint + Prettier |
| Server state | TanStack Query | Caching, loading states, refetch — free |
| Client state | Zustand | Lightweight; no Redux ceremony |
| Testing | Vitest + React Testing Library | Fast, Vite-native |

### Deployment

| Concern | Choice | Rationale |
|---|---|---|
| Platform | Railway.app | Free tier, no sleep, GitHub deploy in ~2 min |
| Database | Railway PostgreSQL plugin | Free, persistent, zero config |
| Secrets | Railway environment variables | `ANTHROPIC_API_KEY`, `DATABASE_URL` never committed |

---

## MVP Feature Prioritisation

The assessment lists 24 concepts. Below is an honest prioritisation for a
production-grade MVP delivered under time constraints.

### In (essential for production MVP)

| Feature | Implementation |
|---|---|
| **CRUD for Order** | Full REST resource at `/api/v1/orders` |
| **PDF extraction** | `POST /orders/{id}/document` + `POST /documents/extract` via Claude API |
| **Activity logging** | FastAPI middleware — every request/response logged automatically, zero per-route boilerplate |
| **Request validation** | Pydantic schemas on all request/response bodies |
| **Error handling** | Structured error responses; LLM errors handled separately (see below) |
| **LLM error handling** | Retry with exponential backoff (max 2 retries); fast-fail on non-retryable errors |
| **LLM rate limiting** | `slowapi` on extraction endpoints (10 req/min per IP); `max_tokens=256` cap per call |
| **Environment config** | `pydantic-settings` + `.env`; `.env.example` committed, `.env` gitignored |
| **API versioning** | All routes under `/api/v1/` |
| **ORM + separation of concerns** | Repository layer (data access) → Service layer (business logic) → Route layer (HTTP) |
| **Documentation** | FastAPI auto-generates OpenAPI/Swagger at `/docs`; README covers setup + deploy |
| **Code structure** | Layered architecture enforced; no business logic in routes |
| **Unit + integration tests** | 90% coverage minimum; real PostgreSQL via session-scoped engine |
| **Deployment** | Railway — public URL required for submission |
| **Tasteful UI / UX** | React frontend: order list, upload flow, activity log viewer |

### Out (diminishing returns within time budget)

| Feature | Reason |
|---|---|
| **Authentication / user management** | Significant complexity; not in requirements; can layer on later |
| **Caching** | Premature at MVP scale |
| **App-level rate limiting (non-LLM)** | Railway handles at infrastructure level |
| **Batch processing** | Not mentioned in requirements |
| **Asynchronous background processing** | Sync LLM calls are acceptable at MVP scale; adds queue complexity |
| **Scalability / horizontal scaling** | Single Railway instance is fine for assessment demo |

---

## Architecture

```
genhealth_assessment/
  backend/
    src/genhealth/
      api/v1/routes/        # orders.py, documents.py, activity.py, health.py
      core/                 # config.py, database.py, logging.py
      middleware/           # activity_log.py
      models/               # order.py, activity_log.py
      repositories/         # order_repository.py, activity_repository.py
      schemas/              # order.py, document.py, activity_log.py
      services/             # order_service.py, document_service.py, activity_service.py
      main.py
    tests/
      conftest.py           # session-scoped engine, per-test rollback, factory fixtures
      test_orders.py
      test_documents.py
      test_activity.py
    alembic/
    pyproject.toml
    Dockerfile
  frontend/
    src/
      api/                  # client.ts, orders.ts, documents.ts
      components/           # OrderTable, OrderForm, UploadCard, ActivityFeed, Layout
      pages/                # OrdersPage, OrderDetailPage
      providers/            # QueryProvider, ThemeProvider
      styles/
      App.tsx
      main.tsx
    biome.json
    vite.config.ts
    vitest.config.ts
    tsconfig.json
    package.json
  docker-compose.yml        # PostgreSQL 16 only — no Redis, no auth service
  railway.toml
  Makefile
  .env.example
  README.md
  PLAN.md                   # this file
```

---

## Data Model

### Order

```python
class Order(Base):
    id:                   Mapped[UUID]          # UUIDv7 (high-write)
    patient_first_name:   Mapped[str | None]
    patient_last_name:    Mapped[str | None]
    patient_dob:          Mapped[date | None]
    status:               Mapped[OrderStatus]   # PENDING | PROCESSING | COMPLETED
    notes:                Mapped[str | None]
    document_filename:    Mapped[str | None]
    extracted_data:       Mapped[dict | None]   # raw LLM JSON response
    created_at:           Mapped[datetime]
    updated_at:           Mapped[datetime]
```

### ActivityLog

```python
class ActivityLog(Base):
    id:              Mapped[UUID]        # UUIDv7
    method:          Mapped[str]         # GET, POST, PUT, DELETE
    path:            Mapped[str]
    status_code:     Mapped[int]
    request_summary: Mapped[str | None]  # sanitised (no file bytes)
    order_id:        Mapped[UUID | None] # nullable FK → orders.id
    duration_ms:     Mapped[int]
    timestamp:       Mapped[datetime]
```

---

## API Surface

```
GET    /api/v1/health                   Health check
GET    /api/v1/orders                   List orders (paginated: ?page=1&page_size=20)
POST   /api/v1/orders                   Create order
GET    /api/v1/orders/{id}              Get order
PUT    /api/v1/orders/{id}              Update order
DELETE /api/v1/orders/{id}              Delete order
POST   /api/v1/orders/{id}/document     Upload PDF → extract → update order fields
POST   /api/v1/documents/extract        Standalone extraction (no order required)
GET    /api/v1/activity                 List activity logs (paginated)
```

---

## LLM Guardrails

Protecting against runaway API costs:

| Guardrail | Value | Enforcement point |
|---|---|---|
| Max file size | 10 MB | Route-level validation before any processing |
| Max pages | 20 pages | `pypdf` page count check before sending to Claude |
| Content-type | `application/pdf` only | Route-level validation |
| `max_tokens` | 256 | Claude API call parameter — first name + last name + DOB is ~30 tokens |
| Extraction rate limit | 10 requests / minute / IP | `slowapi` middleware on extraction endpoints |
| Max retries | 2 (exponential backoff) | On transient errors (429, 529) only |
| Request timeout | 30 seconds | Claude API call timeout |
| Fast-fail | Immediate | On 400, 401 — no retry |

---

## Quality Standards

Mirrors the project's established conventions:

- **ruff** with 50+ rule categories (identical config to Narthex project)
- **ty** for type checking — no `# type: ignore` without specific error code + reason
- **No lint suppression in config files** — targeted inline `# noqa: RULE — reason` only
- **No `any` in TypeScript** — use `unknown` + narrowing
- **90% test coverage** enforced (`--cov-fail-under=90` backend; vitest thresholds frontend)
- **Real PostgreSQL in tests** — never SQLite; session-scoped engine + per-test transaction rollback
- **`make check`** runs everything: lint + format check + typecheck + tests

---

## Deployment

1. Push to GitHub (`mikestack1677/genhealth-assessment`)
2. Create Railway project → "Deploy from GitHub"
3. Add Railway PostgreSQL plugin
4. Set environment variables:
   - `ANTHROPIC_API_KEY`
   - `DATABASE_URL` (auto-injected by Railway)
   - `ENVIRONMENT=production`
5. Railway builds via `Dockerfile`, runs Alembic migrations on startup
6. Public URL available immediately

---

## What This Demonstrates

- **Decision-making under constraints** — auth deferred deliberately; LLM cost controls added proactively
- **Production thinking** — activity logging via middleware, not manual calls; LLM guardrails before a line of extraction code
- **Consistent quality** — same toolchain and standards as production codebases
- **Full-stack delivery** — working backend + tasteful frontend + live deployment
