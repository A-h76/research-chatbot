# Dhund — Backend

> Architecture + **full database audit** for slides / notes. Audited from code 2026-08.

---

## Stack

| Layer | Choice |
|-------|--------|
| API | Flask monolith — `server.py` (~5k+ lines) + factory blueprints in `backend/` |
| Worker | `worker.py` — Postgres queue (`FOR UPDATE SKIP LOCKED`), no Celery |
| DB | **Postgres** production · SQLite local/dev only |
| Cache | Redis optional (`job:{id}:status`, rate limits) |
| Objects | `storage/` + `backend/storage/` (local / R2 / S3) |
| Extract | `imports/` Importer registry (PDF, EPUB, …) |
| LLM | OpenAI Responses API (streaming); Prompt Engine + Capability Router |

**Hard rule:** never `import server` from modules server imports — use factory/DI wiring.

---

## Package map (`backend/`)

| Package | Role |
|---------|------|
| `ai/` | Prompt Engine, capability router, personas, model router, cost ledger |
| `ai_core/` | Chat orchestration / executors |
| `evidence/` | EvidenceObjects, RI stages, writing intelligence, reviewer |
| `evidence_grading/` | GRADE / SIGN-style frameworks |
| `upload/` | Bearer-JWT upload + bulk |
| `library/` · `ecosystem/` · `scholarly/` | Connect, catalog, PubMed/arXiv/UFTR |
| `writing/` · `projects/` · `search/` | Writing shell, hubs, RAG search |
| `analysis_pipeline/` · `document_understanding/` · `classification/` | Paper analysis / SUE |
| `workflow/` · `knowledge_graph/` · `research/` | Events, KG, research helpers |
| `processing/` · `storage/` | Parse jobs, storage backends |
| `prompts/` | Prompt blueprints |

Root also: `auth/`, `quotas/`, `feature_flags/`, `security/`.

---

## Worker job types (HANDLERS)

Typical chain:

| Job | Produces |
|-----|----------|
| `import` | Text extract → `chunks` (+ embeddings) |
| `extract_metadata` | Scholarly metadata on `files` |
| `phase1_analysis` / `paper_analysis` | `analysis_pipeline_results` / `paper_analyses` |
| `evidence_extract` | `evidence_objects` + extraction runs |
| `theme_map` / `literature_review` | `derived_analyses` |
| `library_sync` | External library sync |

Outbox (`outbox_events`) decouples “job created” from “dispatched.”  
Redis mirrors status only — **Postgres `upload_jobs` is source of truth.**

---

## API surfaces (frozen contracts)

Living freeze: `docs/contracts/` (Evidence / RI / jobs / errors / versioning / Capability Router / Research Scope).

Examples:

- Evidence CRUD / extract / explain  
- RI: search, rank, consensus, conflict, reason, writing  
- Writing bindings · reviewer-runs  
- Job observability  
- UFTR (full-text resolution)  
- Auth: Google OAuth, magic link, password, invite beta  

---

# Database audit

## Boot model

1. `Base.metadata.create_all()` — core tables owned by `server.py`  
2. `run_migrations.py` — `migrations/0001` … `0040` tracked in `schema_migrations`  
3. `backfill.py` — seed data  

SQLite: `create_all` + column ensure; **worker refuses SQLite** (needs SKIP LOCKED).

Design constraints:

- Structured data often in **Text + app JSON**, not ORM JSONB  
- Soft Integer FKs across private Bases; real FKs at SQL migration level  
- `create_all` creates tables, **not** new columns on existing tables  

---

## Core tables (ORM / create_all)

### Users & auth

| Table | Purpose |
|-------|---------|
| `users` | Email, auth_provider, quotas, admin, beta status, onboarding fields, session_version |
| `invite_tokens` | Closed beta invites |
| `magic_link_tokens` | Magic-link jti store |
| `email_verification_tokens` / `password_reset_tokens` / `email_change_tokens` | Auth flows |
| `security_events` | Security audit trail |
| `system_settings` | Ops kill switches / budgets |

### Projects & chat

| Table | Purpose |
|-------|---------|
| `projects` | Research hub (`user_id`, name, instructions) |
| `conversations` | Chat threads (optional `project_id`, `file_id` for paper chat) |
| `messages` | Roles, content, sources/attachments JSON text |

### Library & uploads

| Table | Purpose |
|-------|---------|
| `files` (`UserFile`) | Papers: path, checksum, title/authors/DOI, tags, fulltext_json, external_* |
| `chunks` | Passage text + embedding JSON, page/section |
| `upload_sessions` | Presign lifecycle before file row |
| `upload_batches` | Multi-file grouping |
| `upload_jobs` | Queue row: type, status, lock, backoff, pipeline_version_id |
| `import_sessions` | Resumable checkpoints (mostly legacy) |
| `storage_usage` | Per-user bytes / file_count |

### Evidence & research judgment

| Table | Purpose |
|-------|---------|
| `evidence_objects` | Claims, quotes, locators; soft user/project/file ids |
| `claim_reviews` | Human review of claims |
| `evidence_extraction_runs` | Extract job runs |
| `writing_sentence_bindings` | Draft sentence ↔ evidence |
| `research_decisions` | Append-only judgments |
| `workflow_events` | Instrumentation breadcrumbs |

### Writing & reviewer

| Table | Purpose |
|-------|---------|
| `documents` | Writing Studio docs (project-scoped) |
| `document_versions` | Snapshots |
| `document_activity` | Activity log |
| `reviewer_runs` / `reviewer_findings` | Automated review persistence |

### Analysis & RI side products

| Table | Purpose |
|-------|---------|
| `paper_analyses` | Per-file structured analysis |
| `analysis_pipeline_results` | Phase pipeline JSON |
| `derived_analyses` | Multi-paper compare / gaps / research |
| `project_questions` | Research questions |
| `memories` | User/project memory (research kinds) |
| `notes` | Freeform notes |
| `citations` | Bibliography entries |
| `search_index` | Semantic index for note/citation/chat (papers via `chunks`) |

### Library Connect

| Table | Purpose |
|-------|---------|
| `library_connections` | Zotero / Drive / … connections |
| `library_collections` / `library_collection_papers` | Collections |
| `library_sync_runs` | Sync runs |

### Queue, quotas, AI ledger, flags

| Table | Purpose |
|-------|---------|
| `outbox_events` | Transactional outbox |
| `worker_heartbeats` | Worker liveness |
| `usage_logs` | Quota / entitlement audit |
| `ai_usage_ledger` | Per-call AI cost |
| `feature_flags` | Global / per-user flags |
| `model_versions` / `model_presets` | Model versioning / chat presets |
| `support_requests` | Support inbox |

### Prompt Engine (separate Base, wired in server)

| Table | Purpose |
|-------|---------|
| `prompt_versions` | Versioned prompts |
| `pipeline_versions` | Pipeline versioning |
| `personas` | Persona definitions |
| `prompt_executions` | Execution records |
| `model_registry_cost_ledger` | Registry cost ledger |

### Scholarly / ops (migration SQL)

| Table / view | Purpose |
|--------------|---------|
| `provider_cache` / `provider_metrics` / `provider_circuit` | External provider ops |
| `processing_metrics_daily` | Matview over jobs |

---

## Migrations timeline (0001–0040)

| Range | Theme |
|-------|--------|
| 0001–0009 | Upload batches/jobs, storage, outbox, flags, metrics |
| 0010–0016 | Auth provider, quotas, presets, heartbeat, prompt engine, admin |
| 0017–0022 | Analysis results, scholarly providers, discover, hotpath indexes |
| 0023–0030 | Project questions, research memory, beta ops, library bridge/collections/sync |
| 0031–0037 | Writing studio, evidence layer, magic link, reviewer, decisions, workflow |
| 0038–0040 | Auth production / onboarding, entitlement ledger, fulltext_json (UFTR) |

---

## Entity relationships (logical)

```text
users
 ├── projects
 │    ├── files → chunks
 │    ├── evidence_objects → claim_reviews
 │    ├── documents → versions / bindings → evidence_objects
 │    ├── conversations → messages
 │    ├── memories, notes, citations, project_questions
 │    └── library_collections
 ├── upload_jobs → outbox_events
 ├── usage_logs / ai_usage_ledger / storage_usage
 └── library_connections → library_sync_runs
```

---

## Dual-storage note (accepted V1 debt)

| Path | Used by |
|------|---------|
| Root `storage/` | Primary upload pipeline in `server.py` |
| `backend/storage/` | Newer JWT upload blueprint |

Same jobs table; don’t assume APIs are interchangeable.

---

## Slide prompts

1. Stack diagram (SPA ↔ Flask ↔ Postgres ↔ Worker)  
2. Worker HANDLERS list  
3. Domain ERD (users → projects → files → evidence → documents)  
4. Migration eras (upload → evidence → writing)  
5. Contracts freeze box  
6. Postgres vs SQLite vs Redis  

---

## Source paths

- `server.py` · `worker.py` · `run_migrations.py`  
- `migrations/*.sql`  
- `backend/**`  
- `docs/database-design.md` · `docs/contracts/` · `docs/adr/`  
- `docs/00-constitution.md` · `docs/audit/03-TECHNICAL-DEBT-REPORT.md`  
