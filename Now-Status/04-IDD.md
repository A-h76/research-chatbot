# 04 — Interface Definition Document (IDD)

**Title:** Dhund Research OS — Platform Interfaces v1.1 (evolutionary)  
**Status:** Draft for engineering alignment (Phase 0 complete)  
**Rule:** This IDD **extends** existing ADRs and live APIs. It does **not** replace ADR-0003/0005/0007 or invent parallel roots.

**Related:** ADR-0001 … 0007 · `docs/00-constitution.md` · `backend/evidence/query.py` · migration `0033`

---

## 1. Purpose

Define the stable contracts between:

1. Application UI (SPA)  
2. HTTP API  
3. Domain services (Evidence, Writing, Library, Analysis)  
4. Persistence (Postgres + object storage)  
5. Async workers  

…so Dhund can scale as a Research OS **without rewriting** mature modules.

---

## 2. Architectural invariants (unchanged)

| # | Invariant | Source |
|---|-----------|--------|
| I1 | `EvidenceObject` is the sole canonical research knowledge unit | ADR-0003 |
| I2 | Library paper identity = `files` row (no `papers` table) | ADR-0003 |
| I3 | EvidenceQuery must not carry prompt/model/temperature/embeddings | ADR-0007 |
| I4 | Async work via Postgres `upload_jobs` + outbox | ADR-0001 |
| I5 | Packages imported by `server.py` must not `import server` | Constitution / CLAUDE.md |
| I6 | Structured blobs as Text JSON columns (app-serialized) | Prompt-engine constraints |
| I7 | Cross-private-Base FKs are Integer soft FKs; real FKs in SQL migrations | Same |
| I8 | Evidence First — generation consumes accepted evidence | Constitution P11 |

---

## 3. Bounded contexts (reuse existing names)

```text
Identity & Access     → auth/, security/ops, users
Projects              → projects, project_questions, memories(research)
Library               → files, library_*, uploads, imports
Document Intelligence → analysis_pipeline, paper_analyses, chunks
Evidence Platform     → evidence_*, claim_reviews, bindings, extraction_runs
Writing Studio        → documents, document_versions, document_activity
Research Intelligence → retrieve/rank/consensus/conflict/reason/writing services
Prompt Engine         → prompt_versions, personas, model_router/registry, cost ledger
Delivery              → worker HANDLERS, outbox_events
```

**Do not** introduce a sixth “Evidence Engine” deployable until an ADR splits the modular monolith.

---

## 4. Core domain contracts

### 4.1 EvidenceObject (KEEP — freeze)

**Storage:** `evidence_objects`  
**Lifecycle:** `candidate` → `accepted` | `rejected` | `superseded` (append-only via `supersedes_id`)

**Logical fields (already shipped; names must stay stable):**

| Field group | Meaning |
|-------------|---------|
| Identity | `id`, `user_id`, `project_id`, `file_id`, `pipeline_version`, `content_hash` |
| Content | quote / claim / finding text fields as implemented |
| Anchors | page / location provenance |
| Quality | `confidence_band` ∈ {low, moderate, high} |
| Relations | supports / contradicts / limitations (JSON text) |
| Status | candidate \| accepted \| rejected \| superseded |
| Provenance | extraction run, model/pipeline stamps where present |

**API:**

| Method | Path | Contract |
|--------|------|----------|
| GET | `/api/projects/<project_id>/evidence` | List (filter by status) |
| GET | `/api/evidence/<id>` | Get |
| POST | `/api/evidence/<id>/reviews` | Accept / reject / edit→supersede |
| POST | `/api/projects/<project_id>/evidence/extract` | Enqueue extraction |
| POST | `/api/evidence/explain` | **Frozen** Inspector explain |
| POST | `/api/evidence/search` | Query over objects |

**Extension rule:** New columns require migration + ADR if they change Inspector or Writer semantics.

---

### 4.2 EvidenceQuery (KEEP — freeze)

Normalized by `normalize_evidence_query` (`backend/evidence/query.py`).

```text
EvidenceQuery {
  intent: support_sentence | answer_question | review_coverage | compare_topic | list_project
  scope: { user_id(server), project_id, file_ids?, document_id? }
  filters: { status[], confidence_bands[] }
  anchors: { … }
  section_type?: Writing section enum
  ranking_strategy: string  // default_v0
  result_limit: 1..100
}
```

**Forbidden keys:** `prompt`, `model`, `temperature`, `embeddings`, `vector_index`, `api_key`, `provider`.

**Stage pipeline (KEEP endpoints):**

```text
EvidenceQuery
  → POST /api/evidence/retrieve   (or /search)
  → POST /api/evidence/rank
  → POST /api/evidence/consensus
  → POST /api/evidence/conflict
  → POST /api/evidence/reason
  → POST /api/evidence/writing      // grounded draft
```

Stages **compute over EvidenceObjects**; they do not own alternate knowledge stores (ADR-0006).

---

### 4.3 Writing Studio (KEEP tables; EXTEND contracts)

**Storage:** `documents`, `document_versions`, `document_activity`  
**Bindings:** `writing_sentence_bindings`

| Concern | Interface |
|---------|-----------|
| Document CRUD / autosave / versions | `/api/writing/documents*` (existing) |
| Grounded generation | `POST /api/evidence/writing` → response includes `writing_version`, citations, metrics, review, disclaimer |
| Bindings | `POST/GET /api/documents/<id>/evidence-bindings`, `DELETE /api/evidence-bindings/<id>` |
| Export | Existing markdown/export helpers — version stamp required |

**Writing response contract (stabilize as v1):**

```text
GroundedWritingResult {
  status: ok | blocked
  mode / section_type
  paragraph | sections
  citations[]          // must resolve to evidence ids
  metrics { grounding_pct, reviewer_pass_rate, … }
  review { issues[], reviewer_version }
  warnings[]
  disclaimer
  writing_version
  blocked_reason?      // when insufficient evidence
}
```

**Section types (append-only enum):**  
`support_sentence`, `introduction`, `literature_review`, `discussion`, `clinical_summary`, `research_gap`, `executive_summary`

---

### 4.4 Reviewer (EXTEND — persist)

**Current:** `REVIEWER_VERSION` in `backend/evidence/writing/reviewer.py` — in-process.  

**IDD addition (Phase 1–2, non-breaking):**

```text
ReviewerResult {
  reviewer_version: string
  issues: [{ code, severity, message, section_id?, evidence_ids? }]
  metrics: { grounding_pct, citation_coverage, … }
}
```

**Persistence target (Phase 2):** store snapshot on `document_activity` or new `reviewer_runs` table referencing `document_id` + `writing_version`. Do **not** invent a second review semantics beside `claim_reviews` (those are **evidence** reviews).

Naming:

| Term | Meaning |
|------|---------|
| Evidence review | Human accept/reject of EvidenceObject (`claim_reviews`) |
| Research Reviewer | Automated draft critique (`ReviewerResult`) |

---

### 4.5 Library & Upload (KEEP; façade later)

| Surface | Status |
|---------|--------|
| `UserFile` / `files` | Paper identity |
| Research Ready gate | Required before extract |
| UploadJob.job_type | `import`, `phase1_analysis`, `paper_analysis`, `evidence_extract`, … |
| Library bridge | `/api/library/*` |

**Façade (Phase 2):** `LibraryUploadService` used by both session and JWT routes — same jobs, same storage interface.

---

### 4.6 Projects (KEEP)

```text
Project { id, user_id, name, emoji?, instructions? }
ProjectQuestion
ResearchMemory (memories kind/source/payload)
```

Hub + research presets remain the project “assistant” entry — Evidence-scoped where possible.

---

### 4.7 Auth (KEEP)

| Mode | Use |
|------|-----|
| Session cookie | SPA + most `/api/*` |
| Bearer JWT (`session_version`) | Upload, bulk, pipeline, RAG |
| Google / magic link / password ops | Identity |
| Closed beta invites | Gate |

No new auth protocol for Research OS features.

---

### 4.8 Prompt Engine (KEEP composition)

```text
task_name → ModelRouter → model_id → ModelRegistry.call / embed
PromptRegistry + PromptBuilder assemble prompts
PromptExecution / CostLedger for audit (extend coverage to chat SSE over time)
```

**AI Core boundaries (ADR-0002):** no provider SDK outside executor/registry; version stamps on durable AI artifacts.

---

## 5. Event / job contracts (KEEP)

| job_type | Input (logical) | Output |
|----------|-----------------|--------|
| `import` | file_id | text + chunks/embeddings; enqueue phase1 |
| `phase1_analysis` | file_id | `analysis_pipeline_results` |
| `paper_analysis` | file_id | `paper_analyses` |
| `evidence_extract` | project_id, file_id | evidence_objects + extraction_runs |

Outbox: `OutboxEvent(aggregate_type="upload_job", …)` dispatched when job terminal.

**Extension:** new job types only via `HANDLERS` dict + migration if schema needed.

---

## 6. Frontend contracts (KEEP patterns; tighten)

| Pattern | IDD rule |
|---------|----------|
| Feature folders | Keep `features/{domain}` |
| Server state | TanStack Query + `queryKeys` (extend keys for writing/evidence) |
| HTTP | Prefer `apiClient` / JWT helper; deprecate raw `fetch` for authenticated APIs |
| Marketing | Jinja only — SPA must not own `/product`, `/research` guides |
| Auth gate | `/api/me` → `/login` |

---

## 7. Explicit non-interfaces (do not add)

- Claim table as root aggregate  
- Parallel papers table  
- EvidenceQuery model/prompt fields  
- Celery broker as required runtime  
- Chat as primary research knowledge store  

---

## 8. Versioning policy

| Artifact | Version field | Bump rule |
|----------|---------------|-----------|
| Evidence pipeline | `pipeline_version` on objects/runs | Breaking extract semantics |
| Writing | `writing_version` | Breaking draft shape |
| Reviewer | `reviewer_version` | Breaking issue codes/metrics |
| EvidenceQuery | ADR + code constants | New intent/section via append-only enums |

---

## 9. Compatibility with existing clients

Phase 1 of migration **must not** break:

- Current SPA evidence/writing flows  
- Zotero/Mendeley OAuth callbacks  
- Worker job_type strings already in flight  
- Frozen `POST /api/evidence/explain` body/response  

Additive fields are preferred; removals require ADR + dual-read window.
