# 01 — Architecture Assessment

**Product:** Dhund (Research Operating System)  
**Codebase:** Flask modular monolith (`server.py` + `backend/*` factories) · React SPA · Postgres queue worker  
**Review method:** Code + migrations + ADRs + constitution — no assumptions without path evidence.

---

## Existing Strengths

### ✓ Factory / DI blueprint pattern (`backend/*`, `auth/`, `quotas/`)
Modules expose factories taking `SessionLocal`, model classes, and services — they never `import server`. This prevented a real double-import failure mode and is the correct modular-monolith seam. **Keep.**

### ✓ Evidence Layer as canonical knowledge (ADR-0003 / migration `0033`)
`evidence_objects`, `claim_reviews`, `writing_sentence_bindings`, `evidence_extraction_runs` + explain/search/retrieve/rank/consensus/conflict/reason/writing APIs. Differentiates Dhund from ChatGPT wrappers. **Keep and extend — never replace with a parallel “Claim root” store.**

### ✓ EvidenceQuery contract (ADR-0007 / `backend/evidence/query.py`)
Forbidden keys (`prompt`, `model`, `temperature`, `embeddings`, …) force evidence-first intelligence. **Keep frozen; version only via ADR.**

### ✓ Postgres job queue + transactional outbox (ADR-0001)
`upload_jobs` + `FOR UPDATE SKIP LOCKED` + `outbox_events` + Redis status cache as non-authoritative. Proven, operationally simple. **Keep — do not Celery-rewrite.**

### ✓ Import registry (`imports/`)
Ordered `Importer` list with mime/filename dispatch. Extensible without touching workers. **Keep.**

### ✓ Dual-aware but deliberate storage interfaces
`storage/` (session upload) and `backend/storage/` (JWT upload) are two consumers, not accidental copies of the same call site. Constitution already names this. **Keep interfaces; plan MERGE later, not a panic rewrite.**

### ✓ Auth stack
Google OAuth, magic link, JWT (`session_version` binding), closed-beta invites, ops admin. Session for SPA + Bearer for upload/pipeline. **Keep.**

### ✓ Library Bridge (Zotero / Mendeley)
OAuth, import, sync, collections, health, duplicates — real research trust surface. **Keep and surface in product (already started).**

### ✓ Phase 1 analysis pipeline
Document understanding → classification → context → medical → grading → prompt assembly → knowledge graph, persisted in `analysis_pipeline_results`. **Keep as document-prep spine feeding Evidence.**

### ✓ Writing Shell
`documents` / `document_versions` / `document_activity` + autosave idempotency. **Keep as manuscript SoT.**

### ✓ Grounded Writing + Reviewer modules
`backend/evidence/writing/*` (planner, section generator, citation binder, reviewer, export). Versions stamped (`writing_version`, `REVIEWER_VERSION`). **Keep; persist reviewer runs later.**

### ✓ Prompt Engine composition
`ModelRouter` (task→model) × `ModelRegistry` (provider dispatch) × `PromptRegistry` / `PromptBuilder` × `MemoryEngine` × `CostLedger`. **Keep composition; reduce dual call-path (Responses vs Chat Completions) over time.**

### ✓ Frontend feature slices + Research OS IA
`features/*` by product area; sidebar workflow-first (Library / Research / Writing). Marketing separated to Jinja. **Keep direction.**

### ✓ Constitution + ADRs
Binding principles and frozen contracts exist — rare and valuable. **Keep as change-control.**

---

## Weaknesses

| Weakness | Impact |
|----------|--------|
| **`server.py` ~9k-line god module** | Models, chat SSE, files, writing HTTP, marketing, OAuth, enqueue all colocated. High change risk; slow reviews; hard onboarding. |
| **Dual upload + dual storage + dual search** | Session `/api/files` vs JWT `/api/documents`; root `storage/` vs `backend/storage/`; `/api/search` vs `/api/documents/search` + `/api/rag`. Callers must know which stack; bugs diverge. |
| **Dual AI invoke paths** | OpenAI Responses streaming in `server.py` vs `ModelRegistry` Chat Completions. Cost/versioning incomplete for chat path (constitution §5 gap). |
| **Schema docs lag product** | `docs/database-design.md` / `api-contract.md` are upload-era. Evidence/RI/writing routes under-documented → accidental contract drift. |
| **Bootstrap chicken-and-egg** | Core tables via `create_all`; migrations FK to them. Documented gap — ops footgun. |
| **Multiple declarative Bases** | `server.Base` + private Bases for prompts/cost ledger. Soft Integer FKs — integrity is application-enforced. |
| **Roadmap vs code skew** | Phase 2.4/2.5 marked later in roadmap while `/api/evidence/writing` + reviewer already ship. Planning confusion. |
| **Frontend fetch inconsistency** | `apiClient` vs raw `fetch` (discover, related, some writing) → uneven 401 handling. |
| **Writing ↔ Evidence circular UI imports** | Product coupling without a shared “research writing” package boundary. |
| **Giant React pages** | `WritingPage`, `FilesPage`, `PaperOverviewPage` concentrate orchestration. |
| **`SearchIndex` largely unused** | Dead/near-dead surface; cosine-over-chunks is real path. |
| **Reviewer not durable** | In-response only — no audit table for “what did Reviewer say at export time?” |
| **Naming drift** | Folder `files` vs product “Library”; `documents` = writing docs not PDF files. |

---

## Missing Foundation

Capabilities still required for the long-term Research OS vision — **prefer extending EvidenceObject / RI stages**, not new parallel roots:

| Capability | Status | Recommended approach |
|------------|--------|----------------------|
| **EvidenceObject** | ✅ Implemented | Freeze; only ADR-extend fields |
| **Claim as first-class table** | ❌ By design | Keep as field/view of EvidenceObject (ADR-0003) |
| **Evidence Query + RI stages** | 🟡 APIs exist | Harden ranking/consensus; document as platform API |
| **Writing contracts** | 🟡 Versioned responses | Publish IDD section; stabilize section_type enum |
| **Reviewer contracts** | 🟡 In-process | Persist `reviewer_runs` (or document_activity payload); freeze response schema |
| **Research graph (project-level)** | 🟡 Phase 1.7 per-doc KG | Project-scoped graph view over EvidenceObjects — no second graph DB yet |
| **Ranking layer** | 🟡 `ranking_strategy` | Version strategies; metrics for strategy quality |
| **Export contracts** | 🟡 Markdown export | BibTeX/DOCX/journal packs as Phase 3 |
| **Trust page / trust API** | ❌ Marketing `/trust` deferred | Document what AI may/may not do |
| **Unified retrieval index** | 🟡 Chunk cosine | Optional pgvector later via ADR — not required to scale beta |
| **Billing / plans** | 🟡 User plan fields | JazzCash / SaaS-PK parallel track |
| **Teams / collaboration** | ❌ Explicitly deferred | Do not build now |

---

## Reuse Plan

| Module / surface | Decision | Rationale |
|------------------|----------|-----------|
| `EvidenceObject` + evidence APIs | **KEEP** | Canonical differentiator |
| EvidenceQuery normalize | **KEEP** | Frozen platform contract |
| `upload_jobs` / worker `HANDLERS` | **KEEP** | ADR-0001 |
| `imports/` registry | **KEEP** | Clean extension point |
| `auth/` factories | **KEEP** | Proven |
| Library bridge | **KEEP** / **EXTEND** | Sync quality + UX |
| Writing documents tables | **KEEP** | Manuscript SoT |
| `backend/evidence/writing/*` | **KEEP** / **EXTEND** | Add durable reviewer audit |
| Prompt Engine (`backend/ai/`) | **KEEP** / **REFACTOR** (call paths) | Unify invoke behind registry over time |
| Phase 1 analysis pipeline | **KEEP** | Feeds readiness + KG signals |
| Root `storage/` + `backend/storage/` | **MERGE** (Phase 2) | Single facade, two adapters |
| Session files API + JWT documents API | **MERGE** (Phase 2–3) | One upload façade; keep both routes temporarily |
| `/api/search` vs documents search/RAG | **MERGE** (Phase 2) | One retrieval service, two auth modes |
| `server.py` monolith handlers | **REFACTOR** | Extract blueprints without behavior change |
| `SearchIndex` table | **DEPRECATE** or populate | Decide via ADR; don’t leave zombie |
| Celery designs in old docs | **DEPRECATE** | Superseded by ADR-0001 |
| Chat as primary product | **DEPRECATE** (product), **KEEP** (tool) | UI vision: workflow before chat |
| Unused `writingStore` scaffold | **DEPRECATE** | Delete when touching writing |
| Marketing Jinja site | **KEEP** / **EXTEND** | Separate from SPA |
| Constitution / ADRs | **KEEP** | Change control |

**Deletion rule:** Never delete mature code without ADR + migration path + dual-run period.

---

## Architecture Scorecard

| Area | Score | Reasoning |
|------|-------|-----------|
| **Database Design** | **7/10** | Solid Evidence + upload + library schema; soft FKs and create_all/migrate bootstrap drag score down; docs stale. |
| **Domain Modeling** | **8/10** | EvidenceObject-centric model is excellent and ADR-backed; writing/bindings clear; Claim-as-root correctly avoided. |
| **API Design** | **6/10** | Evidence/RI APIs strong; dual upload/search/auth modes and undocumented surfaces hurt consistency. No `/api/v1`. |
| **Scalability** | **6/10** | Queue + SKIP LOCKED scales workers horizontally; in-process cosine search and monolith will cap large corpora. |
| **Maintainability** | **5/10** | Factory pattern helps; `server.py` size and dual stacks hurt. |
| **Modularity** | **7/10** | `backend/*` seams good; incomplete extraction of monolith routes. |
| **AI Architecture** | **7/10** | Prompt Engine + Evidence First + forbidden query keys; dual invoke paths and incomplete version stamps. |
| **Document Processing** | **8/10** | Importer registry + worker pipeline + Research Ready gating are mature. |
| **Search & Retrieval** | **6/10** | Chunk RAG works; Evidence retrieve/rank exist; no vector DB; SearchIndex unused. |
| **Frontend Architecture** | **7/10** | Feature slices + Research OS IA; giant pages, fetch/queryKey inconsistency. |
| **Developer Experience** | **6/10** | Good docs/ADRs; bootstrap gaps; large monolith; real Postgres needed for serious tests. |
| **Production Readiness** | **7/10** | Auth, quotas, ops, closed beta, worker heartbeats, rate limits present; observability/cost coverage uneven. |

**Overall:** **~6.8 / 10** — strong domain spine for a Research OS beta; operational debt concentrated in monolith + dual stacks, not in the evidence thesis.

---

## If joining today as Principal Engineer

### Keep exactly as-is
1. **EvidenceObject + EvidenceQuery + explain/bindings/review workflow** (ADR-0003/0005/0007).  
2. **Postgres worker + HANDLERS + outbox** (ADR-0001).  
3. **Factory/DI rule (no `import server`)**.  
4. **Library = `files` identity** (no new `papers` table).  
5. **Constitution Principle 11 — Evidence First.**

### Improve first (ordered)
1. **Document the live contracts** (this IDD + refresh `api-contract` / database-design for evidence/writing) — stops accidental breakage.  
2. **Extract writing + files HTTP from `server.py` into blueprints** with zero behavior change — reduces blast radius.  
3. **Unify upload façade** (one service; keep dual routes) — removes the #1 onboarding footgun.  
4. **Persist Reviewer/export audit** — trust narrative needs durable proof.  
5. **Frontend: route all fetches through `apiClient` + central `queryKeys`** — session reliability.

### Why this order
The product differentiator is already coded. Risk is **drift and dual paths**, not missing vision. Fix contracts and seams before building Knowledge Graph chrome or new AI capabilities.
