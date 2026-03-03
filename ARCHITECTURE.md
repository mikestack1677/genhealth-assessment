# GenHealth Assessment — Architecture Overview

## What We Built

A full-stack order management system with AI-powered document extraction, deployed to a public URL on Railway.

- **Backend:** FastAPI (Python 3.12), SQLAlchemy 2.0 (async), PostgreSQL 16, Alembic migrations
- **Frontend:** React 19 + TypeScript (strict mode), Vite, TanStack Query, Biome
- **LLM:** Pluggable provider architecture (Anthropic Claude / Google Gemini) for PDF-to-patient-data extraction
- **Deployment:** Multi-stage Dockerfile on Railway; Alembic migrations run at container startup
- **Testing:** 44 backend tests (91% coverage), 105 frontend tests (97% coverage)

Live at: `https://genhealth-assessment-production.up.railway.app`

---

## Architecture

```
Browser ─────► Railway (HTTPS)
                 │
                 ▼
         ┌──────────────┐
         │  FastAPI App  │
         │               │
         │  Middleware:   │
         │  - Basic Auth  │  ◄── optional; enabled via BASIC_AUTH_PASSWORD env var
         │  - CORS        │
         │  - Activity Log │  ◄── every request/response logged to DB automatically
         │               │
         │  Routes:      │
         │  /api/v1/     │
         │  ├─ orders    │──► OrderService ──► OrderRepository ──► PostgreSQL
         │  ├─ documents │──► DocumentService ──► LLMProvider (ABC)
         │  ├─ activity  │──► ActivityService ──► ActivityRepository ──► PostgreSQL
         │  └─ health    │
         │               │
         │  Static files:│
         │  /* (SPA)     │──► Built React app served from /static
         └──────────────┘
                 │
                 ▼
         ┌──────────────┐         ┌──────────────────┐
         │ PostgreSQL 16 │         │ LLM Provider     │
         │ (Railway)     │         │ ┌──────────────┐ │
         │               │         │ │ Anthropic    │ │  ◄── active (LLM_PROVIDER=anthropic)
         │ Tables:       │         │ │ Claude API   │ │
         │ - orders      │         │ └──────────────┘ │
         │ - activity_log│         │ ┌──────────────┐ │
         │ - alembic_ver │         │ │ Gemini       │ │  ◄── available (LLM_PROVIDER=gemini)
         └──────────────┘         │ │ Google AI    │ │
                                  │ └──────────────┘ │
                                  └──────────────────┘
```

### Layered Architecture

Every request flows through the same layers:

1. **Route** — HTTP concerns only: parse request, validate input, return response
2. **Service** — Business logic: orchestrates operations, enforces rules
3. **Repository** — Data access: SQLAlchemy queries, pagination
4. **Model** — SQLAlchemy ORM entities with typed `Mapped[]` columns

No business logic in routes. No HTTP concepts in services. No raw SQL anywhere.

### LLM Provider Design

Document extraction is behind an abstract `LLMProvider` base class:

```python
class LLMProvider(ABC):
    @abstractmethod
    async def extract(self, pdf_bytes: bytes, filename: str) -> str: ...
```

Concrete implementations (`AnthropicProvider`, `GeminiProvider`) handle retries, rate limits, and API-specific details. The active provider is selected by a single env var (`LLM_PROVIDER`). This was a deliberate refactor — we started with Anthropic only, then needed to switch to Gemini when API credits ran out. The abstraction let us swap providers with zero changes to `DocumentService`.

---

## Assessment Categories — Evaluation

The assessment listed 24 concepts to consider. Here's what we did with each one, and why.

### Implemented

| Category | What We Did |
|---|---|
| **Request Validation** | Pydantic schemas on every request/response body. FastAPI returns 422 with field-level errors automatically. Pagination parameters validated with `Query(ge=1, le=100)` to prevent abuse. |
| **Endpoint Versioning** | All routes under `/api/v1/`. Adding `/api/v2/` later requires no changes to existing consumers. |
| **Tasteful UI/UX** | Full React frontend: order table with pagination, inline create/edit forms, drag-and-drop PDF upload with extraction preview, activity log page, dark/light theme toggle. Not a throwaway — it's componentized and tested. |
| **Componentization** | Frontend split into focused components (`OrderTable`, `OrderForm`, `UploadCard`, `ActivityFeed`, `Pagination`, `Layout`), each with its own CSS module and test file. Backend split into routes/services/repositories/schemas/models. |
| **Error Handling** | Structured error responses throughout. LLM errors distinguished from application errors. Frontend mutation hooks surface errors to the user via alert messages. `try/catch` with typed error narrowing, not silent swallowing. |
| **Code Structure and Design** | Layered architecture (route → service → repository → model). No circular dependencies. Single-responsibility modules. Factory pattern for LLM provider selection. |
| **Rate Limiting** | `slowapi` configured on extraction endpoints (10 req/min per IP). `max_tokens=256` cap on LLM calls to control cost. |
| **Environment Configuration** | `pydantic-settings` reads from env vars and `.env` files. All secrets (`ANTHROPIC_API_KEY`, `DATABASE_URL`, `BASIC_AUTH_PASSWORD`) are env-var-driven, never committed. `.env.example` documents all available settings. |
| **Deployment** | Multi-stage Dockerfile: Node 22 builds the React frontend, Python 3.12-slim runs the backend. Alembic migrations run at container startup via `start.sh`. Railway healthcheck at `/api/v1/health`. Live and publicly accessible. |
| **Unit Testing** | 105 frontend tests (Vitest + React Testing Library), 44 backend tests (pytest + pytest-asyncio). Coverage enforced: 85% branch minimum (frontend), 90% statement minimum (backend). Tests run against real PostgreSQL, not SQLite. |
| **Integration Testing** | Backend tests use `httpx.AsyncClient` with ASGI transport — full request/response cycle through FastAPI middleware, validation, and database. Frontend tests render full component trees with mocked API boundaries. |
| **Endpoint Structure** | RESTful resource design: `GET/POST /orders`, `GET/PUT/DELETE /orders/{id}`, `POST /orders/{id}/document`, `POST /documents/extract`, `GET /activity`. Consistent response shapes via Pydantic `response_model`. |
| **LLM Rate Limiting** | Per-IP rate limiting via `slowapi` on extraction endpoints. File size cap (10MB), page count cap (20 pages), and `max_tokens` (256) prevent cost blowout. |
| **LLM Error Handling** | Retry with exponential backoff on transient errors (429, 5xx). Immediate fail on auth errors (401) and bad requests (400). Provider-specific error handling in each `LLMProvider` implementation. Timeout of 30s per call. |
| **Object Relational Mapping** | SQLAlchemy 2.0 with async engine, `Mapped[]` type annotations, UUIDv7 primary keys, and Alembic for migrations. Same PostgreSQL engine in dev, test, and production — no ORM dialect surprises. |
| **Separation of Concerns** | Routes handle HTTP. Services handle logic. Repositories handle queries. Middleware handles cross-cutting concerns (logging, auth). LLM providers handle API-specific details. Each layer is independently testable. |
| **Security** | HTTP Basic Auth middleware (optional, env-var-gated). CORS configured. Pagination bounds enforced to prevent full-table-scan abuse. No secrets in code or Docker image. Healthcheck exempt from auth so Railway deploys keep working. |
| **Documentation** | FastAPI auto-generates OpenAPI/Swagger at `/docs`. `PLAN.md` documents architecture decisions and trade-offs. `README.md` covers local setup and deployment. This document covers the full architecture review. |

### Partially Implemented

| Category | Status | Notes |
|---|---|---|
| **Asynchronous Processing** | Partial | The entire backend is async (`async def` routes, `AsyncSession`, `async` LLM providers). However, extraction is still request-synchronous — the caller waits for the LLM response. A production system would queue extraction as a background job and notify on completion. See "Next Steps" below. |
| **Scalability** | Partial | The async architecture supports high concurrency on a single instance. Pagination prevents unbounded queries. But there's no horizontal scaling, connection pooling tuning, or read replicas. For an assessment demo, a single Railway instance is appropriate. |
| **Caching** | Partial | TanStack Query handles client-side caching (stale-while-revalidate, background refetch). No server-side caching. Adding Redis for extracted-document caching would be the logical next step if extraction volume warranted it. |

### Deliberately Deferred

| Category | Why | When We'd Add It |
|---|---|---|
| **Authentication and Authorization** | Significant complexity (JWT/OAuth, token refresh, RBAC, session management) for zero ROI in a single-user demo. We added Basic Auth as a lightweight access gate instead. | **Sprint 2.** Add OAuth2 with JWT tokens, role-based access control, and per-user activity logs. This is the single highest-priority addition for any multi-user deployment. |
| **User Management** | Depends on authentication. No users = no user management. | **Sprint 2**, alongside auth. User model, registration, profile endpoints. |
| **Batch Processing** | Not in the core requirements. Single-document extraction covers the stated use case. | **Sprint 3.** Add a `/documents/extract-batch` endpoint that accepts multiple PDFs, queues them, and returns a batch ID for polling. Requires the async job queue (see below). |

---

## What We'd Prioritize Next

If this were a real product roadmap, here's how we'd sequence the remaining work:

### Sprint 2: Security and Auth
1. **OAuth2 / JWT authentication** — FastAPI has excellent `OAuth2PasswordBearer` support. Add a `User` model, password hashing (bcrypt), token endpoints, and a `Depends(get_current_user)` guard on all routes.
2. **Role-based authorization** — Admin vs. standard user. Admins can delete orders and view all activity; standard users see only their own.
3. **Audit trail per user** — Extend `ActivityLog` with a `user_id` foreign key.

### Sprint 3: Resilience and Scale
4. **Background job queue** — Move LLM extraction to a Celery/ARQ worker. The API returns 202 Accepted with a job ID; the frontend polls or uses WebSocket for completion. This eliminates the 30-second synchronous wait.
5. **Server-side caching** — Redis cache for repeated extractions of the same document (hash PDF content → cache key).
6. **Horizontal scaling** — Multiple Railway instances behind a load balancer. Requires moving session state (if any) out of process.

### Sprint 4: Testing and Observability
7. **End-to-end tests** — Playwright tests for the critical user flows: create order, upload PDF, verify extraction, edit order, delete order. We evaluated adding E2E in this assessment but determined that a half-finished Playwright setup (install, config, write tests, CI integration) would signal "unfinished" rather than "thoughtful." The unit and integration test coverage (105 + 44 tests) provides strong confidence in the meantime.
8. **Structured observability** — OpenTelemetry traces, Prometheus metrics. The `structlog` JSON logging is a good foundation but doesn't give request waterfall visibility.

---

## Ideas We Explored But Didn't Ship

These came up during development or code review and are worth discussing:

| Idea | What Happened | Verdict |
|---|---|---|
| **Google Gemini free tier** | Built a full `GeminiProvider` implementation. Discovered that Google's free tier requires billing to be attached to the GCP project — all model quotas showed `limit: 0`. Switched back to Anthropic ($5 credits, ~$0.02/extraction). | The provider abstraction is still valuable — swapping LLMs is a one-env-var change. Worth keeping for cost optimization later. |
| **E2E testing with Playwright** | Evaluated adding it. Playwright setup + config + meaningful tests + CI wiring is a 30-45 minute job to do properly. With limited time remaining, we chose to ship 5 high-priority bug fixes instead. | Next priority after auth. The test pyramid is solid at the unit/integration layers; E2E would cover the deployment-specific integration points. |
| **Full authentication** | Designed but deferred. Added HTTP Basic Auth as a lightweight gate instead — it protects the public URL without the complexity of JWT token management, refresh flows, and user registration. | Basic Auth is the right tool for "protect a demo app." Real auth is Sprint 2 work. |
| **Background extraction queue** | Considered ARQ (async Redis queue) for PDF processing. Decided synchronous extraction is acceptable at demo scale — adds 2-5 seconds per request, and there's no concurrent user load. | Necessary before any real multi-user deployment. The `DocumentService` abstraction makes this a clean refactor — swap `await provider.extract()` for `await queue.enqueue(extract_job)`. |
| **CORS tightening** | Started with `allow_origins=["*"]` + `allow_credentials=True` (spec-invalid). Fixed `allow_credentials` to `False` during code review. In production, `allow_origins` should be locked to the actual frontend domain. | Quick fix once a stable domain is established. |

---

## Code Review Findings (Addressed)

During the assessment, we ran a parallel code review with three specialized agents. Key findings we fixed before submission:

- **PATCH vs PUT mismatch** — Frontend sent `PATCH` but backend registered `PUT`. Edit order was broken in production. Fixed.
- **CORS misconfiguration** — `allow_credentials=True` with wildcard origin violates the spec. Fixed.
- **AsyncMock** — Test fixture used `MagicMock` for an async interface. Fixed.
- **Pagination bounds** — No upper limit on `page_size`. Added `ge=1, le=100` constraints.
- **Focus ring removal** — `outline: none` on form inputs violated WCAG 2.4.7. Replaced with visible focus rings.
- **Branch coverage drop** — New feature (auto-create from extraction) added untested branches. Added 5 tests to restore coverage above threshold.

### Known Issues Not Yet Addressed

- Raw exception strings in some 422 responses could leak internal details to end users
- `updated_at` only enforced at ORM level, not via DB trigger
- Node 22 in Dockerfile vs Node 24 in CI (version mismatch, no functional impact)
- CSS skeleton loading styles duplicated between `OrderTable` and `ActivityFeed`
- `DocumentExtractionResponse` type has a `raw_response` field the backend never sends

These are low-severity and would be addressed in normal sprint work.

---

## Test Summary

| Suite | Tests | Coverage | Tool |
|---|---|---|---|
| Backend unit + integration | 44 | 91% statements | pytest, pytest-cov |
| Frontend unit + component | 105 | 97% statements, 87% branches | Vitest, React Testing Library |
| E2E | 0 | — | (Playwright planned, not implemented) |
| **Total** | **149** | | |

All tests run in CI on every push. Backend tests use a real PostgreSQL database with per-test transaction rollback. Frontend tests mock API boundaries but render full component trees.

---

## Running Locally

```bash
# Prerequisites: Python 3.12+, Node 20+, PostgreSQL, uv, pnpm

# Backend
cd backend
cp .env.example .env          # edit with your DB URL and API keys
uv sync
uv run alembic upgrade head
uv run uvicorn genhealth.main:app --reload

# Frontend
cd frontend
pnpm install
pnpm dev

# Full check (lint + typecheck + format + tests)
make check
```
