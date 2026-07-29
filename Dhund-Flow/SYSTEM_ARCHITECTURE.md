# SYSTEM_ARCHITECTURE — Dhund

**Audience:** Engineers changing structure, wiring, or pipeline stages  
**Last updated:** 2026-07-29  
**Status index:** [PROJECT_STATUS.md](PROJECT_STATUS.md)

---

## 1) Dependency direction

Upper layers depend on lower layers. They do **not** reach around them.

```text
Applications
    │
    ▼
Research Intelligence
    │
    ▼
Evidence Platform
    │
    ▼
Analysis Pipeline
    │
    ▼
Document Import
```

| Layer | Role |
|-------|------|
| Applications | Writing · Reviewer · Compare · Assistant · Library UI |
| Research Intelligence | Retrieval → Ranking → Consensus → Conflict → Reasoning → Writing Intelligence |
| Evidence Platform | EvidenceObjects · Explain · Bindings · Reviews · Provenance (frozen) |
| Analysis Pipeline | Phase 1.1–1.7 · grading · graph projections |
| Document Import | Upload · Bridge · worker import · text extraction |

---

## 2) Architecture eras

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

## 3) Architecture principles

1. Evidence First  
2. Research Intelligence computes over evidence  
3. Research Intelligence never owns knowledge  
4. Platform contracts are append-only  
5. All AI research features consume Evidence Query  
6. **No layer may bypass the one directly beneath it without an approved ADR.**  

Principle 6 formalises §1: Applications must not call Evidence / Analysis / Import directly when RI is the correct entry; RI must not invent knowledge outside Evidence Platform; etc.

---

## 4) Model Router (capability, not provider)

Architecture depends on **capabilities**, not vendors. Model routing lives in `backend/ai/` — it is **not** a sixth product layer above Import/Evidence; it is the abstraction between capability calls and providers.

```text
Research Intelligence (and other callers)
        │
        ▼
   Model Router          ← task / capability → model string
        │
        ▼
  Model Registry         ← provider dispatch
        │
 ┌──────┼────────┐
 ▼      ▼        ▼
OpenAI Claude Gemini
```

Prefer capability-shaped calls:

| Capability shape | Not |
|------------------|-----|
| `reason()` · `retrieve()` · `write()` · `review()` | `call_openai()` · `call_gemini()` |

Notes:

- `ModelRouter.get_model_for_task(task_name)` selects the model; `ModelRegistry` dispatches to the provider.  
- Many RI stages (**Retrieval, Ranking, Consensus, Conflict, Reasoning**) are **deterministic / coded** — they do not need a model. Generation (Writing Intelligence, and future narration) is where routing matters.  
- Legacy chat still calling OpenAI Responses directly is known debt — new research-facing AI should go through Evidence Query + Model Router, not a private provider client.

---

## 5) High-level stack

```text
Browser (React SPA)
    ↓ session cookie  /  Bearer JWT (selected routes)
Flask (server.py + blueprints)
    ↓
Services (quotas, storage, search, AnalysisPipelineService, evidence/*)
    ↓
Model Router → Model Registry   (when a capability needs an LLM)
    ↓
 ┌──────┼────────┐
 ▼      ▼        ▼
OpenAI Claude Gemini
    ↓
Postgres (or SQLite for local API-only) + Object storage (R2 / local / S3)
    ↓
worker.py (UploadJob queue via FOR UPDATE SKIP LOCKED)
    ↓  import → phase1_analysis (1.1–1.7) → paper_analysis
```

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, Flask 3, SQLAlchemy 2 |
| Frontend | React 19, TypeScript, Vite, TanStack Query, Tailwind 4 |
| DB | PostgreSQL (prod/worker); SQLite for local API-only |
| Queue | Postgres `upload_jobs` — **not** Celery (ADR-0001) |
| Cache | Optional Redis (job status mirror) |
| Storage | Cloudflare R2 / local / S3 (two facades today — see debt) |
| AI routing | `backend/ai/model_router.py` + `model_registry.py` |

---

## 6) Important flows

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

## 7) Package map (selected)

| Area | Path |
|------|------|
| Monolith + models | `server.py` |
| Worker | `worker.py` |
| Evidence Layer + RI stages | `backend/evidence/` |
| Writing shell services | `backend/writing/` |
| Analysis orchestration | `backend/analysis_pipeline/` |
| Phase 1 engines | processing / pipeline packages under repo |
| Prompt Engine + Model Router / Registry | `backend/ai/` |
| Library Bridge | `backend/library/` |
| Auth | `auth/` |
| Storage (legacy) | `storage/` |
| Storage (upload JWT) | `backend/storage/` |
| Frontend features | `frontend/src/features/*` |

**Constraint:** never `import server` from modules `server.py` imports — use factory/DI wiring.

---

## 8) Evidence Query (universal ask)

Minimal fields: `intent` · `scope` · `filters` · `ranking_strategy` · `result_limit`  
Forbidden on the query: `prompt`, `model`, `temperature`, `embeddings`, `vector_index`.

Canonical: `docs/architecture/phase-2.3-evidence-query-contract.md` (ADR-0007).

---

## 9) Future evolution

New capabilities (agent workflows, automation, collaborative review, publication pipelines) fit **above** Research Intelligence or **consume** it — they do not reach into Evidence / Analysis / Import without an ADR (principle 6).

```text
Applications · Agents · Publication · Collaboration
      │
      ▼
Research Intelligence
      │
      ▼
Evidence Platform → … → Document Import
```

---

## 10) Further reading

- `docs/00-constitution.md`  
- `docs/architecture/week2-evidence-layer-platform-contracts.md`  
- `docs/architecture/phase-2.3-research-intelligence-pipeline.md`  
- `docs/adr/0005-*`, `0006-*`, `0007-*`  
- [FEATURE_MATRIX.md](FEATURE_MATRIX.md) · [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md)
