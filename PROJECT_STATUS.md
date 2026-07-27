# PROJECT_STATUS.md

**Document type:** Engineering architecture audit (source of truth for development)  
**Audience:** Staff / senior engineers taking ownership of this codebase  
**Audit date:** 2026-07-26  
**Last updated:** 2026-07-27 (Scholarly providers Steps 1–2 + AI Core Stage 1 Paper Chat + Docker/Railway deploy; migrations through **0021**)  
**Method:** Codebase inspection — features described as Implemented must exist in code; planned-only design docs are called out explicitly  

**Branding note (inconsistency):** The product is referred to as **Personal AI** (README, login copy, many UI strings), **Soro** (`frontend/index.html`, sidebar, Design System v2), **Research Workspace** (`templates/login.html`), and **ResearchOS** (CI workflow name, `brain.md`, systemd units). These are the same application, not forks. SPA chrome now brands primarily as **Soro**; login/legal templates may still say Personal AI.

---

# 1. Executive Summary

## Current maturity

**Early beta (research pipeline live on upload; Paper Workspace + Design System v2 chrome; scholarly Discover + Crossref enrichment).**

The core product loop works: authenticated users can chat (streaming), upload documents, run async import → **Crossref metadata enrich (when DOI found)** → embed → **Phase 1 structured analysis** → LLM paper overview, inspect Phase 1 outputs in the Paper Workspace (Structure / Classification / Entities / Evidence / Graph / Related), manage projects/notes/citations/memory, search locally **or Discover papers via OpenAlex** (Add to Library as metadata stubs), and use multi-paper compare/gaps tooling. Observability (Prometheus + JSON logs), quotas, dual auth (session + JWT), and a Prompt Engine exist for parts of the AI surface.

**Phase 1 (1.1–1.7)** research engines are implemented, tested, and integrated via `AnalysisPipelineService` (Phase 2). Uploads enqueue `phase1_analysis`; results persist in `analysis_pipeline_results`; PromptBuilder/worker paper analysis consume Phase 1 JSON when present. The SPA consumes `/pipeline` + `/phases/*` via `features/pipeline` + paper tab mappers.

**Scholarly providers (Steps 1–2):** `backend/scholarly/` — Crossref (upload enrichment + citation format), OpenAlex (Discover search + library import), Semantic Scholar (Related Papers tab). Shared `provider_cache` / metrics / DB circuit breaker / bulkheads. Migrations **0018–0021**.

**AI Core Stage 1 Paper Chat** is implemented behind `PAPER_CHAT_PIPELINE_ENABLED` (default OFF; soak via `shadow` → `true`). Spec: `docs/ai-core-stage1-paper-chat.md`.

**Design System v2 (D0 → D9)** is implemented in the live React app: tokens, slim sidebar (Home · Library · Projects · Writing; Ask Soro under More), Home launchpad, `PipelineStatus`, densified Library + CollectionToolbar, demoted global Chat, T4 Writing/Compare/Citations, ⌘K command palette v1, ErrorBoundary + session-expired modal + a11y skip link. Specs: `docs/DESIGN-SYSTEM-v2.md`, `docs/Interaction-Guidelines.md`.

It is **not** production-hardened for a public multi-tenant SaaS launch: incomplete chat quota coverage in places, dual parallel stacks (chat vs Prompt Engine; two storage facades; two upload APIs), branding split on login templates. Chat still uses mixed prompt paths (normal chat PromptBuilder; paper chat Stage 1 flagged). Docker multi-stage + Gunicorn entrypoint support Railway-style deploys; systemd units remain for self-host. Several production-hardening PRs (headers, MIME, metrics auth, chat rate limit) are marked done in §17 — verify deploy config before treating as live.

## Current version

| Signal | Value |
|--------|--------|
| App semver | **Not defined** — no `__version__`, no package version for the product |
| Frontend `package.json` | `0.0.0` |
| Backend docstring | `server.py` header: “Personal AI — … (Phase 1)” |
| Phase-1 pipeline packages | Each declares `PIPELINE_VERSION = "1.0.0"` / `SCHEMA_VERSION = "1.0.0"` internally |
| Integration layer | `backend/analysis_pipeline` → `PIPELINE_VERSION = "2.0.0"` |
| AI Core | `backend/ai_core` → package `__version__` Stage 1 Paper Chat |
| Schema migrations | `migrations/0001` … **`0021`** (`files.source_url` for Discover stubs) |

Treat this as an **unversioned product** with additive Postgres migrations through **0021**, Phase 1 libraries at **1.0.0**, and Phase 2 integration at **2.0.0**.

## Overall architecture

Monolithic Flask app (`server.py`, ~6.8k+ lines) serving API + built SPA static assets, plus a separate Postgres-polled worker (`worker.py`). React SPA in `frontend/`. Object storage via Cloudflare R2 (or local/S3). Optional Redis for job-status cache only. OpenAI (primary) with optional Anthropic/Gemini via `ModelRegistry`.

```
Browser (React SPA)
    ↓ session cookie  /  Bearer JWT (selected routes)
Flask (server.py + blueprints)
    ↓
Services (quotas, storage, AI registries, search, AnalysisPipelineService,
          scholarly providers: Crossref / OpenAlex / Semantic Scholar)
    ↓
Postgres (or SQLite for local/dev) + Object storage (R2/local/S3)
    + provider_cache / provider_metrics / provider_circuit
    ↓
worker.py (UploadJob queue via SKIP LOCKED)
    ↓  import → Crossref enrich (DOI) → phase1_analysis (1.1–1.7) → paper_analysis
OpenAI / optional LLM providers + OpenAlex / Crossref / Semantic Scholar
```

## Technology stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, Flask 3, SQLAlchemy 2, Authlib, Flask-JWT-Extended, Flask-Limiter, Prometheus client |
| Frontend | React 19, TypeScript, Vite 8, TanStack Query 5, Tailwind 4, shadcn/Base UI, Framer Motion, react-router 7 |
| DB | PostgreSQL (prod/worker required); SQLite allowed for local API-only dev |
| Queue | Postgres `upload_jobs` (`FOR UPDATE SKIP LOCKED`) — **not** Celery (ADR-0001) |
| Cache | Optional Redis (job status mirror only) |
| Storage | Cloudflare R2 / local filesystem / AWS S3 |
| AI | OpenAI Responses API (chat), Chat Completions / multi-provider (`ModelRegistry`), `text-embedding-3-small` |
| Research pipeline | Phase 1.1–1.7 deterministic engines + Phase 2 `AnalysisPipelineService` orchestration |
| Scholarly data | Crossref, OpenAlex, Semantic Scholar via `backend/scholarly/` (cache + circuit + bulkheads) |
| Email | Resend (optional; console log fallback) |
| Auth | Google OAuth, magic link, `DEV_AUTO_LOGIN` |
| Deploy | Docker multi-stage (`Dockerfile` + `entrypoint.sh`), Procfile/Gunicorn, systemd units |
| CI | GitHub Actions: flake8 + pytest (Postgres + Redis services) |

## Current product positioning

Private / personal **research & thesis writing assistant**: ChatGPT-style chat grounded in user uploads (RAG), projects with instructions, selective long-term memory, citation manager, structured document analysis (Phase 1) plus LLM paper overview, multi-paper compare/gap tools, and writing helpers. Positioned as a personal or small-team research workspace — not a billed multi-tenant SaaS (no payments integration).

## What the application currently does

1. Authenticate via Google OAuth, magic link, or local DEV auto-login; SPA shows **Session expired** modal on 401 (no silent dump)  
2. Stream chat replies (OpenAI Responses API) with optional web search + save_citation tools; global Ask Soro demoted under sidebar More / ⌘K  
3. Upload documents/images from **Library** (toolbar + zone) or chat; queue **import → Crossref DOI enrich → chunk/embed → Phase 1.1–1.7 → LLM paper analysis**  
4. Persist Phase 1 outputs (`analysis_pipeline_results`); expose `/api/documents/<id>/analyze|pipeline|phases/*`  
5. **Paper Workspace** tabs: Overview · Structure · Classification · Entities · Evidence · Graph · Narrative · **Related** · Chat — pipeline AI-state chrome  
6. **Discover** (Search page): OpenAlex keyword search; **Add to Library** as metadata-only stubs (no PDF fetch until user uploads)  
7. RAG over user chunks (in-Python cosine similarity) in chat and via JWT `/api/rag`  
8. Manage projects, files/library, notes, citations (table + BibTeX export; Crossref-verified format API), memories  
9. Dashboard (research launchpad), corpus search, writing transforms, compare/gaps, settings, support tickets, legal pages  
10. ⌘K command palette (find papers/projects/chats + core commands)  
11. Admin-gated prompt authoring + usage analytics APIs (session `is_admin`)  
12. Ops: `GET /api/worker/health`, `GET /api/health/providers`  

---

# 2. Current Feature Inventory

Legend: **Implemented** | **Partial** | **Planned** (design docs / libraries not wired) | **Not Implemented**

---

### Authentication & accounts

**Status:** Implemented (with production caveats)

| Area | Detail |
|------|--------|
| Backend | `server.py` (OAuth, session, `/api/me`, account delete); `auth/jwt_utils.py`, `auth/decorators.py`, `auth/magic_link.py`, `auth/context.py` |
| Frontend | No React login page — `/login` is Flask `templates/login.html`; `useMe`, logout redirect, JWT bridge in `frontend/src/lib/apiClient.ts`; **D9** `SessionExpiredModal` on `soro:session-expired` (401) |
| Endpoints | `GET /login`, `GET /auth/google`, `GET /auth/callback`, `GET /logout`, `POST /api/dev-login`, `POST /auth/magic-link`, `POST /auth/magic-link/verify`, `GET /api/auth/jwt`, `POST /api/auth/token`, `GET /api/me`, `PATCH /api/profile`, `DELETE /api/account` |
| Database | `users` (`auth_provider`, quotas, `is_admin`) |
| Dependencies | Authlib, Flask-JWT-Extended, itsdangerous (magic link), Resend (email) |
| Known issues | `DEV_AUTO_LOGIN` in `.env.example`; no password auth; no session TTL; allowlist optional (`ALLOWED_EMAILS` blank = open); `get_current_user` unified helper unused by routes |

---

### Chat (streaming)

**Status:** Implemented

| Area | Detail |
|------|--------|
| Backend | `server.py` `POST /api/chat` — Responses API streaming, tools, RAG inject, memory |
| Frontend | `features/chat/` — `useChatStream`, Composer, MessageList, model/temp/reasoning controls, voice input, memory toggle; global entry demoted to **Ask Soro** (sidebar More + ⌘K); Paper/Project inquiry chrome (D6) |
| Endpoints | `POST /api/chat`; conversation CRUD under `/api/conversations` |
| Database | `conversations`, `messages` |
| Dependencies | OpenAI; ddgs (web search tool) |
| Known issues | PromptBuilder for normal chat; Paper Chat Stage 1 pipeline behind `PAPER_CHAT_PIPELINE_ENABLED` (default OFF); share button copies URL only; confirm chat rate/token limits enabled on deploy (§17) |

---

### Knowledge Library / Files

**Status:** Implemented

| Area | Detail |
|------|--------|
| Backend | `POST/GET/PATCH/DELETE /api/files*`, library tags/stats; JWT `POST /api/documents/upload`; bulk `POST /api/uploads/bulk` |
| Frontend | `features/files/` — dense Library (D5), `CollectionToolbar`, `LibraryUploadZone` / queue, dual upload paths in `api.ts` |
| Endpoints | See §6 |
| Database | `files`, `chunks`, `upload_jobs`, `upload_batches`, `storage_usage`, `upload_sessions` |
| Dependencies | `storage/` + `backend/storage/`, `imports/`, worker, `backend/scholarly/` (Crossref enrich) |
| Discover stubs | Metadata-only library rows (`source_url`, empty path); **Metadata only** badge in UI; Phase 1/RAG after user uploads PDF |
| Known issues | Two upload APIs with different allowlists/size limits historically; `FilePreviewDialog.tsx` still dead |

---

### Paper Analysis / Research Pipeline

**Status:** Implemented (Phase 1 structured + LLM overview; **SPA Paper Workspace surfaces Phase 1**)

| Area | Detail |
|------|--------|
| Backend live — Phase 2 | `backend/analysis_pipeline/` — `AnalysisPipelineService` runs 1.1→1.7; persists JSON; worker job `phase1_analysis` |
| Backend live — LLM | Worker `paper_analysis` (consumes Phase 1 via `phase1_context`); sync `POST /api/documents/<id>/analysis` (PromptBuilder + Phase 1 when cached); `GET/POST /api/files/<id>/analysis*` |
| Phase 1 packages (black boxes) | `document_understanding` (1.1), `classification/pass2` (1.2), `analysis_context` (1.3), `medical_understanding` (1.4), `evidence_grading` (1.5), `prompt_assembly` (1.6), `knowledge_graph` (1.7) |
| APIs | `POST /api/documents/<id>/analyze`, `GET …/pipeline`, `GET …/phases/<phase>`; plus existing analysis/compare/gaps |
| Frontend | `features/pipeline/` (hooks, AI-state, `PipelineStatusPanel`); Paper Workspace tabs + mappers for DU / classification / entities / evidence / graph; Narrative = LLM overview; **Related** = Semantic Scholar; Chat = paper-scoped |
| Database | `paper_analyses`, `derived_analyses`, **`analysis_pipeline_results`** (migration 0017) |
| Known issues | Confirm-upload / thread legacy paths still exist (deprecated warnings); chat does not consume Phase 1 structured JSON; lazy migration for old files; Related needs API key for live results |

---

### Phase 1 Research Engines (detail)

**Status:** Implemented + integrated (Phase 2)

| Phase | Package | Public API | Wired? |
|-------|---------|------------|--------|
| 1.1 Document Understanding | `backend/document_understanding/` | `DocumentUnderstandingPipeline.process(path)` | Yes — via AnalysisPipelineService |
| 1.2 Classification | `backend/classification/pass2/` | `DocumentClassificationPipeline.process(doc)` | Yes |
| 1.3 Analysis Context | `backend/analysis_context/` | `AnalysisContextPipeline.process(doc, classification)` | Yes |
| 1.4 Medical Understanding | `backend/medical_understanding/` | `MedicalUnderstandingPipeline.process(...)` | Yes (routing-gated skip) |
| 1.5 Evidence Grading | `backend/evidence_grading/` | `EvidenceGradingPipeline.process(...)` | Yes (routing-gated skip) |
| 1.6 Prompt Assembly | `backend/prompt_assembly/` | `PromptAssemblyPipeline.process(...)` | Yes (research AssembledPrompt; distinct from `backend.ai.PromptBuilder`) |
| 1.7 Knowledge Graph | `backend/knowledge_graph/` | `KnowledgeGraphPipeline.process(...)` | Yes (in-memory + JSON/GraphML serialize; no graph DB) |
| 2.0 Integration | `backend/analysis_pipeline/` | `AnalysisPipelineService.analyze_file_path(...)` | Yes — worker + HTTP |

**Non-goals still deferred:** Neo4j/query engine, Phase 1 LLM inside engines, Celery, chat→PromptBuilder migration.

---

### Projects

**Status:** Implemented

| Area | Detail |
|------|--------|
| Backend | `/api/projects` CRUD; instructions injected into chat / PromptBuilder |
| Frontend | Projects list + detail pages |
| Database | `projects` |
| Known issues | `PromptBuilder` loads project by id **without** `user_id` ownership check (`backend/ai/prompt_builder.py`) — cross-user instruction leak if id guessed; `ProjectList.tsx` dead (Sidebar uses inline nav) |

---

### Memory & personalization

**Status:** Implemented (create via chat only)

| Area | Detail |
|------|--------|
| Backend | Memories CRUD; chat extraction; `MemoryEngine` for Prompt Engine path |
| Frontend | Memory page (view/edit/delete); Settings personalization; Composer memory toggle |
| Database | `memories`; `users.custom_instructions` |
| Known issues | No manual “create memory” UI; MemoryEngine ranking is naive token-overlap (TODO embeddings) |

---

### RAG / Document search

**Status:** Implemented (simple) + Discover (OpenAlex)

| Area | Detail |
|------|--------|
| Backend | `rag_retrieve` in `server.py`; JWT `GET /api/documents/search`, `POST /api/rag` (`backend/search/routes.py`); `GET /api/discover`, `POST /api/discover/import` |
| Frontend | Search page: **My Library** + **Discover** tabs; Ask AI; chat auto-retrieval; Discover **Add to Library** |
| Database | `chunks.embedding` (JSON float arrays as text); Discover stubs on `files` (`source_url`, provenance cols) |
| Known issues | No pgvector/ANN; O(n) cosine in Python; `search_index` table never written; dual retrieval semantics (chat has keyword fallback; JWT path does not) |

---

### Prompt Engine

**Status:** Partial (wired for RAG + sync/worker paper analysis + normal chat + admin; **paper chat** still legacy)

| Area | Detail |
|------|--------|
| Backend | `backend/ai/*` (PromptRegistry, PromptBuilder, DomainRegistry, ModelRegistry), `backend/prompts/` admin |
| Frontend | Settings AI sections (`/api/ai/prompts`, `/api/ai/test` DEV) |
| Database | `prompt_versions`, `personas`, `prompt_executions`, `model_registry_cost_ledger`, `model_presets` |
| Phase 2 | `PromptBuilder.build(..., phase1_context=)` injects Phase 1 summary; worker + sync analysis use it when cached |
| Distinct from | `backend/prompt_assembly` (Phase 1.6 research AssembledPrompt) — different type/purpose |
| Known issues | Chat normal path uses PromptBuilder; Paper Chat Stage 1 flagged (`PAPER_CHAT_PIPELINE_ENABLED`); DomainRegistry parallel to Phase 1.2; dual cost ledgers; domain modules mostly stubs (medical + ai_ml real) |

---

### Citation Manager

**Status:** Implemented

| Area | Detail |
|------|--------|
| Backend | CRUD, from-paper, BibTeX export; chat tool `save_citation` |
| Frontend | CitationsPage + dense `CitationTable` (D7 T4); CitationFormDialog; Library/Writing toolbar entry |
| Database | `citations` |
| Known issues | Seeded `citation_generation` prompt **not** called from any live path; Crossref APA via `/api/files/<id>/citation` is separate from this manager |

---

### Scholarly providers (Crossref / OpenAlex / Semantic Scholar)

**Status:** Implemented (core) / Partial (UI polish)

| Area | Detail |
|------|--------|
| Package | `backend/scholarly/` — shared `provider_get`, Crossref, OpenAlex, Semantic Scholar |
| Upload enrichment | After text extract: DOI → Crossref merge (provenance) → then Phase 1 AI (`worker.py`) |
| Discover | `GET /api/discover` (OpenAlex); `POST /api/discover/import` metadata stub + optional Crossref |
| Related | `GET /api/files/<id>/related` (Semantic Scholar; needs `SEMANTIC_SCHOLAR_API_KEY`) |
| Citation format | `GET /api/files/<id>/citation?style=` (Crossref CSL → APA/MLA/Chicago) |
| Ops | `GET /api/health/providers`; metrics; DB circuit breaker; bulkheads; SWR cache; daily cleanup |
| Env | `CROSSREF_MAILTO`, `CROSSREF_PLUS_TOKEN`, `OPENALEX_BASE_URL`, `SEMANTIC_SCHOLAR_API_KEY`, `ENABLE_*` |
| Soft-fail | Provider errors never fail upload/import jobs |
| Known gaps | PubMed deferred; Related empty-state polish; verified citation badge in Citations UI; OA PDF fetch deferred |

---

### Notes

**Status:** Implemented — `/api/notes`, `features/notes/`; also reachable via ⌘K / toolbars

---

### Dashboard

**Status:** Implemented — `GET /api/dashboard`, Home launchpad (D2): Today’s Focus, library analysed/processing counts, open workspace CTA

---

### Web search (in chat)

**Status:** Implemented — `ddgs` tool in chat Responses API loop (`server.py`); disabled in paper-scoped chat

---

### Writing assistant

**Status:** Implemented — `POST /api/writing`, `features/writing/`; D7 T4 Draft/Export chrome; page still uses raw `fetch` in places vs shared `writingApi.transform`

---

### Multi-paper compare & gap analysis

**Status:** Implemented — rate-limited; cached in `derived_analyses`; D7 T4 tool UI; Library CollectionToolbar + Project + ⌘K entry

---

### Shell / Design System (SPA)

**Status:** Implemented (D1–D9)

| Area | Detail |
|------|--------|
| Tokens | Teal signal primary; denser spacing/type (`frontend/src/index.css`) |
| Shell | Slim sidebar, `ObjectHeader`, sticky paper tabs, ⌘K `CommandPalette`, skip link + `<main>` |
| Tools | CollectionToolbar (Compare / Citations / Writing / Filters / Upload) |
| Trust | `ErrorBoundary`, route `errorElement`, `SessionExpiredModal` |
| Specs | `docs/DESIGN-SYSTEM-v2.md`, `docs/Interaction-Guidelines.md`, `docs/prototypes/d0.5/` |

---

### Export

**Status:** Implemented — account export, notes, analysis, chat export endpoints

---

### Support & legal

**Status:** Partial — Support form Implemented; Legal pages **Partial** (placeholder emails/entity strings in `features/legal/content.ts`)

---

### Admin

**Status:** Partial — Admin APIs for prompts + usage analytics (`is_admin`); **no** admin UI dashboard; first admin is manual DB update

---

### Quotas

**Status:** Partial — Storage + monthly tokens on JWT upload/analysis paths; session `/api/files` has inline storage check; **chat not token-quota gated**

---

### Payments / billing

**Status:** Not Implemented — comment in `server.py` ~2719 notes avoiding billing API at this scale

---

### Notifications (push/email product notifications)

**Status:** Not Implemented — transactional email only (magic link, support ack)

---

### Virus scanning / ClamAV

**Status:** Not Implemented — described in `docs/production-hardening.md` only

---

### n8n / external automation

**Status:** Not Implemented

---

### Feature flags (runtime)

**Status:** Not Implemented in app — table `feature_flags` exists via migration `0008`; **no ORM/service reads or writes**

---

# 3. Complete Module Map

| Module | Purpose | Responsibilities | Dependencies | Implementation level |
|--------|---------|------------------|--------------|----------------------|
| **Authentication** | Identity | Google OAuth, magic link, DEV login, session, JWT mint/refresh | Authlib, JWT-Extended, Resend | **Implemented** |
| **Projects** | Workspace scoping | CRUD, instructions, filter chats/files | `projects` table | **Implemented** |
| **Knowledge Library** | Document store | Upload, list, tags, stats, ownership | storage, worker, files | **Implemented** |
| **Paper Analysis** | Per-paper LLM summary + Phase 1 structured pipeline | Worker phase1→paper_analysis, HTTP analysis, AnalysisPipelineService; SPA Paper Workspace tabs | OpenAI, prompts, Phase 1 engines | **Implemented** |
| **Prompt Engine** | Versioned prompts / personas / assembly | Registry, builder, seed, analytics, admin API; `phase1_context` | Jinja2 sandbox, DB | **Partial** (Paper Chat Stage 1 flagged OFF by default) |
| **RAG** | Retrieval + optional answer | Chunk embeddings, cosine, `/api/rag` | OpenAI embed | **Implemented** (simple) |
| **Memory** | Durable user facts | Chat write + Memory page + MemoryEngine | `memories` | **Implemented** |
| **Citation Manager** | Bibliography | CRUD, export, tool | `citations` | **Implemented** |
| **Export** | Data portability | JSON/Markdown exports | session auth | **Implemented** |
| **Dashboard** | Home stats | Aggregate recent activity | `/api/dashboard` | **Implemented** |
| **Uploads** | Ingest pipeline | Validation, storage, jobs | worker, imports | **Implemented** (dual APIs) |
| **Search** | Corpus + RAG UI + Discover | `/api/search`, `/api/rag`, `/api/discover*` | chunks, notes, OpenAlex | **Implemented** |
| **Scholarly** | External paper metadata | Crossref enrich, OpenAlex Discover, S2 Related | `backend/scholarly/`, provider_* tables | **Implemented** (core) |
| **Analytics** | Cost/usage | Admin prompt-usage APIs | ledgers | **Partial** (no product analytics) |
| **Notifications** | User alerts | — | — | **Not Implemented** |
| **Settings** | Preferences | Theme, models, data controls, privacy | profile/export APIs | **Implemented** |
| **Admin** | Ops control | Prompt CRUD, usage | `is_admin` | **Partial** (API only) |
| **Explain / explainability UI** | Model decision UI | Paper Evidence / Classification / Entities / Graph tabs + chat confidence chips | Phase 1 APIs + mappers | **Partial** (structured inspect yes; no global tool-call inspector) |
| **Document Understanding** | Structured PDF parse | `DocumentUnderstandingPipeline` + SPA Structure tab | pymupdf, etc. | **Implemented** (engine + UI) |
| **Classification pass1/pass2** | Domain/type/study design | Rule/LLM-ish pipelines + SPA Classification tab | processing / DU models | **Implemented** (engine + UI; pass2 primary) |
| **Medical Understanding** | PICO / entities | Extractors, registry + SPA Entities tab | — | **Implemented** (engine + UI; routing-gated) |
| **Evidence Grading** | GRADE/Oxford/NIH/SIGN | Assessments + aggregators + SPA Evidence tab | — | **Implemented** (engine + UI; routing-gated) |
| **Analysis Context** | Routing/prompt profiles | Profiles pipeline + classification context UI | classification outputs | **Implemented** (engine + partial UI) |
| **Knowledge Graph** | Entity-relation graph | Pipeline + SPA Graph tab (read-only) | — | **Implemented** (in-memory JSON; no graph DB) |
| **Design System / Shell** | Research OS chrome | D1–D9 tokens, sidebar, palette, a11y, session modal | React SPA | **Implemented** |
| **Processing (legacy)** | Older PDF section pipeline | Feed for pass1 tests | — | **Library** (superseded conceptually by DU) |
| **Storage** | Object blobs | R2/local/S3 | boto3 | **Implemented** (two facades) |
| **Imports** | Text extraction | pdf/docx/pptx/xlsx/epub/zip/text | PyMuPDF, etc. | **Implemented** (live) |
| **Quotas** | Abuse/cost bounds | Storage + monthly tokens | `usage_logs`, user cols | **Partial** |
| **Observability** | Logs + metrics | JSON logs, Prometheus | prometheus_client | **Implemented** |
| **Worker** | Async jobs | Poll, claim, retry, heartbeat; Crossref enrich on import | Postgres + scholarly | **Implemented** |

---

# 4. Architecture Overview

## High-level stack

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (React SPA)                                       │
│  Vite build → frontend/dist  served by Flask in prod        │
└──────────────────────────┬──────────────────────────────────┘
                           │ Cookie session  /  Bearer JWT
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  API — Flask server.py + blueprints                         │
│  auth/, backend/upload, backend/search, backend/prompts     │
└────────────┬─────────────────────────────┬──────────────────┘
             │                             │
             ▼                             ▼
┌────────────────────┐          ┌────────────────────────────┐
│  Services          │          │  Object Storage            │
│  Quotas, AI, RAG   │          │  R2 / Local / S3           │
│  Imports (sync)    │          └────────────────────────────┘
└─────────┬──────────┘
          ▼
┌────────────────────┐          ┌────────────────────────────┐
│  Database          │◄─────────│  worker.py                 │
│  Postgres (+SQLite │  poll    │  import / metadata /       │
│  for API-only)     │  jobs    │  paper_analysis            │
└─────────┬──────────┘          └─────────────┬──────────────┘
          │                                   │
          │                                   ▼
          │                     ┌────────────────────────────┐
          └────────────────────►│  OpenAI (+ optional        │
                                │  Anthropic / Gemini)       │
                                └────────────────────────────┘
```

## Important flows

### Chat (legacy prompt path)

```
Client → POST /api/chat (session)
  → load conversation + ownership check
  → build_system_prompt → PromptBuilder.build_chat_instructions (normal chat)
     or build_paper_chat_prompt (paper-scoped chat)
  → rag_retrieve (chunks cosine)
  → OpenAI Responses API stream (+ tools: web_search, save_citation)
  → persist messages → SSE to client
```

### JWT RAG answer (Prompt Engine path)

```
Client → GET /api/auth/jwt → Bearer
  → POST /api/rag
  → ModelRegistry.embed(query)
  → cosine over user Chunks
  → PromptBuilder (semantic_search) → model call → PromptExecution
  → answer + sources
```

### Upload → ready (Phase 2)

```
Client upload (/api/files | /api/documents/upload | /api/uploads/bulk)
  → validate size/(ext) → quota → storage.put
  → UserFile + UploadJob(import) + OutboxEvent
  → worker claims import
  → imports.extract_text → chunk_* → embed_texts → Chunk rows
  → Crossref enrich (DOI from text; soft-fail; provenance on UserFile)
  → enqueue phase1_analysis
  → AnalysisPipelineService (1.1→1.7) → analysis_pipeline_results
  → apply bibliographic metadata to UserFile (merge; don’t blindly overwrite Crossref)
  → enqueue paper_analysis
  → PromptBuilder (+ phase1_context) → PaperAnalysis.data
  → Ready for RAG / paper UI / GET …/pipeline
```

Discover import (`POST /api/discover/import`) creates a metadata-only `UserFile` (no blob); Phase 1/RAG wait until the user uploads a PDF later.

Legacy note: `extract_metadata` handler remains for in-flight jobs (deprecated). Confirm-upload may still use thread paths (`_apply_metadata` / `_run_paper_analysis`) — marked deprecated.

### Auth

```
Google / Magic link / DEV
  → session[user_id] (+ session[jwt])
  → SPA uses cookie for most APIs
  → getBearerToken() for document/search/RAG JWT routes
```

---

# 5. Database Audit

**Bootstrap:** `Base.metadata.create_all()` + `ensure_columns()` in `server.py`, then `run_migrations.py` for `migrations/*.sql`. **No Alembic.** Three SQLAlchemy declarative Bases (server, prompt_registry, model_registry).

**Domain `models.py` files** under `backend/{processing,document_understanding,...}` are **dataclasses**, not ORM tables.

## Tables

### `users`
- **Purpose:** Accounts, quotas, admin  
- **Columns (ORM):** id, email (unique), name, picture, custom_instructions, auth_provider, created_at, storage_limit_bytes, monthly_token_used, monthly_token_limit, quota_reset_at, is_admin  
- **Indexes:** unique email  
- **Relationships:** Logical parent of user-scoped rows  
- **Migration:** create_all + 0010, 0011, 0016  
- **Concerns:** Admin bootstrapped manually  

### `projects`
- **Purpose:** Workspaces  
- **Columns:** id, user_id FK, name, emoji, description, instructions, created_at  
- **Indexes:** PK only — **missing** `user_id` index  
- **Migration:** create_all + 0015 (`instructions`)  

### `conversations` / `messages`
- **Purpose:** Chat  
- **Columns:** Conversations: user/project/file, title, model, temperature, reasoning_effort, memory_enabled, timestamps; Messages: role, content, sources, attachments  
- **Relationships:** ORM cascade Conversation↔Message  
- **Indexes:** **Missing** on `conversation_id`, `user_id`, `updated_at`  

### `memories`
- **Purpose:** Durable facts  
- **Indexes:** **Missing** on `user_id`  

### `files` (`UserFile`)
- **Purpose:** Uploaded documents + library metadata (+ Discover stubs)  
- **Indexes:** `ix_files_user`, `ix_files_user_checksum`  
- **Relationships:** → chunks  
- **Scholarly cols (0018–0021):** `doi`, `doi_verified`, `metadata_source`, provenance fields, `source_url` (OpenAlex/landing URL for stubs)  
- **Stubs:** empty `path` / no blob until user uploads PDF; delete/raw handlers guard empty paths  

### `chunks`
- **Purpose:** RAG segments + embeddings  
- **Columns:** file_id, idx, content, embedding (Text JSON), page, section  
- **Indexes:** `ix_chunks_file`  
- **Concerns:** No vector index; embeddings as JSON text  

### `upload_sessions` / `upload_batches` / `upload_jobs`
- **Purpose:** Presign sessions; bulk grouping; worker queue  
- **Job types:** `import` | `phase1_analysis` | `paper_analysis` | `extract_metadata` (legacy) — `job_type` VARCHAR(40) after 0017  
- **Indexes:** User indexes; pending partial index from migration 0002 (**not** recreated in `ensure_columns` — SQLite path lacks it; worker requires Postgres anyway)  
- **`pipeline_version_id`:** Soft ORM FK; real FK in 0005; rarely populated  

### `storage_usage`
- **Purpose:** Live quota counters  
- **Drift:** Migration `bigint` vs ORM `Integer` for `bytes_used` — overflow risk  

### `import_sessions`
- **Purpose:** Intended checkpoints  
- **Status:** **Schema only — no writers**  

### `outbox_events`
- **Purpose:** Transactional outbox with jobs  
- **Note:** Worker polls jobs directly; outbox marked dispatched — not a separate consumer  

### `model_versions` / `ai_usage_ledger`
- **Purpose:** Model versioning + per-call cost (legacy/server path)  
- **Note:** Chat/memory/title coverage incomplete per code comments  

### `worker_heartbeats`
- **Purpose:** Liveness for `/api/worker/health`  
- **Also:** Daily scholarly `provider_cache` cleanup on heartbeat path  

### Scholarly ops tables (migrations 0018–0020)
- **`provider_cache`:** Shared HTTP response cache (SWR + fetch locks / `locked_by`)  
- **`provider_metrics`:** Counter/histogram-style rows for provider calls  
- **`provider_circuit`:** DB-backed circuit breaker state per provider  

### `citations` / `notes` / `support_requests`
- **Purpose:** Product features  
- **Indexes:** `ix_notes_user`; citations/support lack `user_id` indexes  

### `paper_analyses` / `derived_analyses` / `analysis_pipeline_results`

- **`paper_analyses`:** LLM 14-field overview JSON (`PaperAnalysis.data`) — product UI primary cache  
- **`derived_analyses`:** multi-paper compare/gaps cache  
- **`analysis_pipeline_results`:** Phase 1.1–1.7 JSON (`phase_results` Text/JSON), one row per `file_id`, content_hash idempotency, status `pending|running|done|failed|partial` — migration **0017**, ORM `AnalysisPipelineResult`  
- **Lazy migration:** older files have no row until first `phase1_analysis` / `POST …/analyze`  

### `search_index`
- **Purpose:** Unified embeddings for notes/citations/chats  
- **Status:** **ORM exists; nothing writes rows** (orphan)  

### `usage_logs`
- **Purpose:** Coarse quota audit (`quotas/models.py`)  

### AI tables
| Table | Status |
|-------|--------|
| `prompt_versions` | Implemented + 0015 authoring cols |
| `personas` | Implemented |
| `prompt_executions` | Written on RAG + sync analysis |
| `model_registry_cost_ledger` | create_all (no CREATE migration); 0015 ALTER |
| `model_presets` | Seeded |
| `pipeline_versions` | Migration + backfill; **factory not on live server Base** |

### Migration-only / views
| Object | Status |
|--------|--------|
| `feature_flags` | **Unused** |
| `processing_metrics_daily` | Materialized view — **no refresh job in code** |
| `schema_migrations` | `run_migrations.py` tracker |

## Future concerns
- Dual schema bootstrap drift (create_all vs migrations vs ensure_columns)  
- Three Bases → soft FKs  
- Linear RAG will not scale  
- Chat FK indexes needed before multi-user load  

---

# 6. API Audit

Auth: **Session** = `@login_required`; **JWT** = `@jwt_required`; **Admin** = session + `is_admin`; **Public** = none.

Rate limits: Flask-Limiter **memory://** (not multi-process safe). Only routes listed below have limits.

## Auth

| Method | Route | Auth | Rate limit | Purpose |
|--------|-------|------|------------|---------|
| GET | `/login` | Public | — | Login / DEV auto |
| GET | `/auth/google` | Public | — | OAuth start |
| GET | `/auth/callback` | Public | — | OAuth complete |
| GET | `/logout` | Public | — | Clear session |
| POST | `/api/dev-login` | Public if DEV else 403 | — | Dev session |
| POST | `/auth/magic-link` | Public | 3/hour/email | Request link |
| POST | `/auth/magic-link/verify` | Public | — | Verify → session |
| GET | `/api/auth/jwt` | Session | — | Mint Bearer |
| POST | `/api/auth/token` | Refresh JWT | — | Refresh tokens |

**Validation / security notes:** Magic verify unthrottled; CSRF Origin check applies to `/api/*` only (not `/auth/*`).

## User / models / support

| Method | Route | Auth | Rate | Purpose |
|--------|-------|------|------|---------|
| GET | `/api/me` | Session | — | Current user |
| PATCH | `/api/profile` | Session | — | Profile / instructions |
| GET | `/api/models` | Session | — | Model list |
| POST | `/api/support` | Public (optional session) | 6/h; 30/d | Ticket |
| DELETE | `/api/account` | Session | 5/h | Wipe account |

## Files / uploads / library / dashboard

| Method | Route | Auth | Purpose |
|--------|-------|------|---------|
| POST/GET | `/api/files` | Session | Upload / list |
| GET/PATCH/DELETE | `/api/files/<fid>` | Session | CRUD |
| GET/POST | `/api/files/<fid>/analysis*` | Session | Analysis |
| GET | `/api/files/<fid>/raw` | Session | Download (presign redirect) |
| GET | `/api/jobs/<job_id>/status` | Session | Job poll |
| POST | `/api/uploads/presign` | Session | Presign (FE not primary) |
| POST | `/api/uploads/multipart/complete` | Session | Multipart |
| POST | `/api/uploads/confirm` | Session | Confirm (may sync-process) |
| PUT/GET | `/api/uploads/local-put\|get/<key>` | Signed token | Local storage |
| GET | `/api/library/tags`, `/stats` | Session | Library |
| GET | `/api/dashboard` | Session | Dashboard |
| POST | `/api/documents/upload` | JWT | JWT upload |
| POST | `/api/documents/<id>/analysis` | JWT | Sync LLM analysis (injects Phase 1 context if cached) |
| POST | `/api/documents/<id>/analyze` | JWT | Trigger Phase 1 pipeline (async job; `?sync=1` inline) |
| GET | `/api/documents/<id>/pipeline` | JWT | Full Phase 1 `phase_results` JSON |
| GET | `/api/documents/<id>/phases/<phase>` | JWT | One Phase 1 stage result |
| POST | `/api/uploads/bulk` | JWT | Bulk |
| GET | `/api/uploads/batch/<id>/status` | JWT | Batch status |

**Missing validation:** Magic-byte MIME; session upload any extension; JWT vs session policy mismatch.

## Search / RAG

| Method | Route | Auth | Rate | Purpose |
|--------|-------|------|------|---------|
| GET | `/api/documents/search` | JWT | — | Vector search |
| POST | `/api/rag` | JWT | — | RAG answer |
| POST | `/api/search` | Session | 60/min | Unified search |

## Notes / citations / projects / conversations / memories

Standard session CRUD on `/api/notes`, `/api/citations` (+ from-paper, export), `/api/projects`, `/api/conversations` (+ bulk delete), `/api/memories`. Ownership checks via `user_id` on typical paths.

## Chat / analysis / writing / export

| Method | Route | Auth | Rate | Purpose |
|--------|-------|------|------|---------|
| POST | `/api/chat` | Session | **None** | Streaming chat |
| POST | `/api/analysis/compare` | Session | 20/h | Compare |
| GET/DELETE | `/api/analysis/compare/<id>` | Session | — | Cache |
| POST | `/api/analysis/gaps` | Session | 20/h | Gaps |
| GET/DELETE | `/api/analysis/gaps/<id>` | Session | — | Cache |
| POST | `/api/writing` | Session | 30/h | Writing transform |
| GET | `/api/export` | Session | 60/h | Account export |
| POST | `/api/export/notes` | Session | — | Notes export |
| GET | `/api/export/analysis/<file_id>` | Session | — | Analysis export |
| GET | `/api/export/chat/<cid>` | Session | — | Chat export |

## Prompt admin / AI utilities

| Method | Route | Auth | Purpose |
|--------|-------|------|---------|
| GET/POST/PATCH | `/api/prompts*` | Session / Admin mutations | Prompt engine CRUD |
| POST | `/api/prompts/preview` | Session | Preview assembly |
| GET/POST | `/api/personas` | Session / Admin create | Personas |
| GET | `/api/prompt-usage*` | Admin | Analytics |
| GET | `/api/ai/prompts` | Session | List prompts |
| POST | `/api/ai/test` | Session | Test call |

## Ops / static

| Method | Route | Auth | Purpose |
|--------|-------|------|---------|
| GET | `/metrics` | **Unauthenticated** | Prometheus |
| GET | `/api/worker/health` | **Unauthenticated** | Worker liveness |
| GET | `/robots.txt` | Public | SEO |
| GET | `/`, `/<path>`, `/assets/*` | Public | SPA |

**Typical error codes:** `401` not_authenticated; `403` forbidden/admin/DEV; `404` ownership miss disguised as not found; `429` limiter; `413` body too large. Exact JSON schemas: Unable to verify every route’s full error contract without exhaustive reading of each handler — patterns above are consistent across audited routes.

---

# 7. Security Audit

| Control | Status | How it works |
|---------|--------|--------------|
| **Authentication** | Implemented | Google OAuth (Authlib), magic link (timed serializer 15m), DEV auto-login |
| **Authorization** | Partial | Per-resource `user_id` checks common; PromptBuilder project load missing owner check; admin session-only |
| **Session management** | Implemented | HttpOnly + SameSite=Lax; Secure in production; idle + absolute TTL (PR4) |
| **CSRF** | Partial | Origin/Referer check on `/api` mutations; no CSRF tokens; `/auth/*` excluded; no Origin → allowed (API clients) |
| **CORS** | Missing (by design) | Same-origin / Vite proxy; no flask-cors |
| **Cookies** | Implemented | Session flags above; JWT also stored in session after login |
| **Password storage** | N/A | No passwords |
| **Google OAuth** | Implemented | OpenID scopes; optional `ALLOWED_EMAILS` |
| **JWT** | Implemented | HS256; ~15m access / ~30d refresh; refresh rejects deleted users |
| **File validation** | Partial | JWT ext allowlist + size; session any type; client MIME trusted |
| **MIME validation** | Partial | Extension-based; client `mimetype` stored |
| **Magic byte validation** | Missing | No python-magic / filetype sniff |
| **XSS protection** | Implemented | DOMPurify (`frontend/src/lib/markdown.ts`); rehype-sanitize on analysis |
| **SQL injection** | Implemented | ORM + bound params; raw SQL only for fixed DDL/migrations |
| **ORM safety** | Implemented | SQLAlchemy 2 style queries |
| **Secrets management** | Partial | Env vars; random secret fallback if unset (multi-worker footgun) |
| **Environment variables** | Partial | `.env.example` incomplete vs code (JWT_*, AWS_*, etc.) |
| **OpenAI key protection** | Implemented | Server-only `OPENAI_API_KEY`; not in frontend env |
| **Prompt injection protection** | Partial | Sectioned prompts, Jinja sandbox; user/doc text still in context; no classifier |
| **RAG isolation** | Implemented | Retrieval scoped by `user_id` (+ project/file filters) |
| **Project isolation** | Partial | Most routes filter user; PromptBuilder gap |
| **Object ownership validation** | Implemented | Typical 404 on `user_id` mismatch for files/notes/etc. |
| **Download permissions** | Implemented | Ownership then presigned/local signed URL |
| **Upload permissions** | Implemented | login/JWT + quota |
| **Session expiration** | Partial | JWT TTLs yes; Flask session until logout |
| **Reauthentication** | Missing | No step-up auth for destructive actions beyond rate limit on delete |
| **Delete account security** | Implemented | Authenticated + 5/h; deletes user data; clears session |
| **Logging** | Implemented | JSON logs + correlation id; `log_security_event` |
| **Security headers** | Missing | No CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy |
| **Clickjacking** | Missing | No X-Frame-Options / CSP frame-ancestors |
| **Content Security Policy** | Missing | — |
| **Rate limiting** | Partial | Selective routes; in-memory; chat unlimited |
| **Brute-force protection** | Partial | Magic-link request limited; verify/OAuth not |
| **DoS protection** | Partial | Body size limits; no global API throttle; metrics open |
| **Quota enforcement** | Partial | Storage broadly; tokens on JWT analysis not chat |
| **Abuse prevention** | Partial | Allowlist optional; quotas; selective limits |
| **Token budgeting** | Partial | Hard char truncations; monthly token quota incomplete |
| **OpenAI token limits** | Partial | Provider limits + local truncations; no tiktoken budgeter |
| **Request size limits** | Implemented | `MAX_CONTENT_LENGTH` from env |
| **Upload size limits** | Implemented | `MAX_FILE_MB` (25), `MAX_DOCUMENT_UPLOAD_MB` (50) |
| **Worker isolation** | Partial | Separate process; parsers can still run on request (presign confirm); no Celery sandbox |
| **Temporary file cleanup** | Implemented | `finally` removes; temp sweeps; upload session GC |
| **Storage permissions** | Partial | Key prefix `users/{id}/...`; OS user via systemd |
| **Cloud storage access** | Implemented | R2/S3 credentials server-side |
| **Presigned URLs** | Implemented | Upload/download; local signed put/get |
| **Virus scanning** | Missing | Planned in docs only |
| **Dependency vulnerabilities** | Missing | No pip-audit/npm audit/Dependabot in CI |

---

# 8. Prompt Engine Audit

## Architecture

Layered `PromptBuilder` (`backend/ai/prompt_builder.py`):

**System → Persona → Project Context → Memory → Retrieved Context → Task (+ domain) → Output Format**

Supporting components: `PromptRegistry`, `SystemPromptManager`, `PersonaEngine`, `MemoryEngine`, `DomainRegistry`, `ModelRouter`, `ModelRegistry`, `CostLedger`, `PromptAnalytics`, seed data.

## Prompt generation flow

1. Resolve prompt template by name (`active` version)  
2. Optionally detect domain/document type  
3. Assemble sections into `AssembledPrompt`  
4. Call `ModelRegistry`  
5. Record `PromptExecution` + cost ledger (on wired paths)

## System / developer prompts

- Versioned `system_prompt` row via SystemPromptManager  
- Chat uses separate legacy `chat_system` / `build_system_prompt` in `server.py`  

## Dynamic building / intent / domain

- Domain: keyword/venue first-match (`domain_registry.py`) — **Partial**  
- Intent detection as a dedicated classifier: **Not Implemented**  
- Seeded domain modules: medical (real) + ai_ml (placeholder); other domains registered without modules  

## Context injection

| Layer | Prompt Engine | Chat |
|-------|---------------|------|
| System | Yes | Legacy |
| Persona | Optional | No |
| Project | Yes | Yes |
| Memory | Top-5 keyword | All matching |
| RAG | Dedicated section | Developer message |
| Domain | Task append | No |
| Phase 1 structured | `phase1_context` on paper analysis | No |

## Memory / project / RAG / refinement

- MemoryEngine + project instructions: Implemented on engine path  
- RAG context: Implemented on `/api/rag`  
- Prompt refinement / iterative rewrite: **Not Implemented** as a product loop  

## Output formatting / safety / versioning / caching

- Expected output types + medical JSON schemas in `prompts.py`: Implemented for analysis templates  
- Safety: accuracy/no-fabricate instructions; Jinja sandbox — **Partial**  
- Versioning: draft/active/archived — **Implemented**  
- Caching of assemblies/embeddings: **Missing**  

## Model routing / optimization

- `ModelRouter` task→model policy: Implemented (process-local overrides)  
- Token optimization: hard caps only (`META_EXCERPT_CHARS`, `ANALYSIS_MAX_CHARS`, chunk 1500, etc.)  

## Current limitations

1. Chat outside PromptBuilder (worker paper analysis now uses builder + Phase 1)  
2. `semantic_search` template `{{ documents }}` vs builder vars mismatch  
3. Dual ledgers / incomplete `prompt_version_id` on legacy paths  
4. PipelineVersion unused live  
5. `citation_generation` seeded but unwired  
6. A/B multi-active versions unsupported (partial unique active)  
7. DomainRegistry may disagree with Phase 1.2 classification labels  

## Future improvements (from gaps, not marketing)

- Migrate chat to PromptBuilder (`docs/chat-migration-roadmap.md` / preview stub in code)  
- Prefer Phase 1.2 domain over DomainRegistry when both available  
- Unify ledgers; vector-backed memory ranking  

---

# 9. RAG Audit

| Topic | Current state |
|-------|----------------|
| **Chunking** | `chunk_text` / `chunk_document` in `server.py`: size **1500**, overlap **200**, max **400** chunks; PDF page markers via imports |
| **Embeddings** | `text-embedding-3-small` (default); batches of 64; stored JSON floats on `Chunk.embedding` |
| **Retrieval** | Load in-scope chunks; cosine similarity in Python |
| **Ranking** | Cosine only — no reranker, no hybrid BM25 |
| **Citation generation** | Source metadata (file, page, section, score) returned; chat instructed to cite; BibTeX manager separate |
| **Context assembly** | Top-k snippets truncated (~1500 chars); chat injects developer JSON |
| **Metadata** | page, section, file ownership, project/file filters |
| **Search quality** | Adequate for small personal libraries; degrades with corpus size |
| **Weaknesses** | No pgvector/FAISS; `search_index` dead; dual chat vs JWT semantics; no embedding/query cache; scanned PDFs yield empty text notes without OCR indexing |

---

# 10. Upload Pipeline

```
Client
  → Validation (size; JWT ext allowlist; session any type)
  → Storage (R2/local/S3 via dual facades)
  → DB: UserFile + UploadJob(import) + Outbox
  → worker import: extract → chunk → embed
  → worker phase1_analysis: AnalysisPipelineService (1.1→1.7)
       → persist analysis_pipeline_results
       → fill UserFile bibliographic fields when Phase 1.1 provides them
  → worker paper_analysis: PromptBuilder(+phase1_context) → PaperAnalysis
  → Ready (RAG + paper UI + GET …/pipeline)
```

| Concern | Detail |
|---------|--------|
| **Memory** | Full extracted text in process; Phase 1 holds structured objects; embeddings held before commit |
| **Storage** | Objects in R2/local; DB metadata + chunks + `analysis_pipeline_results` |
| **Performance** | Phase 1 target ~&lt;12s/doc (deterministic); LLM paper_analysis dominates cost/latency |
| **Limits** | 25 MB session / 50 MB JWT doc; batch size `MAX_BATCH_SIZE` (default 50); 400 chunk cap |
| **On path** | document_understanding → classification → analysis_context → medical → evidence_grading → prompt_assembly → knowledge_graph |
| **Deprecated** | Direct enqueue of `extract_metadata` after import; thread `_apply_metadata` / `_run_paper_analysis` |

---

# 11. Background Jobs

| Topic | State |
|-------|--------|
| **Queues** | Postgres `upload_jobs` |
| **Workers** | `python worker.py` — requires Postgres |
| **Handlers** | `import`, **`phase1_analysis`**, `paper_analysis`; `extract_metadata` (legacy/in-flight only) |
| **Primary chain** | `import` → **Crossref enrich (DOI)** → `phase1_analysis` → `paper_analysis` |
| **Retry** | Backoff `attempts * 60s`; max `WORKER_MAX_ATTEMPTS` (5); then `failed` |
| **Partial failure** | Phase failures inside AnalysisPipelineService → `partial`/`failed` status + errors list; completed phases still persisted when possible; Crossref soft-fails |
| **Checkpointing** | `import_sessions` table **unused** — full job restart |
| **Scheduling** | Poll loop `WORKER_POLL_INTERVAL` (2s); batch `WORKER_BATCH_SIZE` (10) |
| **Automation / n8n** | **Not Implemented** |
| **Redis** | Optional status cache only |
| **Heartbeat** | `worker_heartbeats` + `/api/worker/health`; scholarly daily cleanup |
| **Outbox** | Written with jobs; not independently consumed |

ADR-0001: **Keep Postgres worker; do not migrate to Celery** (decision recorded; design docs mentioning Celery are superseded for queue choice).

---

# 12. Performance Audit

| Area | Finding |
|------|---------|
| **Large PDFs** | Full-text in memory; 400-chunk cap truncates long docs; scanned PDFs weak |
| **Memory usage** | Extraction + embed batches; worker single-process |
| **Database** | Missing chat/message indexes; JSON embeddings; linear scans |
| **API latency** | Sync analysis & some confirm paths can be long; chat streams |
| **OpenAI latency** | Dominant cost for chat/analysis/embed |
| **Frontend** | SPA + TanStack Query; streaming SSE |
| **Caching** | Derived analysis cache; Redis job status optional; **`provider_cache` SWR** for scholarly APIs; no RAG cache |
| **Streaming** | Chat SSE Implemented |
| **Worker utilization** | Sequential jobs per process; horizontal scale via more workers |

Documented intentional bottleneck: in-Python cosine over all user chunks (`docs/upload-architecture.md`).

---

# 13. Monitoring

| Area | Status | Detail |
|------|--------|--------|
| **Logging** | Implemented | JSON + `X-Request-ID` / correlation (`observability/`) |
| **Metrics** | Implemented | Prometheus `/metrics`; worker port `WORKER_METRICS_PORT`; scholarly provider counters |
| **Analytics** | Partial | Admin prompt/cost APIs only; no product analytics SDK |
| **Error tracking** | Missing | No Sentry (or equivalent) |
| **Alerts** | Missing in repo | Docs mention Prometheus ops; no alertmanager config |
| **Admin dashboard** | Partial | APIs only; no ops UI |
| **Provider health** | Implemented | `GET /api/health/providers` (circuit/bulkhead/cache status) |

---

# 14. Configuration Audit

## From `.env.example`

| Variable | Purpose | Required? | Default | Security |
|----------|---------|-----------|---------|----------|
| `OPENAI_API_KEY` | OpenAI | Prod yes | empty | Server secret |
| `FLASK_SECRET_KEY` | Sessions / magic link | Prod yes | random/boot | Must set in prod |
| `DATABASE_URL` | DB | Yes | sqlite file | Prod Postgres |
| `FLASK_ENV` / `APP_ENV` | Secure cookies | Soft | development | Set production |
| `GOOGLE_CLIENT_ID/SECRET` | OAuth | For Google | empty | Secrets |
| `ALLOWED_EMAILS` | Allowlist | Optional | blank=open | Open signup risk |
| `DEV_AUTO_LOGIN` | Skip OAuth | Dev only | example=`1` | **Must clear in prod** |
| `DEFAULT_MODEL` / `UTILITY_MODEL` / `EMBED_MODEL` / `MODELS` | Models | Optional | gpt-4o-mini etc. | Cost |
| `MAX_FILE_MB` | Session upload | Optional | 25 | DoS bound |
| `MAX_DOCUMENT_UPLOAD_MB` | JWT upload | Optional | 50 | |
| `R2_*` | Object storage | If R2 | empty→local | Secrets |
| `STORAGE_BACKEND` | r2/local/s3 | Optional | auto | |
| `WORKER_*` | Poll/batch/attempts/metrics/health | Optional | 2/10/5/9101/60 | Metrics exposure |
| `REDIS_URL` | Job status cache | Optional | empty | Optional |
| `RESEND_API_KEY` / `EMAIL_FROM` / `SUPPORT_EMAIL` | Email | Optional | log fallback | |
| `APP_BASE_URL` | Absolute URLs / CSRF host | Soft | localhost:5000 | Must match prod host |
| `CROSSREF_MAILTO` | Crossref polite pool identity | Recommended | empty | Public email OK |
| `CROSSREF_PLUS_TOKEN` | Crossref Plus (optional) | Optional | empty | Secret |
| `OPENALEX_BASE_URL` | OpenAlex API base | Optional | public API | No key required |
| `SEMANTIC_SCHOLAR_API_KEY` | Related papers | Optional | empty | Secret; Related empty without it |
| `ENABLE_CROSSREF` / `ENABLE_OPENALEX` / `ENABLE_SEMANTIC_SCHOLAR` | Feature flags | Optional | on | Ops kill-switch |
| `PAPER_CHAT_PIPELINE_ENABLED` | AI Core Stage 1 Paper Chat | Optional | off | `false` / `shadow` / `true` |

## Used in code but not in `.env.example`

`JWT_SECRET_KEY`, `JWT_ACCESS_TOKEN_EXPIRES_MIN`, `JWT_REFRESH_TOKEN_EXPIRES_DAYS`, `MULTIPART_THRESHOLD_MB`, `UPLOAD_PART_SIZE_MB`, `UPLOAD_SESSION_TTL_MINUTES`, `MAX_BATCH_SIZE`, `STORAGE_PROVIDER`, `LOCAL_STORAGE_DIR`, `AWS_S3_*` / `AWS_REGION`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `{TASK}_MODEL` overrides.

CI sets unused `SECRET_KEY` (app expects `FLASK_SECRET_KEY`).

---

# 15. Third-party Services

| Service | Purpose | Current usage |
|---------|---------|---------------|
| **OpenAI** | Chat, embeddings, analysis | Primary |
| **Google OAuth** | Login | Implemented |
| **Google Gemini** | Optional LLM | If `GOOGLE_API_KEY` set |
| **Anthropic** | Optional LLM | If `ANTHROPIC_API_KEY` set |
| **Postgres** | Primary DB / queue | Prod + worker |
| **SQLite** | Local/dev/tests | Default local |
| **Redis** | Optional job status cache | Not required for correctness |
| **Cloudflare R2** | Object storage | When configured |
| **AWS S3** | Alternate storage | `STORAGE_BACKEND=s3` |
| **Resend** | Magic link + support email | Optional |
| **DuckDuckGo (`ddgs`)** | Chat web_search tool | Implemented |
| **n8n** | Automation | **Not Implemented** |
| **Product analytics** | Usage telemetry | **Not Implemented** |
| **Sentry** | Error tracking | **Not Implemented** |
| **Payments** | Billing | **Not Implemented** |

---

# 16. Production Readiness Score

| Area | Score /10 | Rationale |
|------|-----------|-----------|
| **Architecture** | 7 | Phase 1+2 unified analysis path on worker; dual stacks (chat vs engine, two uploads/storages) remain |
| **Security** | 5 | Good ownership/XSS/ORM/OAuth; missing headers/MIME/virus scan; open metrics; PromptBuilder IDOR risk; chat unthrottled |
| **Performance** | 5 | Fine for personal scale; linear RAG + missing indexes; Phase 1 adds CPU per upload but stays deterministic |
| **Scalability** | 4 | Single-node friendly; no vector index; in-memory limiter; SQLite not worker-capable |
| **Maintainability** | 5 | `server.py` monolith; three Bases; Phase 1 packages modular; branding inconsistency |
| **Code Quality** | 7 | Strong pytest on Phase 1 + analysis_pipeline + upload; flake8 CI; some legacy deprecation left in place |
| **UX** | 8 | Research OS chrome (D1–D9); Paper Workspace surfaces Phase 1; upload on Library; ⌘K; session/error UX |
| **Deployment** | 7 | Docker multi-stage + `entrypoint.sh` (Railway-ready); systemd + Procfile; migrations through **0021** |
| **Observability** | 7 | Prometheus + JSON logs; `/api/health/providers`; scholarly metrics; no Sentry/alerts/product analytics |
| **Testing** | 7 | Large pytest surface including Phase 1.1–1.7 + Phase 2 + scholarly; frontend Vitest not in CI |
| **Overall readiness** | **7 / 10** | Suitable for **trusted private deploy** with allowlist + HTTPS + secrets + migrations **0017–0021**; scholarly Discover/enrich live; **not** ready for open public multi-tenant production |

---

# 17. Missing Production Features

Checklist (items not done or incomplete):

### Authentication
- [x] Session absolute/idle TTL (PR4: defaults 12h absolute / 60m idle)  
- [ ] Step-up reauth for account deletion  
- [ ] Remove/disable DEV_AUTO_LOGIN in prod by default  
- [ ] Headless OAuth→JWT without browser (explicitly not built)

### Security
- [x] CSP / security headers / clickjacking defenses (PR4: baseline headers + HSTS; CSP Report-Only in prod)  
- [x] Magic-byte MIME validation (PR3: sniff + ZIP subtype checks; unified allowlist)  
- [x] Virus scanning (PR3: optional ClamAV behind `CLAMAV_ENABLED`, fail-closed when on)  
- [x] Authenticate or firewall `/metrics` (PR2: Bearer token or loopback-only; worker bind 127.0.0.1)  
- [x] Fix PromptBuilder project ownership (Phase A chat path + PR2 call-site / legacy hardening)  
- [x] Rate-limit + token quota on `/api/chat` (PR1: 60/min; token quota on analysis paths)  
- [x] Redis-backed limiter for multi-worker (PR1: `REDIS_URL` when reachable; fail-closed in prod if set but down)  
- [ ] Dependency vulnerability scanning in CI  

### Payments
- [ ] Billing / Stripe / plans — **Not Implemented**

### Analytics
- [ ] Product analytics (PostHog/Plausible/etc.)  

### Monitoring
- [ ] Sentry (or equivalent)  
- [ ] Alertmanager / paging  
- [ ] Admin ops UI  

### CI/CD
- [ ] Frontend build + Vitest in CI  
- [ ] Deploy pipeline  
- [ ] Coverage gates  
- [ ] Dependabot / pip-audit / npm audit  

### Testing
- [ ] Chat streaming E2E  
- [ ] OAuth E2E  
- [ ] Security regression for cross-user project access  

### Backups
- [ ] Documented automated DB/object backup runbooks in repo — **Unable to verify from current implementation** (no backup scripts found)

### SEO
- [ ] Per-route titles / OG tags (SPA auth-gated — limited value)

### Accessibility
- [x] Skip link + main landmark (D9)  
- [x] Icon control labels on shell chrome (ThemeToggle, nav, ⌘K) — deeper page audit still useful  
- [x] Paper workspace keyboard shortcuts with typing guard (D9)  
- [x] Command palette keyboard-first (D8)  

### Admin
- [ ] First-admin bootstrap UI; full admin dashboard  

### Legal
- [ ] Replace placeholder legal/support emails; finalize entity names  

### Performance
- [ ] pgvector / ANN; chat indexes; checkpointed imports  

### Scalability
- [ ] Shared rate-limit store; horizontal story beyond multi-worker SKIP LOCKED  

### Infrastructure
- [ ] Docker Compose / k8s manifests  
- [ ] Require secrets (fail closed if `FLASK_SECRET_KEY` unset in prod)  

### Frontend product (post–Design System)
- [x] Design System v2 D1–D9 (tokens → shell → pages → palette → a11y/session)  
- [x] Phase 1 Paper Workspace tabs wired to `/pipeline` + `/phases/*`  
- [ ] Resizable rails with persisted widths  
- [ ] Login/legal template brand sweep → Soro  
- [ ] Frontend Vitest in CI   

---

# 18. Technical Debt

| Item | Severity | Resolution |
|------|----------|------------|
| `server.py` monolith (~6.8k lines) | High | Extract blueprints/services gradually |
| Dual upload APIs + dual storage facades | High | Unify behind one storage + validation policy |
| Chat vs Prompt Engine divergence | High | Finish chat migration to PromptBuilder |
| Legacy confirm-upload / thread analysis paths | Medium | Route all analysis through AnalysisPipelineService + worker jobs |
| `extract_metadata` LLM job still in HANDLERS | Medium | Remove after queue drain; Phase 1.1 fills meta when available |
| Phase 1 UI not surfacing structured results | ~~Medium~~ | **Done** — Paper Workspace tabs + `features/pipeline` |
| `feature_flags` / `search_index` / unused `import_sessions` | Medium | Implement or drop |
| Worker LLM overview vs Phase 1.6 AssembledPrompt unused by chat | Medium | Decide product path for research AssembledPrompt |
| `PipelineVersion` not on live Base | Medium | Register or remove FK usage |
| Dual cost ledgers | Medium | Consolidate attribution |
| ORM vs migration type drift (`bytes_used`, jsonb vs Text) | Medium | Align types; prefer BigInteger |
| Missing FK indexes (messages, conversations, …) | Medium | Add migrations |
| Dead frontend: ProjectList, FilePreviewDialog | Low | Delete or wire (`CitationTable` now used on CitationsPage) |
| Branding: Personal AI / Soro / ResearchOS / Research Workspace | Medium | Pick one product name |
| Obsolete docs (`prompt-engine-architecture.md` “not implemented”, shipping-plan claiming no CI) | Medium | Mark superseded; point to this file |
| `get_current_user` / `jwt_optional` unused | Low | Use or remove |
| CI `SECRET_KEY` vs `FLASK_SECRET_KEY` | Low | Fix CI env |
| `semantic_search` Jinja `documents` unused | Low | Fix template or builder vars |
| Writing page raw fetch vs `writingApi` | Low | Use shared client |

---

# 19. Current Risks

### Security risks
- Open signup if `ALLOWED_EMAILS` blank + public deploy → API cost abuse  
- `DEV_AUTO_LOGIN` left on in production — **mitigated in PR1** (startup refuses)  
- Unauthenticated metrics endpoints — **mitigated in PR2** (token or loopback; worker bind localhost)  
- PromptBuilder cross-user project instruction leak — **mitigated** (Phase A ownership + PR2 call sites / legacy)  
- Spoofed file types (no magic bytes / AV) — **mitigated in PR3** (magic required; ClamAV optional)  
- Chat unbounded rate/token spend — **mitigated in PR1** (60/min chat limit + security logs; analysis token quota)  

### Scaling risks
- O(n) RAG cosine  
- In-memory rate limiter when `REDIS_URL` unset (PR1 prefers Redis when configured)  
- Full-document memory during import  
- Missing DB indexes on hot chat paths  

### Business risks
- No payments / tenancy packaging  
- Branding confusion  
- Legal copy incomplete  

### Data risks
- Schema dual-bootstrap drift  
- Incomplete cost attribution → blind spend  
- Account delete vs object storage consistency — verify operationally (code deletes DB + attempts file cleanup; **full R2 orphan guarantee unable to verify without runtime audit**)  

### AI risks
- Prompt injection via uploaded docs  
- Hallucinated citations despite instructions  
- DomainRegistry keyword detection may disagree with Phase 1.2 classification  
- Phase 1 JSON size growth on large papers (mitigated by truncation config)  
- Confirm-upload legacy threads can still bypass Phase 1 if used  

### Infrastructure risks
- Worker requires Postgres; SQLite “works” for API-only and misleads  
- Secret random fallback breaks multi-process sessions  
- No Sentry → silent production failures  

---

# 20. Roadmap

Based **only** on current implementation state (not aspirational design docs):

## Completed
- Session + Google OAuth + magic link + JWT bridge  
- Streaming chat with tools (web search, save citation)  
- Projects, memories, notes, citations, dashboard, settings  
- Upload → Postgres worker → extract/chunk/embed  
- **Phase 1.1–1.7** research engines (DU, classification, analysis context, medical, evidence grading, prompt assembly, knowledge graph) — code + tests  
- **Phase 2 integration** — `AnalysisPipelineService`, `analysis_pipeline_results` (0017), worker `phase1_analysis`, APIs `/analyze|/pipeline|/phases/*`, PromptBuilder `phase1_context`  
- **Phase 1 Paper Workspace UI** — Structure / Classification / Entities / Evidence / Graph + pipeline AI-state chrome  
- **Design System v2 D1–D9** — tokens, shell/Home, PipelineStatus, Paper Overview, Library, Chat demotion, Writing/Compare/Citations, ⌘K, ErrorBoundary + session modal + a11y  
- RAG (cosine) + JWT search/RAG endpoints  
- Prompt Engine (registry, builder, personas, analytics APIs) for RAG + paper analysis  
- Quotas (storage; partial tokens)  
- Prometheus metrics + JSON logging  
- Multi-paper compare/gaps, writing assistant, export  
- CI: flake8 + pytest  
- **Scholarly Step 1** — Crossref upload enrichment (merge + provenance), `provider_cache`, soft-fail before Phase 1  
- **Scholarly Step 2** — OpenAlex Discover + Add to Library (metadata stubs); Related via Semantic Scholar; citation format API; ops hardening (circuit/bulkhead/health)  
- **AI Core Stage 1 Paper Chat** — behind `PAPER_CHAT_PIPELINE_ENABLED`  
- **Docker / Railway** — multi-stage `Dockerfile`, Gunicorn `entrypoint.sh`  

## In Progress / inconsistent
- Dual auth/upload/storage stacks  
- Branding rename (Soro SPA vs Personal AI login/legal)  
- Prompt Engine adoption (**paper chat** Stage 1 flagged OFF by default)  
- Legacy confirm-upload / `extract_metadata` deprecation drain  
- Admin role (API yes, UI no)  
- Legal/support production copy  
- Scholarly UI polish (Related empty states, verified citation badge)  

## Next (highest leverage before public launch)
1. Verify production hardening PRs (§17) on every deploy (secrets, allowlist, headers, MIME, metrics, chat limits)  
2. Finish legacy path removal (confirm-upload threads → queue-only)  
3. Paper-scoped chat soak: `PAPER_CHAT_PIPELINE_ENABLED=shadow` → `true`  
4. Add chat/message indexes; decide pgvector timeline  
5. Run frontend tests in CI; fix legal placeholders + brand templates  
6. Apply migrations **0017–0021** on all deployed Postgres environments  
7. Delete or wire remaining dead FE (`ProjectList`, `FilePreviewDialog`)  
8. Scholarly Step 3/4 polish (Related UX, Crossref citation badge); PubMed deferred  

## Future
- ImportSession checkpointing  
- Feature flags service (or drop table)  
- Populate or remove `search_index`  
- Product analytics + Sentry  
- Admin UI  
- Resizable rails persistence  
- Graph DB persistence / query engine (Phase 1.7 non-goals)  
- Competitive track M13+ (compare→outline, claim blocks, writing studio) per `docs/soro-vs-jenni-roadmap.md`  
- Open-access PDF fetch for Discover (explicitly deferred)  

## Long-term
- Vector index / hybrid search  
- Deeper medical product UX on top of Phase 1.4–1.7  
- Payments / multi-tenant packaging (if business requires)  
- Possible Celery revisit only if Postgres worker proven insufficient (ADR currently says no)  

---

## Appendix A — Key file map

| Area | Path |
|------|------|
| App entry | `server.py` |
| Worker | `worker.py` (`import` → Crossref → `phase1_analysis` → `paper_analysis`) |
| Migrations | `migrations/0001`–`0021`, `run_migrations.py` |
| Auth | `auth/` |
| Upload JWT | `backend/upload/` |
| Search/RAG JWT | `backend/search/` |
| **Scholarly providers** | `backend/scholarly/` (Crossref, OpenAlex, Semantic Scholar) |
| Prompt Engine | `backend/ai/`, `backend/prompts/` |
| AI Core Stage 1 | `backend/ai_core/` (Paper Chat; feature-flagged) |
| **Phase 2 integration** | `backend/analysis_pipeline/` |
| Phase 1.1 | `backend/document_understanding/` |
| Phase 1.2 | `backend/classification/` (prefer `pass2`) |
| Phase 1.3 | `backend/analysis_context/` |
| Phase 1.4 | `backend/medical_understanding/` |
| Phase 1.5 | `backend/evidence_grading/` |
| Phase 1.6 | `backend/prompt_assembly/` |
| Phase 1.7 | `backend/knowledge_graph/` |
| Processing precursor | `backend/processing/` (adapter for older pass1) |
| Storage | `storage/`, `backend/storage/` |
| Imports | `imports/` |
| Quotas | `quotas/` |
| Observability | `observability/` |
| Frontend | `frontend/src/` (`features/pipeline`, `features/papers`, Design System shell) |
| Design System | `docs/DESIGN-SYSTEM-v2.md`, `docs/Interaction-Guidelines.md`, `docs/prototypes/d0.5/` |
| CI | `.github/workflows/ci.yml` |
| Deploy | `Dockerfile`, `entrypoint.sh`, `deploy/systemd/`, `Procfile` |
| Internal map (may drift) | `brain.md` |
| Design docs (partially superseded) | `docs/` |
| Architecture note (Phase 2) | `backend/analysis_pipeline/ARCHITECTURE.md` |
| UI audit (D9 closure in §20) | `UI-State.md` |

## Appendix B — Explicit “Unable to verify”

- Exact runtime coverage % of pytest  
- Whether production deploy currently uses R2 vs local  
- Operational backup/restore procedures outside the repo  
- Every individual endpoint’s complete OpenAPI-style request/response schema  
- Dependency CVE status at audit time (no scanner in CI)  
- Whether every §17 “PR1–PR4” hardening item is enabled on the live host  

---

*End of PROJECT_STATUS.md — audited 2026-07-26; refreshed for Phase 1+2, Design System D1–D9, scholarly Steps 1–2 (Crossref/OpenAlex/S2), AI Core Stage 1 Paper Chat, and Docker/Railway deploy (2026-07-27).*
