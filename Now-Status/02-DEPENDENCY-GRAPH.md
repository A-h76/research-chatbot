# 02 — Dependency Graph

## Logical layers (target & mostly current)

```text
┌─────────────────────────────────────────────────────────────┐
│  Marketing (Jinja)          Application (React SPA)         │
│  / /product /how-it-works   /home /library /writing /…      │
│  /research /early-access    RootLayout → /api/me gate       │
│  /login (auth only)                                         │
└───────────────────────────────┬─────────────────────────────┘
                                │ HTTP (cookie session / JWT)
                                ▼
┌─────────────────────────────────────────────────────────────┐
│  API layer                                                  │
│  Blueprints: documents, upload/bulk, search/rag, library,   │
│  projects, analysis_pipeline, evidence, prompts, ops,       │
│  magic_link                                                 │
│  Monolith (server.py): files, chat SSE, writing CRUD,       │
│  notes, citations, memories, me, analysis compare/gaps, …   │
└───────────────────────────────┬─────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│  Services                                                   │
│  AnalysisPipelineService · LibraryImport/Sync               │
│  Evidence extract/retrieve/rank/consensus/conflict/reason   │
│  Writing intelligence (planner→generator→binder→reviewer)   │
│  PromptBuilder · MemoryEngine · QuotaService                │
│  AIGateway / ModelRouter / ModelRegistry                   │
└───────────────────────────────┬─────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│  Repositories / persistence access                          │
│  SQLAlchemy SessionLocal + model classes (mostly inline)    │
│  Soft-FK Integers across private Bases                      │
│  storage/ + backend/storage/ object IO                      │
│  imports/ extraction                                        │
└───────────────────────────────┬─────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│  Database (Postgres) + Object storage (Local/R2/S3)         │
│  users · projects · files · chunks · evidence_* · documents │
│  upload_jobs · outbox_events · library_* · prompt_*         │
└─────────────────────────────────────────────────────────────┘

        │
        │  peer process (intentional import server)
        ▼
┌─────────────────────────────────────────────────────────────┐
│  worker.py                                                  │
│  HANDLERS: import → phase1_analysis → paper_analysis        │
│            evidence_extract                                 │
│  Redis: job:{id}:status cache only                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Frontend → API dependency (product)

```text
AppShell / features
  ├── projects ──────────► /api/projects/*
  ├── files (Library) ───► /api/files* + /api/documents/upload + /api/library/*
  ├── papers ────────────► files + pipeline + analysis + evidence + chat
  ├── writing ───────────► /api/writing/* + /api/evidence/writing + bindings
  ├── evidence ──────────► /api/evidence/* + project evidence extract
  ├── chat ──────────────► /api/chat (SSE) + /api/conversations*
  ├── search ────────────► /api/search + /api/discover + JWT RAG
  ├── analysis ──────────► /api/analysis/compare|gaps
  └── profile/settings ──► /api/me + settings APIs
```

---

## Circular / hazardous dependencies

| Risk | Type | Notes |
|------|------|-------|
| Package → `import server` | **Forbidden** | Would re-exec monolith under name `server`. Factories avoid this. |
| `worker.py` → `import server` | **Allowed** | Separate process. |
| Tests → `import server` | **Allowed** | Load app as module. |
| Writing UI ↔ Evidence UI | **Product cycle** | Cross-imports; extract shared `research-writing` UI kit later. |
| `server.Base` ↔ private Bases | **Soft cycle risk** | Soft FKs; migrations define real FKs carefully. |
| Marketing `/research*` vs SPA `/research/compare` | **Route collision** | Explicit Flask routes win; SPA catch-all aborts `research/`. |

**No classical Python import cycle** was found in production packages that `server.py` imports. The main hazard remains **accidental `import server`** in new modules.

---

## Dual-stack edges (consolidation candidates)

```text
Upload:   /api/files  ──┐
          /api/documents/upload ──┼──► UserFile + UploadJob
          /api/uploads/* ─────────┘

Storage:  storage/ (Local/R2) ──┐
          backend/storage/ ─────┴──► bytes on disk/R2

Search:   POST /api/search (session) ──┐
          GET  /api/documents/search ──┼──► Chunk embeddings
          POST /api/rag ───────────────┘

AI call:  Responses API (chat SSE) ──┐
          ModelRegistry.call ────────┴──► tokens / cost (uneven ledger)
```

---

## Blueprint registration order (coupling note)

Deferred registration in `server.py` exists because `model_router` / `PromptExecution` appear mid-file. **Do not reorder blindly.** When extracting blueprints, pass dependencies explicitly at wire-up time (already the pattern).
