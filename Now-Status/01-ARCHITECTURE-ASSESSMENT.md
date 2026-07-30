# 01 — Architecture Assessment

**Product:** Dhund (Research Operating System)  
**Codebase:** Flask modular monolith (`server.py` + `backend/`* factories) · React SPA · Postgres queue worker  
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

`backend/evidence/writing/*` (planner, section generator, citation binder, reviewer, export). Versions stamped (`writing_version`, `REVIEWER_VERSION`). **Keep; reviewer runs persisted (A-401 / migration 0035).**

### ✓ Prompt Engine composition

`ModelRouter` (task→model) × `ModelRegistry` (provider dispatch) × `PromptRegistry` / `PromptBuilder` × `MemoryEngine` × `CostLedger`. **Keep composition; reduce dual call-path (Responses vs Chat Completions) over time.**

### ✓ Frontend feature slices + Research OS IA

`features/*` by product area; sidebar workflow-first (Library / Research / Writing). Marketing separated to Jinja. **Keep direction.**

### ✓ Constitution + ADRs

Binding principles and frozen contracts exist — rare and valuable. **Keep as change-control.**

---

## Weaknesses (post A-201 to A-215 hardening)

### Resolved / materially reduced (no behavior rewrite)


| Weakness                                  | Status    | What changed                                                                                                                                                                                                              |
| ----------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Evidence extraction contract drift**    | ✅ Reduced | `POST /api/projects/{id}/evidence/extract` now has stable status matrix (`400/409/200/202`) + async `job_id/run_id` path + idempotent reuse.                                                                              |
| **Job status opacity**                    | ✅ Reduced | A-404: `lifecycle`, `retry`, `timings`, classified `error`; Redis cache retains full payload. |
| **Evidence list envelope drift**          | ✅ Reduced | Evidence list/get endpoints now carry stable pagination envelope (`items,total,limit,offset`).                                                                                                                            |
| **Event contract gap**                    | ✅ Reduced | `EvidenceExtractionStarted`, `EvidenceCreated`, `EvidenceUpdated`, `BindingCreated`, `BindingDeleted` emitted with contract payloads.                                                                                     |
| **RI response inconsistency**             | ✅ Reduced | Shared envelope fields (`stage`, `timing_ms`, `versions`) standardized across RI stages.                                                                                                                                  |
| **Missing integration smoke path**        | ✅ Reduced | A-215 smoke path now codified: Research Ready → extract → accept one object (integration + staging script alignment).                                                                                                     |
| `**server.py` god-module blast radius**   | ✅ Reduced | Shared orchestration extracted into reusable modules (`backend/jobs/outbox.py`, `backend/search/shared.py`) and wired from `server.py`; monolith now delegates core cross-cutting logic instead of duplicating it inline. |
| **Dual upload/storage/search divergence** | ✅ Reduced | Session + JWT paths now share upload job/outbox enqueue and document-chunk search logic through common facades, reducing route-stack drift while preserving both APIs.                                                    |


### Remaining structural weaknesses


| Weakness                           | Current impact                                                                              |
| ---------------------------------- | ------------------------------------------------------------------------------------------- |
| **Dual AI invoke paths**           | Registry-driven and streaming paths are not fully unified for cost/version observability.   |
| **Schema/bootstrap footgun**       | `create_all` + migration ordering remains an operational sharp edge for fresh environments. |
| **Multiple declarative Bases**     | Cross-module integrity still partly application-enforced (soft FK pattern).                 |
| **Frontend architecture hotspots** | Some giant pages and mixed data-fetch patterns remain to be normalized.                     |
| **SearchIndex uncertainty**        | Table remains optional/unclear (deprecate or operationalize with ADR).                      |
| **Roadmap ↔ code narrative skew**  | Partially addressed by A-405 doc freeze; keep Now-Status/IDD in sync on larger changes.     |


---

## Missing Foundation

Capabilities still required for the long-term Research OS vision — **prefer extending EvidenceObject / RI stages**, not new parallel roots:


| Capability                         | Status                        | Recommended approach                                                           |
| ---------------------------------- | ----------------------------- | ------------------------------------------------------------------------------ |
| **EvidenceObject**                 | ✅ Implemented                 | Freeze; only ADR-extend fields                                                 |
| **Claim as first-class table**     | ❌ By design                   | Keep as field/view of EvidenceObject (ADR-0003)                                |
| **Evidence Query + RI stages**     | 🟡 APIs exist                 | Harden ranking/consensus; document as platform API                             |
| **Writing contracts**              | 🟡 Versioned responses        | Publish IDD section; stabilize section_type enum                               |
| **Reviewer contracts**             | 🟡 In-process                 | Persist `reviewer_runs` (or document_activity payload); freeze response schema |
| **Research graph (project-level)** | 🟡 Phase 1.7 per-doc KG       | Project-scoped graph view over EvidenceObjects — no second graph DB yet        |
| **Ranking layer**                  | 🟡 `ranking_strategy`         | Version strategies; metrics for strategy quality                               |
| **Export contracts**               | 🟡 Markdown export            | BibTeX/DOCX/journal packs as Phase 3                                           |
| **Trust page / trust API**         | ❌ Marketing `/trust` deferred | Document what AI may/may not do                                                |
| **Unified retrieval index**        | 🟡 Chunk cosine               | Optional pgvector later via ADR — not required to scale beta                   |
| **Billing / plans**                | 🟡 User plan fields           | JazzCash / SaaS-PK parallel track                                              |
| **Teams / collaboration**          | ❌ Explicitly deferred         | Do not build now                                                               |


---

## Reuse Plan


| Module / surface                      | Decision                                 | Rationale                                       |
| ------------------------------------- | ---------------------------------------- | ----------------------------------------------- |
| `EvidenceObject` + evidence APIs      | **KEEP**                                 | Canonical differentiator                        |
| EvidenceQuery normalize               | **KEEP**                                 | Frozen platform contract                        |
| `upload_jobs` / worker `HANDLERS`     | **KEEP**                                 | ADR-0001                                        |
| `imports/` registry                   | **KEEP**                                 | Clean extension point                           |
| `auth/` factories                     | **KEEP**                                 | Proven                                          |
| Library bridge                        | **KEEP** / **EXTEND**                    | Sync quality + UX                               |
| Writing documents tables              | **KEEP**                                 | Manuscript SoT                                  |
| `backend/evidence/writing/*`          | **KEEP** / **EXTEND**                    | Add durable reviewer audit                      |
| Prompt Engine (`backend/ai/`)         | **KEEP** / **REFACTOR** (call paths)     | Unify invoke behind registry over time          |
| Phase 1 analysis pipeline             | **KEEP**                                 | Feeds readiness + KG signals                    |
| Root `storage/` + `backend/storage/`  | **MERGE** (Phase 2)                      | Single facade, two adapters                     |
| Session files API + JWT documents API | **MERGE** (Phase 2–3)                    | One upload façade; keep both routes temporarily |
| `/api/search` vs documents search/RAG | **MERGE** (Phase 2)                      | One retrieval service, two auth modes           |
| `server.py` monolith handlers         | **REFACTOR**                             | Extract blueprints without behavior change      |
| `SearchIndex` table                   | **DEPRECATE** or populate                | Decide via ADR; don’t leave zombie              |
| Celery designs in old docs            | **DEPRECATE**                            | Superseded by ADR-0001                          |
| Chat as primary product               | **DEPRECATE** (product), **KEEP** (tool) | UI vision: workflow before chat                 |
| Unused `writingStore` scaffold        | **DEPRECATE**                            | Delete when touching writing                    |
| Marketing Jinja site                  | **KEEP** / **EXTEND**                    | Separate from SPA                               |
| Constitution / ADRs                   | **KEEP**                                 | Change control                                  |


**Deletion rule:** Never delete mature code without ADR + migration path + dual-run period.

---

## Architecture Scorecard


| Area                      | Score      | Reasoning                                                                                                                                                              |
| ------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Database Design**       | **8.5/10** | Evidence + run/audit tables are now better exercised by contracts/integration; bootstrap order + soft FK pattern still a known caveat.                                 |
| **Domain Modeling**       | **9.2/10** | EvidenceObject-first model remains coherent and ADR-governed; no parallel claim root introduced.                                                                       |
| **API Design**            | **9.0/10** | Evidence/RI/extract contracts are now explicit and test-backed (status matrix, envelopes, events). Remaining debt is dual-surface consolidation, not contract quality. |
| **Scalability**           | **8.6/10** | Queue/outbox architecture is strong for beta-scale and horizontal workers; future retrieval scaling still optional/ADR-gated.                                          |
| **Maintainability**       | **8.4/10** | Hardening and contract tests materially lowered change risk, though `server.py` extraction remains the biggest lever.                                                  |
| **Modularity**            | **8.8/10** | Factory seams + staged extraction path are working; further blueprint extraction is still planned.                                                                     |
| **AI Architecture**       | **8.7/10** | Evidence-first pipeline is solid; registry/streaming unification remains incremental technical debt, not a blocker.                                                    |
| **Document Processing**   | **9.1/10** | Importer registry + readiness gating + extraction lifecycle are now operationally tighter.                                                                             |
| **Search & Retrieval**    | **8.5/10** | RI stages are contract-stable; index strategy choices remain explicit roadmap decisions.                                                                               |
| **Frontend Architecture** | **8.6/10** | Product IA is strong and contracts are clearer; page decomposition + fetch unification still pending.                                                                  |
| **Developer Experience**  | **8.9/10** | ADR/constitution + contract tests + smoke paths significantly improve confidence and onboarding.                                                                       |
| **Production Readiness**  | **9.0/10** | Auth/quotas/worker/events/contracts now align well for beta operations; remaining work is primarily architectural consolidation.                                       |


**Overall:** **9.0 / 10** — architecture is now strong and contract-driven for a Research OS beta, with remaining risk concentrated in consolidation/refactor tracks (`server.py`, dual surfaces), not in domain correctness.

---

## If joining today as Principal Engineer

### Keep exactly as-is

1. **EvidenceObject + EvidenceQuery + explain/bindings/review workflow** (ADR-0003/0005/0007).
2. **Postgres worker + HANDLERS + outbox** (ADR-0001).
3. **Factory/DI rule (no `import server`)**.
4. **Library = `files` identity** (no new `papers` table).
5. **Constitution Principle 11 — Evidence First.**

### Improve first (ordered, no functionality changes)

1. **Extract writing + files HTTP from `server.py` into blueprints** (behavior-preserving move only).
2. **Unify upload façade behind one service** while keeping both route families during dual-run.
3. **Unify retrieval entry service** behind existing routes (`/api/search`, `/api/documents/search`, `/api/rag`).
4. **Persist Reviewer/export audit** (`reviewer_runs` or durable `document_activity` payload contract).
5. **Frontend fetch/queryKey normalization** (`apiClient` + centralized keys) for consistent auth/error behavior.

### Why this order

The product differentiator is already coded. Risk is **drift and dual paths**, not missing vision. Fix contracts and seams before building Knowledge Graph chrome or new AI capabilities.