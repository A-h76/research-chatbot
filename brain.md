# brain.md — project map & current state

Internal reference for whoever (human or Claude) picks this codebase up next.
`README.md` is the user-facing quick start; `docs/*.md` are the original
design docs (written before most of this was built, some now partially
superseded by what's actually running). This file is the third thing:
what's *actually in the repo right now*, how the pieces fit together, and
what's still rough. Written 2026-07-20, updated 2026-07-20 to add the AI
layer (§6), updated again same day (§2, §6, §8, §9) to add `backend/search/`
(JWT search + RAG) and `POST /api/documents/<id>/analysis`, which existed in
the repo but weren't documented yet; re-verify anything load-bearing before
trusting it — code drifts, this file doesn't auto-update.

Project is a single Flask app (`server.py`) + a React/TS SPA (`frontend/`).
Branded "Personal AI" in the UI; the repo/CI call it "ResearchOS" — same
project, two names in circulation, not a fork.

---

## 1. Directory map

```
server.py            Flask app, ~6,500 lines. Every DB model, most routes,
                      app config, and blueprint registration live here.
                      Runs as __main__ (python server.py) — see §3 gotcha.
worker.py             Standalone queue worker process (python worker.py).
                       Polls upload_jobs, requires real Postgres.
backfill.py           One-off data-migration/seed script.
run_migrations.py     Idempotent SQL migration runner (Postgres only).

auth/                 JWT + magic-link auth. Independent of Flask sessions.
quotas/                Storage/token quota checking & recording.
storage/                Legacy object-storage layer (Protocol-based). Still
                        the one server.py's core upload path and worker.py use.
imports/                 File-text-extraction importer registry (pdf/docx/
                         pptx/xlsx/epub/zip/text/legacy office).
backend/                Newer code, added for the JWT-auth API surface and
                        the AI layer:
  backend/storage/       ABC-based storage compat layer, wraps storage/.
  backend/upload/        POST /api/documents/upload + POST /api/documents/
                          <id>/analysis (Bearer-JWT routes), validation.py.
  backend/search/         GET /api/documents/search + POST /api/rag
                          (Bearer-JWT), reuses Chunk embeddings — see §6.
  backend/ai/             Prompt registry, multi-provider model registry,
                          cost ledger, DB seeding, shared prompt text
                          (prompts.py) — see §6.
observability/          JSON logging, correlation ids, Prometheus
                        metrics — shared by server.py and worker.py,
                        imports neither. See §12.

migrations/             Numbered .sql files (0001-0014), Postgres-only,
                        tracked via a schema_migrations table (see
                        run_migrations.py). Every statement is idempotent
                        (server.py must run before these ever can, per
                        FK deps — see §6) — verified end-to-end for real.
Procfile                web + worker process types (Heroku-style). See §5.
deploy/systemd/         Unit files for a plain-VM deploy. See §5.
docs/                   Pre-implementation design docs (architecture,
                        DB design, pipeline, hardening, API contract, UX,
                        shipping plan) + docs/adr/ (ADR-0001, unresolved).
frontend/               React 19 + TS + Vite + Tailwind + shadcn/ui SPA.
                        src/features/<domain>/ per feature area; src/lib/
                        apiClient.ts talks to the Flask API.
tests/                  test_ai.py (real tests, §6) alongside one
                        orphaned conftest.py — see §10, the latter is dead
                        scaffolding, safe to ignore.
templates/, static/     Login page HTML, robots.txt. Not the main UI.
.github/workflows/ci.yml  Lint (flake8) + test (pytest against real
                          Postgres+Redis service containers) on push/PR.
```

---

## 2. The two upload paths (read this before touching either)

There are **two** upload entry points, both writing to the same `UserFile`
(`files` table) and both ending up processed by the same `worker.py` —
they are not competing systems, they're two front doors to one pipeline:

| | `POST /api/files` | `POST /api/documents/upload` |
|---|---|---|
| Auth | Flask session (`@login_required`) | Bearer JWT (`@jwt_required()`) |
| Where | `server.py` directly | `backend/upload/routes.py` (blueprint) |
| Storage write | `storage.upload()` (legacy singleton) | `backend.storage.get_storage_backend()` |
| Allowed types | anything (images → vision path) | `.pdf/.epub/.docx/.txt` only |
| Quota | inline check against `MAX_STORAGE_MB` | `QuotaService.check_storage_quota` (403) |
| Dedup | checksum-based, skips re-upload | none |
| Used by frontend today | **yes** (`features/files/api.ts` → `postForm("/api/files", ...)`) | **no** — no `/api/documents` reference anywhere in `frontend/src` |

Both write `UploadJob(job_type="import", status="pending")` +
`OutboxEvent` in the same transaction as the file row (transactional
outbox), so `worker.py` picks up either one identically. Both routes'
`storage_backend` ultimately point at the **same R2 bucket** via
different client objects (`storage.r2_provider.R2Provider` vs.
`backend.storage.r2.R2Backend` — the latter literally wraps the former).

⚠️ **They must stay pointed at the same physical storage.** If `STORAGE_BACKEND`
is ever forced to `local` while `R2_BUCKET` stays set, `/api/documents/upload`
starts writing to local disk while `worker.py` (which reads via the legacy
`storage/` package) still looks in R2 — uploads silently never process. Leave
`STORAGE_BACKEND` blank (auto-detect) unless you also change the legacy
package's provider selection to match.

Same blueprint (`backend/upload/routes.py`) also owns `POST
/api/documents/<id>/analysis` — a **synchronous** counterpart to `/api/files/
<id>/analysis` (§8's Ops group): same `paper_analysis` prompt (shared by
name via `backend/ai/prompts.py`, not forked), same `PromptRegistry`/
`ModelRegistry`/`PaperAnalysis` row, but runs inline in the request instead
of via the queue/worker, and always regenerates (no `content_hash`
short-circuit — a caller hitting this endpoint wants a fresh answer now, not
"only if missing").

---

## 3. Auth — three login methods, one identity space, two credential types

- **Google OAuth** (`/auth/google`, `/auth/callback`) — primary login.
- **Dev auto-login** (`/api/dev-login`, or `DEV_AUTO_LOGIN` env bypass) — local dev only.
- **Magic link** (`auth/magic_link.py`, `POST /auth/magic-link` + `/verify`) — passwordless, email-allowlist gated, rate-limited, generic response regardless of allowlist match (no email enumeration).

All three set a Flask session **and** mint a JWT pair (`session["jwt"]`),
so a browser session and a Bearer token both resolve to the same
`User.id`. `GET /api/auth/jwt` hands a logged-in browser session a
portable token; `POST /api/auth/token` refreshes it.

- `@login_required` — session only (original, untouched decorator).
- `@jwt_required()` / `@jwt_optional` (`auth/decorators.py`) — Bearer only, sets `g.current_user` (a **string** user id).
- `get_current_user` (`auth/context.py`) — session-or-Bearer, session wins if both present. Not used by many routes yet; most of `server.py` still calls `@login_required` directly.

Every module under `auth/` and `quotas/` is **constructor-injected**
(`create_X(SessionLocal, User, ...)`), never `import server`. Reason:
`server.py` runs as `__main__`; anything it reaches into that imports
`server` back gets a second module identity and re-executes the whole
file, recursing infinitely. This bit us once (early magic-link draft),
now it's the standing pattern for every new module.

---

## 4. Quotas

`quota_service = QuotaService(SessionLocal, User, StorageUsage, UsageLog, select)`,
built once in `server.py`, injected into whatever needs it.

- `check_storage_quota(user_id, bytes)` / `check_token_quota(user_id, tokens)` — raise `QuotaExceededError`, caller decides the HTTP status (403).
- `increment_storage(user_id, bytes, delta_files=1)` — writes a `UsageLog` row **and** updates the live `StorageUsage.bytes_used`/`file_count` counters in one transaction (own session, not the caller's — best-effort from a caller already inside its own transaction, see `backend/upload/routes.py`'s comment on why it runs *after* that route's own commit).
- `increment_tokens` / `get_usage_summary` — token side, monthly rollover via `quota_reset_at` (lazy — rolls over on next access, not a cron job).

Only `/api/documents/upload` actually calls `QuotaService` today.
`/api/files` (the original route) still does its own inline check against
`MAX_STORAGE_MB` / `StorageUsage` directly — never migrated to
`QuotaService`. Both are correct, they just don't share code yet.

---

## 5. Background processing (`worker.py`)

Not Celery — a **Postgres-native queue**: `SELECT ... FOR UPDATE SKIP
LOCKED` on `upload_jobs`, linear backoff (`attempts * 60s`), dead-letter
after `WORKER_MAX_ATTEMPTS` (default 5). Refuses to start against
SQLite. Run with `python worker.py` — it is **not** started automatically
by `python server.py`; they're always two separate processes, in dev and
in prod.

**Process supervision**: a `Procfile` at the repo root (`web: python
server.py`, `worker: python worker.py`) covers Heroku-style platforms.
`deploy/systemd/*.service` covers a plain Linux VM — copy both units to
`/etc/systemd/system/`, adjust the placeholder paths/user, then
`systemctl enable --now researchos-web researchos-worker`. No
`docker-compose.yml` — this repo has deliberately stayed Docker-free for
dev (§11), and neither Postgres nor Redis is required locally, so a
compose stack would add infrastructure this project doesn't otherwise
need rather than solve a real gap.

**Health check**: worker.py upserts a single-row heartbeat
(`worker_heartbeats`, id=1) once per poll iteration. `GET
/api/worker/health` (unauthenticated — an ops probe, not a user route)
reads it and returns `200 {"status": "ok", ...}` if the heartbeat is
newer than `WORKER_HEALTH_THRESHOLD_SECONDS` (default 60s), `503
{"status": "down", ...}` if stale, `503 {"status": "unknown", ...}` if
the worker has never reported in at all. Point an uptime monitor or the
systemd unit's own health tooling at this — it's the only way to tell
"worker process crashed" apart from "no jobs happen to be queued right
now," which look identical from the outside otherwise. If jobs are
piling up as `pending` forever, check this endpoint first.

Job chain: `import` → (on success) enqueues `extract_metadata` +
`paper_analysis`. Handlers in `worker.py`'s `HANDLERS` dict, each fetches
the file via `server.storage.storage_manager.provider.local_copy(uf.path)`
— the **legacy** storage singleton, which is why §2's storage-backend
consistency warning matters.

`docs/adr/0001-queue-backend.md` is the still-open decision on whether to
stay on this or migrate to Celery per the constitution's original
Principle 6. Status: proposed, not decided. Treat the Postgres worker as
the real, current implementation regardless of what that doc says should
happen — code wins over an unresolved ADR.

---

## 6. AI layer (`backend/ai/`)

Newer, separate from everything server.py already did with OpenAI
(`responses_text()`, the streaming `/api/chat` path, `embed_texts()` —
all untouched). Built across several tasks; five files:

- **`models.py`** — `create_prompt_version_model(Base)` /
  `create_pipeline_version_model(Base)`: factories (not classes) for
  `prompt_versions` and `pipeline_versions`, the two tables migration
  0005 creates that never got a server.py ORM class. Deliberately does
  **not** define `ModelVersion`/`AIUsageLedger` — those already exist,
  live, in `server.py` (§7's Ops/usage group) — and there's no
  `PromptTemplate` class anywhere: 0005 is one flat `prompt_versions`
  table (rows grouped by a plain `name` column), not a parent/child pair.
- **`prompt_registry.py`** — `PromptRegistry(db_session)`:
  `create_prompt`/`add_version`/`get_prompt` (Jinja2-rendered, raises
  `ValueError` if missing, `TemplateError` if rendering fails)/
  `list_prompts`/`get_active_version`. Owns a **private** `declarative_base()`
  (module-level `_Base`, with `PromptVersion` instantiated against it) —
  separate from server.py's own `Base` — so its constructor only needs
  the injected `Session`, not a second "which mapped class" argument.
  Maps onto the real `prompt_versions` table by name, not by Base identity.
- **`model_registry.py`** — `ModelRegistry(db_session=None)`: unified
  `call(model, messages, fallback_models=None, **kwargs)` routing by
  prefix (`gpt-`/`o1`/`o3`/`o4` → OpenAI via Chat Completions, not the
  Responses API; `claude-` → Anthropic; `gemini-` → Google) plus
  `embed()`. 3 retries with exponential backoff, except 400/401/403/404
  (bad key/unsupported model/malformed request) which fail immediately —
  verified against each provider's *real* exception shape (Anthropic
  uses `.status_code`, google-genai only has `.code`, both confirmed by
  actually triggering real auth failures against live servers). Also
  owns a private `_Base` (`CostLedgerEntry` instantiated against it).
- **`cost_ledger.py`** — `CostLedger(Model)`: `estimate_cost(model,
  prompt_tokens, completion_tokens)` (pure, no DB) + `log(db_session,
  ...)` (writes a row). Pricing table only covers models with
  confident, publicly documented rates (`gpt-4o`/`gpt-4o-mini`/
  `gpt-4-turbo`/`gpt-4`/`gpt-3.5-turbo`, the `claude-3-5`/`claude-3`
  family) — anything else (gpt-5-family, o-series, gemini-2.0) returns
  `cost: 0.0` rather than a fabricated number. server.py's own older
  `_PRICE_PER_1K_TOKENS` dict used to disagree (a hand-entered price for
  `gpt-5-mini`) — reconciled: that entry was removed, both tables now
  return `0.0` for anything unverified rather than one guessing and the
  other declining to (§10 used to track this as open; it's fixed).
- **`seed.py`** — `seed_prompts()`/`seed_pipelines()`/`seed_all()`,
  idempotent, runnable via `python -m backend.ai.seed`. Seeds 7 named
  prompts and 3 named chat-call presets (`gpt-4o-chat` etc., *not* the
  same concept as `pipeline_versions` — see `model_presets` below).
  **Important**: `backfill.py` already seeds `prompt_versions` under
  different names (`extract_metadata`, `paper_analysis`, `compare`,
  `gap_finder`, `chat_system`) — real templates the app's actual
  extraction/analysis code depends on. `seed.py`'s own `paper_analysis`
  entry collides by name; seeding is idempotent-by-name specifically so
  it never overwrites `backfill.py`'s real one if that ran first.

**A fifth table, `model_presets`**, backs `seed_pipelines()` — a named
`{model, temperature, max_tokens}` preset, structurally nothing like
`pipeline_versions` (which requires a real FK to `model_versions`), so
it isn't stored there. No migration existed for it until `migrations/
0012_model_presets.sql`; `seed.py` also creates it ad hoc
(`checkfirst=True`) if the migration hasn't run.

**Anthropic (`anthropic`) and Google (`google-genai`) SDKs are
installed** — but no `ANTHROPIC_API_KEY`/`GOOGLE_API_KEY` is configured
anywhere in this project, so Claude/Gemini have never had a real
*successful* call, only real *auth-failure* calls (used to verify retry
classification). Uses `google-genai`, not the older `google.generativeai`
— that package is fully deprecated by Google ("no longer receiving
updates or bug fixes", confirmed via its own import warning); building
new code against it would have started on a dead end.

**Wired into `server.py`**: `get_prompt_registry(db_session)` /
`get_model_registry(db_session)` are request-scoped factories (each
call opens its own session via the normal `db = SessionLocal(); ...;
db.close()` pattern every other route uses) — **not** singletons built
once at startup, despite that being how an earlier version of this task
was phrased. `PromptRegistry`/`ModelRegistry` each hold one open
`Session` for their lifetime by design; one shared instance across
concurrent requests would mean concurrent requests sharing one session,
a real bug. `get_cost_ledger()` **is** a genuine startup-time singleton
— `CostLedger` holds no session at all. Two new routes: `GET
/api/ai/prompts` (`@login_required`, lists all active prompts) and
`POST /api/ai/test` (`@login_required`, 403 when `IS_PRODUCTION` — a
call-any-model-with-any-prompt endpoint is a real cost/abuse surface,
not something "optional, for dev" should ship unguarded).

**`DEFAULT_MODEL`/`MODELS` no longer default to gpt-5-family.** Changed
to `gpt-4o-mini` / `gpt-4o,gpt-4o-mini,gpt-4-turbo,gpt-3.5-turbo` in
`.env`, `.env.example`, and both Python-level fallback constants
(`server.py`, `model_registry.py`) — specifically so the app's default
usage lines up with `CostLedger`'s confident-pricing set. Doesn't block
manually picking gpt-5 from the live OpenAI-account dropdown; only
changes what's used automatically.

⚠️ **`prompt_versions`/`model_registry_cost_ledger`/`model_presets`
live under `backend/ai`'s own private declarative Bases, never
server.py's own `Base`** — by design (avoids `import server`), but it
means server.py's startup runs *two* separate `create_all(engine,
checkfirst=True)` calls (one per private Base) alongside its own
`Base.metadata.create_all(engine, checkfirst=True)` to make sure these
tables exist.

✅ **`run_migrations.py` now actually completes on a fresh Postgres
database — fixed and verified for real** (was previously 🛑 broken; see
git history / prior task if you want the original diagnosis). Two
distinct problems, both fixed:
1. **Every `CREATE TABLE`/`CREATE INDEX` across all 12 migrations is now
   `IF NOT EXISTS`** (`ALTER TABLE ADD COLUMN` too), since server.py's
   own `create_all()` always creates these same objects first in the
   only order this schema's FK dependencies allow (0001 needs
   `users`/`projects`/`conversations`, which only server.py's bootstrap
   creates). Postgres has no `ADD CONSTRAINT IF NOT EXISTS` (confirmed:
   syntax error) — the one constraint that needs one
   (`fk_upload_jobs_pipeline_version`, 0005) uses a `DO $$ ...
   EXCEPTION WHEN duplicate_object ... END $$` block instead.
   `run_migrations.py`'s statement splitter used to do a naive
   `sql.split(";")`, which would have shredded that block's own internal
   semicolon into broken fragments — it's now dollar-quote-aware
   (`split_sql_statements()`), verified against the real file.
2. **A deeper bug `IF NOT EXISTS` alone can't fix**: `UploadJob` and
   `AIUsageLedger`'s ORM classes were missing columns their own
   migrations defined (`locked_by`/`locked_at`/`pipeline_version_id`;
   `prompt_version_id`) — since server.py's `create_all()` builds the
   table from the ORM class first, `CREATE TABLE IF NOT EXISTS` would
   silently leave those columns missing forever (a no-op statement can't
   backfill a column). Fixed at the root: added the missing columns to
   both ORM classes, added matching `ensure_columns()` entries (SQLite),
   and added `ALTER TABLE ADD COLUMN IF NOT EXISTS` backfills to
   migrations 0002/0006 (Postgres) so either creation path converges to
   the same complete schema.
3. **Bonus find while comparing definitions side by side**:
   `ensure_columns()` was *also* creating `ix_upload_batches_user` and
   `ix_outbox_events_pending` with the same names as migrations
   0001/0007 but *different* definitions (missing the `created_at DESC`
   column and the `WHERE status = 'pending'` partial clause,
   respectively) — `IF NOT EXISTS` checks the name only, so the
   migration's more-complete index would have silently never been
   created, no error, just the wrong index forever. Fixed by making
   `ensure_columns()`'s definitions match the migrations exactly.

Verified end-to-end against a real, throwaway local Postgres database:
full 12-migration chain from a truly fresh DB (server.py bootstrap →
`run_migrations.py`, the only valid order) succeeds completely; a
second run is a clean no-op via `schema_migrations`; a third run with
`schema_migrations` wiped *also* succeeds cleanly (genuine SQL
idempotency, not just the tracking table); and the resulting schema was
inspected directly (`\d upload_jobs`, `\d ai_usage_ledger`, `pg_indexes`)
to confirm every backfilled column, the CHECK constraint, the FK
constraint, and both corrected indexes are exactly right — not just
error-free. The two stale indexes were also fixed directly on this
repo's own local `chat_dev.db`, which had been carrying the old,
incomplete definitions from before this fix.

Two migrations landed after that verification pass, both additive and
unrelated to the above: `0013_worker_heartbeat.sql` (creates
`worker_heartbeats`, the single-row table §5's health check reads) and
`0014_worker_heartbeat_timestamptz.sql` (fixes that table's
`last_seen_at` column to real `timestamptz` on any DB where server.py's
own `create_all()` had already created it as naive `timestamp` first —
same "ORM creates the table before the migration can" ordering problem
as finding #2 above, caught live as a 5-hour clock skew in `GET
/api/worker/health`'s `age_seconds`, UTC vs. the Postgres session's
local timezone).

### 6b. Search & RAG (`backend/search/`)

Two Bearer-JWT routes, same "additional flow, not a replacement" pattern
as `/api/documents/upload` next to `/api/files` (§2): `GET
/api/documents/search` and `POST /api/rag`, sitting alongside server.py's
existing session-based `POST /api/search` rather than replacing it.

- **No second search engine.** Both new routes query the exact same
  `Chunk.embedding` data (JSON-serialized floats, real cosine similarity,
  no pgvector) that `/api/search` already reads for paper results.
  `_search_chunks()` skips any chunk with no stored embedding rather than
  falling back to keyword scoring — unlike `/api/search`, which does have
  a keyword fallback. `SearchIndex` (notes/citations/chat unified index)
  stays untouched — nothing in this codebase has ever written a row to
  it; neither route needed it.
- **`GET /api/documents/search`** — embeds the query (`ModelRegistry.embed`),
  cosine-ranks the caller's own `UserFile(kind="document")` chunks
  (optionally scoped to `file_id`/`project_id`), returns up to `limit`
  (default 20, capped 50) scored snippets.
- **`POST /api/rag`** — same retrieval (`top_k`, default 6, capped 20),
  then feeds the retrieved chunk text into the `semantic_search` prompt
  (`backend/ai/prompts.py`, seeded idempotently via `ensure_default_prompts`
  on every call) and calls `utility_model` for a cited answer. Returns
  `{answer: null, sources: []}` (200, not an error) when nothing scores
  above `min_score` — "no relevant documents" is a normal outcome, not a
  failure.
- Constructor-injected (`SessionLocal`, `UserFile`, `Chunk`,
  `utility_model`), same reason as every other `backend/`/`auth/`/`quotas/`
  module: `server.py` runs as `__main__`, so anything it reaches into that
  imports `server` back gets a second module identity and recurses.

---

## 7. Database

SQLite (`chat_dev.db`, default when `DATABASE_URL` is blank) locally;
Postgres (Neon or CI's `postgres:15` service container) in
production/CI. `worker.py` requires the latter.

22 model classes in `server.py`, plus 3 more under `backend/ai`'s own
private Bases (§6): `PromptVersion` (`prompt_versions`), `CostLedgerEntry`
(`model_registry_cost_ledger`), `ModelPreset` (`model_presets`, only via
`backend/ai/seed.py` — not exported from `backend/ai/models.py`).
`PipelineVersion` (`pipeline_versions`) has a factory in
`backend/ai/models.py` but is never instantiated against any concrete
Base anywhere — no code path actually creates a usable class for it yet.

server.py's 21, grouped by what they're for:

**Core app**: `User`, `Project`, `Conversation`, `Message`, `Memory`
**Files/library**: `UserFile` (table `files` — the file record, despite
the class name; has Knowledge-Library metadata: title/authors/abstract/
tags/reading_status), `Chunk`, `Citation`, `PaperAnalysis`,
`DerivedAnalysis`, `Note`, `SearchIndex`
**Upload pipeline**: `UploadSession` (presigned-upload handshake),
`UploadBatch`, `UploadJob`, `OutboxEvent`, `ImportSession` (schema-only,
nothing writes real checkpoints yet), `StorageUsage` (live per-user
bytes/file-count — the single source of truth both quota paths read)
**Ops/usage**: `ModelVersion`, `AIUsageLedger`, `SupportRequest`,
`WorkerHeartbeat` (single-row heartbeat, id=1 — §5)

`auth.auth_provider`, `storage_limit_bytes`, `monthly_token_used`,
`monthly_token_limit`, `quota_reset_at` were added to `User` mid-session
(migrations `0010`, `0011`); `UsageLog` (quota audit trail) is defined via
`quotas/models.py`'s `create_usage_log_model(Base)`, not a class in
`server.py` itself.

`ensure_columns()` in `server.py` does dev-mode `ALTER TABLE ... ADD
COLUMN` for SQLite; `migrations/*.sql` + `run_migrations.py` are the real
mechanism for Postgres. Both need to stay in sync when a column is added
— easy to forget the SQLite side.

---

## 8. Route inventory (by area)

- **Auth**: `/login`, `/auth/google`, `/auth/callback`, `/logout`,
  `/api/dev-login`, `/api/auth/jwt`, `/api/auth/token`,
  `/auth/magic-link[/verify]`
- **Files/uploads**: `/api/files` (POST/GET/PATCH/DELETE + `/<id>/analysis`,
  `/<id>/analysis/refresh`, `/<id>/raw`), `/api/documents/upload`,
  `/api/documents/<id>/analysis` (POST, synchronous — §2), `/api/uploads/presign`,
  `/api/uploads/multipart/complete`, `/api/uploads/confirm`,
  `/api/uploads/local-put|get`, `/api/jobs/<id>/status`
- **Library**: `/api/library/tags`, `/api/library/stats`, `/api/dashboard`
- **Notes/Citations**: `/api/notes*`, `/api/citations*`
- **Projects/Conversations**: `/api/projects*`, `/api/conversations*`
- **Chat/AI**: `/api/chat`, `/api/search`, `/api/models`,
  `/api/analysis/compare*`, `/api/analysis/gaps*`, `/api/writing`
- **AI layer** (§6, new): `GET /api/ai/prompts`, `POST /api/ai/test` (dev-only)
- **Search/RAG** (§6b, new, Bearer-JWT): `GET /api/documents/search`,
  `POST /api/rag`
- **Account**: `/api/me`, `/api/profile`, `/api/memories*`,
  `/api/account` (delete), `/api/support`, `/api/export*`
- **SPA catch-all**: `/`, `/<path:path>` → serves `frontend/dist`

`backend/upload/routes.py`'s `documents` blueprint owns both
`/api/documents/upload` and `/api/documents/<id>/analysis`;
`backend/search/routes.py`'s `search` blueprint owns
`/api/documents/search` and `/api/rag`. `/api/ai/*` are plain
`@app.route`s in `server.py` itself (no blueprint — the task that added
them was scoped to "integrate into server.py," not "create a blueprint").

---

## 9. Testing & CI

199 tests total (`pytest --collect-only -q`), all passing as of this
writing, spread across: `auth/test_{auth,context,magic_link}.py`,
`storage/test_storage.py`, `imports/test_imports.py`,
`quotas/test_service.py`, `backend/storage/test_backends.py`,
`backend/upload/test_upload.py`, `backend/search/test_search.py`,
`backend/ai/test_{models,prompt_registry,model_registry,seed}.py`,
root-level `test_chat.py`/`test_upload_quota.py`/`test_worker.py`/
`test_worker_health.py`, `observability/test_observability.py`, and
`tests/test_ai.py` (the one file placed at the literal `tests/` path
asked for — see §1, conftest.py doesn't interfere since its fixtures
are only invoked by name).

Frontend has its own, separate Vitest suite (`cd frontend && npm test`,
i.e. `vitest run`) — unit tests for the newer API wrapper modules only
(`features/ai/api.test.ts`, `features/files/api.test.ts`,
`features/search/api.test.ts`), not counted in the 199 above and not
run by the root `pytest`/CI backend job.

Run everything: `pytest` from repo root (picks up `pytest.ini`'s
`test_*.py` pattern). Most suites are pytest-based with isolated
in-memory-SQLite fixtures (no dependency on `server.py` or a real DB);
`auth/test_auth.py`/`test_context.py`/`test_magic_link.py` use a
plain-assert `if __name__ == "__main__"` self-check style instead —
both patterns coexist, neither is wrong, just inconsistent.
`pytest-mock` (the `mocker` fixture) is installed and used in
`tests/test_ai.py`; distinct from `requests-mock`, also installed, used
elsewhere.

**Real, not mocked, integration coverage** (all skip cleanly if the
relevant credential isn't set, so the suite still passes without them):
`backend/storage/test_backends.py`'s R2 round-trip (`R2_BUCKET`);
`backend/ai/test_model_registry.py`'s OpenAI chat + embedding round-trips
(`OPENAI_API_KEY`) and real auth-failure calls against Anthropic/Google
with fake keys (no key needed for *these* — they're supposed to fail).

CI (`.github/workflows/ci.yml`): flake8 lint job, then a test job against
real `postgres:15` + `redis:7` service containers, `STORAGE_BACKEND=local`.
Sets a `SECRET_KEY` env var that **nothing in this codebase reads**
(only `FLASK_SECRET_KEY` is real) — likely copied from a generic
template; harmless (unused vars don't break anything) but worth knowing
if you're debugging a CI-only config issue.

⚠️ **CI sets `OPENAI_API_KEY: sk-fake-key-for-ci`** — non-empty, so the
`skipif(not os.environ.get("OPENAI_API_KEY"))` guards on the real-round-trip
tests in `backend/ai/test_model_registry.py`/`tests/test_ai.py` won't
skip in CI; they'll actually run against the real OpenAI API with an
invalid key and get a real 401, which the retry logic now fails fast on
(§6) rather than retrying — so they'll fail, not hang, but they will
fail. Not verified against a live CI run (no `gh` access from this
environment) — flagged as a real risk, not confirmed broken.

---

## 10. Known rough edges (honest, not exhaustive)

- **`tests/conftest.py` is dead scaffolding.** It scans for
  `app.py`/`run.py`/`main.py`/`wsgi.py`/`backend/app.py` and Flask-SQLAlchemy
  extensions — none of which exist here (entry point is `server.py`, DB
  access is raw SQLAlchemy `sessionmaker`, not `flask_sqlalchemy`). No
  test file actually uses these fixtures. Safe to ignore or delete.
- ~~`.epub` has no real importer~~ **Fixed.** `imports/importers/epub.py`
  parses the real OCF/OPF structure (`META-INF/container.xml` -> package
  document -> spine), extracting each content document's text via
  stdlib `xml.etree.ElementTree` in actual reading order, `<script>`/
  `<style>` excluded. Registered ahead of `ZipImporter` in
  `imports/registry.py` — epub's `application/epub+zip` mimetype
  contains "zip", which `ZipImporter.matches()` also accepts, so
  ordering is what keeps `.epub` from still falling through by
  accident.
- **`worker.py` still isn't started automatically in local dev — by
  design, not a gap.** `python server.py` and `python worker.py` staying
  two separate commands is deliberate (§5): most dev work doesn't touch
  background processing, and it needs real Postgres anyway (SQLite dev
  can't run it). If you want both up together locally, `pip install
  honcho && honcho start` runs the repo's own `Procfile` — that's the
  opt-in path, not automatic startup baked into `python server.py`
  itself (which would be a surprising side effect for the common case
  that doesn't need the worker at all).
- ~~`/api/documents/upload` has no frontend caller~~ **Fixed.**
  `features/files/api.ts`'s `upload()` now routes document uploads
  (`.pdf`/`.epub`/`.docx`/`.txt`) through it via a session-to-JWT bridge
  (`getBearerToken()`, `GET /api/auth/jwt`); images still go through the
  original `/api/files` (the JWT route doesn't accept images at all).
- ~~ADR-0001 (Postgres worker vs. Celery) is unresolved~~ **Resolved.**
  `docs/adr/0001-queue-backend.md` now says: keep the Postgres worker,
  don't migrate to Celery. Every concern the ADR raised against it —
  retry/backoff/dead-letter, observability, process supervision — is
  now addressed directly on top of it (§5, §12). Priority queues and
  cancellation stay explicitly out of scope until a real caller needs
  them.
- ~~Quota enforcement is split~~ **Partly fixed.** The *limits* now
  agree — both `/api/files` and `/api/documents/upload` check
  `User.storage_limit_bytes` (falling back to
  `QuotaService.DEFAULT_STORAGE_LIMIT_BYTES`). They used to actually
  disagree, not just duplicate: `/api/files` compared against the
  standalone `MAX_STORAGE_MB` env var (5000 MB default) while
  `/api/documents/upload` went through `QuotaService`
  (`storage_limit_bytes`, ~1000 MB default) — a user could hit 5GB
  through one route and get blocked at 1GB through the other.
  `MAX_STORAGE_MB` has been removed (it no longer did anything real).
  The *increment* side still doesn't share code — `/api/files` folds it
  into `_adjust_storage_usage()`, atomic with the same transaction that
  writes the file/job rows; `QuotaService.increment_storage()` opens its
  own session and also writes a `UsageLog` row. Left separate on
  purpose: routing `/api/files` through `QuotaService.increment_storage()`
  would break that atomicity guarantee and start writing `UsageLog` rows
  a working code path never wrote before, for a "two functions instead
  of one" win that isn't worth either risk.
- ~~No frontend caller for anything in `backend/ai`~~ **Fixed.** Settings
  now has an "AI Prompts" tab (`GET /api/ai/prompts`, read-only) and, in
  dev builds only, a "Test AI" tab (`POST /api/ai/test`) — both session-
  authed, no JWT bridge needed since these are `server.py`'s own routes.
- ~~Two pricing tables, not reconciled~~ **Fixed.** `server.py`'s
  `_PRICE_PER_1K_TOKENS` had a hand-entered `gpt-5-mini` rate that
  `backend/ai/cost_ledger.py`'s `CostLedger.PRICING` deliberately
  excluded as unverified. Reconciled toward the conservative side: the
  entry was removed, so an unpriced model returns `cost: 0.0` in both
  places rather than a real number in one and a declined guess in the
  other. Net effect: `gpt-5-mini` — this app's actual `DEFAULT_MODEL` —
  now reports `$0.00` everywhere pricing isn't confirmed, instead of a
  specific-looking number nobody had verified against OpenAI's real
  pricing page. Re-add with a real rate once someone actually checks.

---

## 11. Running it

```bash
# one-time setup
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
# fill in .env — see .env.example for every var this app reads

# dev
python server.py                 # http://localhost:5000
cd frontend && npm run dev        # optional: hot-reload UI on :5173, proxies to :5000

# seed default AI prompts/presets (optional — idempotent, safe to re-run)
python -m backend.ai.seed

# background processing (optional — only matters if you want uploaded
# files to actually get extracted/analyzed; requires DATABASE_URL to
# point at real Postgres, not SQLite)
python worker.py

# verify the worker is actually running:
curl http://localhost:5000/api/worker/health

# tests
pytest -v                         # everything, 199 tests, ~35 seconds
```

No Docker, no local Redis server, no local Postgres required for basic
dev (SQLite fallback + Redis-optional caching that no-ops when unset).
See `.env.example` for the full, current list of every environment
variable this app actually reads.

**Deploying to real Postgres**: `python server.py` once (creates the
core schema), then `python run_migrations.py` — that order, every
`CREATE TABLE`/`CREATE INDEX`/`ADD COLUMN` in `migrations/*.sql` is now
idempotent, verified end-to-end against a real throwaway Postgres
database (§6). The reverse order (migrations against a truly empty DB,
before server.py ever ran) still doesn't work — `0001` needs
`users`/`projects`/`conversations`, which only server.py's own bootstrap
creates; nothing else in this repo creates them.

---

## 12. Observability (`observability/`)

JSON logs, Prometheus metrics, correlation ids — no tracing (the task
that added this marked OpenTelemetry optional; skipped, nothing here
makes enough cross-service hops yet to need distributed traces over
correlation-id'd logs).

- **Logging**: `observability.configure_logging()` replaces
  `logging.basicConfig` in both server.py and worker.py — every log line
  becomes one JSON object (`observability/logging_config.py`'s
  `JSONFormatter`), not structlog (a formatter is a few lines; this app
  already uses stdlib `logging` everywhere, so this is a smaller change
  than swapping the logging backend for what the task's own brief calls
  an equally acceptable alternative).
- **Correlation ids**: `correlation_id_var` (a `contextvars.ContextVar`,
  correct under Flask's threaded dev server without extra plumbing).
  server.py sets one per HTTP request (`X-Request-ID` in if the caller
  sent one, minted otherwise; always echoed back in the response
  header); worker.py sets one per job (`job-<id>`). Every log line
  emitted during that request/job carries it automatically — including
  werkzeug's own access-log lines, verified live.
- **Metrics** (`observability/metrics.py`, prometheus_client):
  `http_requests_total`/`http_request_duration_seconds` (labeled by
  method + **route rule**, e.g. `/api/files/<int:fid>` — never the
  resolved path, that would put every distinct file id in its own label
  and never stop growing), `ai_calls_total`/`ai_tokens_total` (labeled
  by model only, not user_id — per-user token accounting already exists
  in `AIUsageLedger`/`CostLedger`, SQL with no cardinality limit;
  Prometheus is for operational aggregates, not a second billing
  ledger), `upload_queue_length` (a Gauge, recomputed live from
  `upload_jobs` on every `/metrics` scrape, not pushed periodically —
  avoids staleness between scrapes).
- **Two processes, two scrape targets**: prometheus_client's registry is
  per-process — it can't merge state across server.py and worker.py.
  server.py exposes `GET /metrics` (unauthenticated, same reasoning as
  `/api/worker/health`); worker.py runs its own tiny metrics HTTP server
  on `WORKER_METRICS_PORT` (default 9101, via
  `start_worker_metrics_server()`). Point Prometheus at both; aggregate
  with `sum by (model) (ai_calls_total)` etc. at query time.
- **AI-call instrumentation is at the choke points, not every call
  site**: `responses_text()`/`embed_texts()`/`_log_chat_cost()` in
  server.py (the legacy path) and `ModelRegistry.call()`/`.embed()` in
  `backend/ai/model_registry.py` (the new path, used by both processes)
  — four places cover every AI call in the app. Success-path only; no
  error/status label — a real scope cut, not an oversight (would mean
  wrapping call sites that don't currently have their own try/except,
  like `responses_text()`, purely for metrics).
