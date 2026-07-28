# SYSTEM_ARCHITECTURE — Dhund

**Audience:** Engineers changing structure, wiring, or pipeline stages  
**Last updated:** 2026-07-28  
**Status index:** [PROJECT_STATUS.md](PROJECT_STATUS.md)

---

## 1) Architecture eras

```text
Era 1 — Analysis
  PDF → Document Understanding → Knowledge Graph
       (+ Phase 1.5 Evidence Grading)

Era 2 — Evidence Platform (frozen v0.2.0-rc1)
  Analysis → EvidenceObjects → Inspector → Explain API

Era 3 — Research Intelligence (Sprint 0–6 complete)
  EvidenceObjects
       → Retrieval → Ranking → Consensus → Conflict
       → Reasoning → Writing Intelligence
```

Rules:

- Eras compose; they do not rewrite each other.
- RI **never owns knowledge** — only computes over EvidenceObjects.
- Guided generation sits **last** (Writing Intelligence), after coded stages.

---

## 2) Architecture principles

1. Evidence First  
2. Research Intelligence computes over evidence  
3. Research Intelligence never owns knowledge  
4. Platform contracts are append-only  
5. All AI research features consume Evidence Query  

---

## 3) High-level stack

```text
Browser (React SPA)
    ↓ session cookie  /  Bearer JWT (selected routes)
Flask (server.py + blueprints)
    ↓
Services (quotas, storage, AI registries, search, AnalysisPipelineService, evidence/*)
    ↓
Postgres (or SQLite for local API-only) + Object storage (R2 / local / S3)
    ↓
worker.py (UploadJob queue via FOR UPDATE SKIP LOCKED)
    ↓  import → phase1_analysis (1.1–1.7) → paper_analysis
OpenAI / optional Anthropic / Gemini
```

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, Flask 3, SQLAlchemy 2 |
| Frontend | React 19, TypeScript, Vite, TanStack Query, Tailwind 4 |
| DB | PostgreSQL (prod/worker); SQLite for local API-only |
| Queue | Postgres `upload_jobs` — **not** Celery (ADR-0001) |
| Cache | Optional Redis (job status mirror) |
| Storage | Cloudflare R2 / local / S3 (two facades today — see debt) |
| AI | OpenAI Responses (chat) + ModelRegistry (multi-provider) |

---

## 4) Important flows

### Library → Analysis → Evidence

```text
Upload / Bridge import
  → worker: import → phase1_analysis (1.1–1.7)
  → paper_analysis (LLM overview + Phase 1 context)
  → evidence_extract (EvidenceObjects candidates)
  → review / accept → Inspector + Explain
```

### Research Intelligence (Evidence Query)

```text
EvidenceQuery
  → /api/evidence/search|retrieve   (Retrieval)
  → /api/evidence/rank              (Ranking)
  → /api/evidence/consensus         (Consensus)
  → /api/evidence/conflict          (Conflict)
  → /api/evidence/reason            (Reasoning — no LLM)
  → /api/evidence/writing           (Writing Intelligence — generation last, grounded_v0)
```

Each stage: one responsibility, one API, one test suite, one contract (ADR-0006).

### Chat (legacy path — still live)

```text
POST /api/chat → PromptBuilder / legacy system prompt
  → RAG cosine over chunks → OpenAI Responses stream
```

Chat is **not** the Evidence Query answer path. New research-facing AI must go through Evidence Query unless waived by ADR.

### Writing Studio Shell

```text
Project-scoped documents
  → autosave (optimistic lock + idempotency)
  → versions / restore
  → lifecycle draft → active → archived → deleted
```

Shell is `v0.1.0`. Evidence-backed writing uses RI Writing Intelligence, not freeform “write my intro.”

---

## 5) Package map (selected)

| Area | Path |
|------|------|
| Monolith + models | `server.py` |
| Worker | `worker.py` |
| Evidence Layer + RI stages | `backend/evidence/` |
| Writing shell services | `backend/writing/` |
| Analysis orchestration | `backend/analysis_pipeline/` |
| Phase 1 engines | processing / pipeline packages under repo |
| Prompt Engine | `backend/ai/` |
| Library Bridge | `backend/library/` |
| Auth | `auth/` |
| Storage (legacy) | `storage/` |
| Storage (upload JWT) | `backend/storage/` |
| Frontend features | `frontend/src/features/*` |

**Constraint:** never `import server` from modules `server.py` imports — use factory/DI wiring.

---

## 6) Evidence Query (universal ask)

Minimal fields: `intent` · `scope` · `filters` · `ranking_strategy` · `result_limit`  
Forbidden on the query: `prompt`, `model`, `temperature`, `embeddings`, `vector_index`.

Canonical: `docs/architecture/phase-2.3-evidence-query-contract.md` (ADR-0007).

---

## 7) Further reading

- `docs/00-constitution.md`  
- `docs/architecture/week2-evidence-layer-platform-contracts.md`  
- `docs/architecture/phase-2.3-research-intelligence-pipeline.md`  
- `docs/adr/0005-*`, `0006-*`, `0007-*`  
- [FEATURE_MATRIX.md](FEATURE_MATRIX.md) · [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md)
