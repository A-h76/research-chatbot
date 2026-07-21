# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

"Personal AI" (aka ResearchOS) — a private ChatGPT-style research/writing assistant. Flask backend (OpenAI Responses API, streaming) + a React/TypeScript SPA frontend. Google OAuth / magic-link / dev-login auth, Postgres (or SQLite for local dev), file upload + RAG pipeline with a Postgres-queue worker, and a "Prompt Engine" layer (domain routing, personas, model routing, memory, cost ledger).

## Commands

### Backend (Python)
```bash
pip install -r requirements.txt

python server.py                    # Flask app → http://localhost:5000
python worker.py                    # queue worker (needs Postgres; SQLite has no FOR UPDATE SKIP LOCKED)

pytest                              # full suite (tests are colocated: auth/test_*.py, backend/ai/test_*.py, etc., plus tests/ and root-level test_*.py)
pytest path/to/test_file.py         # single file
pytest path/to/test_file.py::test_name   # single test
pytest -k "some_expr"               # by name expression

flake8 .                            # lint (max-line-length 120, see .flake8 for ignored codes)
black .                             # format (line-length 120)
isort .                             # import sort (black profile)
```

A few packages (`storage/`, `imports/`) also ship dependency-free, framework-free self-checks runnable directly, useful as a fast pre-flight before the full DB-backed suite:
```bash
python -m storage.test_storage
python -m imports.test_imports
```

CI (`.github/workflows/ci.yml`) runs `flake8 . --count --max-complexity=20 --statistics` and `pytest -v` against real Postgres 15 + Redis 7 services — this codebase avoids mocking storage/queue/DB in tests (see Constitution principle 10 below), so most non-trivial tests expect a real Postgres, not SQLite. `conftest.py` at the repo root points `DATABASE_URL` at an isolated temp SQLite file before any test module imports `server.py` (which runs `Base.metadata.create_all()` at import time) — don't duplicate that env-var-setting in individual test files, the root conftest already guarantees it runs first.

### Frontend (`frontend/`)
```bash
cd frontend
npm install
npm run dev       # Vite dev server, http://localhost:5173, proxies /api /auth /login to :5000
npm run build      # tsc -b && vite build → frontend/dist, served by Flask in production
npm run lint        # oxlint
npm test           # vitest run
```

## Architecture

### The `import server` constraint (read this before adding a module)

`server.py` is a ~5,000+ line Flask monolith run directly as `__main__` (`python server.py`), and it owns every SQLAlchemy model (`User`, `Conversation`, `UploadJob`, `PromptVersion`, etc. — all defined inline in `server.py`, not in a models package). Because it's the entry point, **no module it imports may `import server` back** — that would import the file a second time under a different module identity and re-execute the whole thing (hit and fixed for real once; see `auth/magic_link.py`'s docstring).

The fix used everywhere (`auth/`, `quotas/`, `backend/*`): modules expose a **factory function** taking explicit dependencies (`SessionLocal`, model classes, `select`, other services) rather than importing them, e.g. `create_get_current_user(SessionLocal, User)`, `create_magic_link_blueprint(secret_key=..., SessionLocal=..., User=..., ...)`, `create_documents_blueprint(...)`. `server.py` itself does the wiring: imports the factory, calls it with its own live objects, registers the resulting blueprint. When adding a new module that needs DB access or other server state, follow this pattern — don't reach for `import server`.

Blueprint registration order in `server.py` matters: some blueprints (documents, search) are deferred until after `model_router`/`PromptExecution` exist further down the file — check the comment at the import site before moving registration code.

### Two storage abstractions — not a duplicate, two different consumers
- `storage/` (root) — the original document-upload storage layer (`StorageProvider` interface, `LocalProvider`/`R2Provider`, `StorageManager`, checksums, GC/reconcile). Used by the primary upload pipeline in `server.py`.
- `backend/storage/` — a separate `StorageBackend` interface (`LocalBackend`/`R2Backend`/`S3Backend`, `get_storage_backend()` factory) used by the newer `backend/upload` blueprint (Bearer-JWT document upload, bulk upload).

Check which one a given call site already uses before adding storage code — don't assume they're interchangeable.

### `backend/` package — the newer, blueprint-based layer
Everything under `backend/` follows the factory/DI pattern above and is wired into `server.py` via `register_blueprint(create_X_blueprint(...))`:
- `backend/ai/` — the "Prompt Engine": `domain_registry` (routes a query to a domain), `persona_engine`, `model_router` (task_name → model string; distinct from `model_registry`, which does provider dispatch — the two compose: `registry.call(router.get_model_for_task(...), ...)`), `prompt_builder`/`prompt_registry`, `memory_engine`, `cost_ledger`, `analytics`. Design doc: `docs/prompt-engine-architecture.md`.
- `backend/upload/` — Bearer-JWT document upload (`routes.py`) and bulk upload (`bulk.py`), reusing `server.py`'s `UserFile`/`UploadJob`/`OutboxEvent` models rather than defining new ones.
- `backend/search/`, `backend/prompts/` — their own blueprint factories.

### `worker.py` — the queue
Postgres-backed job queue using `FOR UPDATE SKIP LOCKED` (no Celery, no separate broker — deliberate, see ADR-001 draft in `docs/00-constitution.md`). Job types are dispatched via a `HANDLERS` dict (`worker.py`); add a new job type by adding a handler function and registering it there, not with a new dispatch mechanism. Retry uses exponential backoff with a dead-letter (`failed`) terminal state after `WORKER_MAX_ATTEMPTS`. A transactional outbox (`OutboxEvent`) decouples "job was created" from "job was dispatched." Job status optionally mirrors to Redis (`job:{id}:status`, 1h TTL) purely as a cache — Postgres's `upload_jobs` row is always the source of truth; every read path degrades gracefully if Redis is absent.

### `imports/` — document text extraction
`imports/registry.py` dispatches to an ordered list of `Importer` implementations (`imports/importers/*.py`) by matching filename/mime — order matters (e.g. `EpubImporter` must precede `ZipImporter` since an epub's mimetype contains "zip"). Adding a new file format means adding a new `Importer` and inserting it at the right point in `_IMPORTERS`, not touching a dispatch chain.

### Migrations
Raw SQL files in `migrations/`, run via `run_migrations.py` (tracked in a `schema_migrations` table). They assume `users`/`projects`/`conversations`/`files` already exist — those four are created by `server.py`'s own `Base.metadata.create_all()`, not by any migration file. Boot order matters: for a genuinely fresh DB, `server.py` must create the core tables before `run_migrations.py` runs the numbered migrations, then `backfill.py` populates seed data. See `docs/testing-guide.md` §3.2 for the exact sequence and its known ordering gap.

### Frontend
React 19 + TypeScript + Tailwind v4 + shadcn/ui (`@base-ui/react`) + Framer Motion, built with Vite. `frontend/src/features/*` is organized by product area (chat, papers, search, memory, projects, citations, dashboard, writing, ...); `frontend/src/routes/router.tsx` + `RootLayout.tsx` for routing; `frontend/src/lib/apiClient.ts`/`sse.ts` for backend calls and streaming. In dev, Vite (`:5173`) proxies `/api`, `/auth`, `/login` to Flask (`:5000`); in production Flask serves the built `frontend/dist` as static files.

## Design constraints worth knowing before writing new backend code

From `docs/prompt-engine-architecture.md` §1, proven necessary by real past bugs, not style preference:
1. Never `import server` (see above).
2. Structured data goes in `Text` columns, JSON-serialized by the application — not SQLAlchemy `JSON`/`JSONB` types (matches `UserFile.tags`, `OutboxEvent.payload`, etc.).
3. No SQLAlchemy `ForeignKey` across a private `Base` (e.g. a new package's own declarative base) and `server.py`'s real `Base` — use a plain `Integer` column instead and add the real FK constraint only at the raw-SQL migration level. A `ForeignKey` between two tables on the *same* private Base is fine.
4. `create_all(checkfirst=True)` creates tables, never columns — a schema change to an existing table needs a migration file, not just an edited model class.

## `docs/00-constitution.md`

Binding architecture principles for this repo — read it before any structural change (new dependency, rewrite of a working module, new cross-cutting concern). Key points not obvious from the code alone:
- **No rewrites without an ADR** (`docs/adr/NNNN-title.md`) — extend existing interfaces (`Importer`, `StorageProvider`, `worker.py`'s `HANDLERS`) instead of replacing them wholesale.
- Dependency inversion is uneven today by design, not oversight: storage backends and (mostly) the database are already swappable; queues (`worker.py` calls Postgres-specific APIs directly) and LLM providers (`OpenAI` client constructed once at module load, called directly from many functions) are not, and that gap is named as a known, deliberately-deferred debt rather than something to silently "fix" as a drive-by.
- Real containers (Postgres, Redis) over mocks for integration tests — mocked storage/queue tests previously hid real bugs (presigned-URL round trip, FK ordering, Redis key encoding) that only appeared against real infrastructure.

## Other docs worth checking before large changes
- `docs/database-design.md` — schema/table reference.
- `docs/api-contract.md` — API surface.
- `docs/upload-architecture.md`, `docs/processing-pipeline-architecture.md` — upload/job pipeline detail beyond the summary above.
- `docs/testing-guide.md` — tiered manual test plan (self-checks → SQLite app boot → full Postgres+Redis+worker pipeline), including the exact migration bootstrap sequence and other known gaps.
