# Week 2 Evidence Layer — Backend Technical Design

Status: Frozen for implementation  
Depends on: `docs/architecture/week2-evidence-layer-architecture.md`, ADR-0003  
Scope: Schema, extraction job, scoring v0, reviews, bindings, `POST /api/evidence/explain`

---

## 1) Goals

- Persist canonical `EvidenceObject` rows that are project-scoped, page-anchored, and provenance-complete.
- Extract candidates only from Research Ready files, reusing Phase 1.1 / 1.5 / 1.7 outputs.
- Support human accept/reject/edit without silent mutation of accepted objects.
- Bind Writing Shell sentences/blocks to evidence and assemble Inspector payloads via explain API.
- Never invent evidence ids or facts in API responses.

---

## 2) Schema (migration `0033_evidence_layer.sql`)

Constitution rules: soft Integer columns for cross-domain refs; real FKs only in raw SQL migrations; structured payloads as Text JSON.

### 2.1 `evidence_objects`

| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| user_id | INTEGER NOT NULL | Owner |
| project_id | INTEGER NOT NULL | Project scope |
| file_id | INTEGER NOT NULL | Library file (no papers table) |
| page | INTEGER | 1-based page when known |
| char_start | INTEGER | Optional span in page/section text |
| char_end | INTEGER | Optional |
| section | VARCHAR(200) | e.g. Results |
| quote | TEXT NOT NULL | Grounded excerpt |
| claim | TEXT NOT NULL | Normalized claim text |
| study_type | VARCHAR(80) | From Phase 1 / heuristics |
| study_quality | VARCHAR(40) | From Phase 1.5 |
| supports_json | TEXT | JSON array of related claim/evidence refs or strings |
| contradicts_json | TEXT | JSON array |
| limitations_json | TEXT | JSON array |
| confidence_band | VARCHAR(20) | `low` \| `moderate` \| `high` |
| status | VARCHAR(20) | `candidate` \| `accepted` \| `rejected` \| `superseded` |
| pipeline_version | VARCHAR(40) NOT NULL | e.g. `2.2.0` |
| created_by | VARCHAR(80) | `analysis-pipeline` \| `user` \| … |
| content_hash | VARCHAR(64) NOT NULL | Hash of grounded identity fields |
| supersedes_id | INTEGER | Prior object id when versioned |
| provenance_json | TEXT | JSON provenance blob |
| source_kg_node_id | VARCHAR(120) | Optional Phase 1.7 node id |
| created_at / updated_at | TIMESTAMPTZ | |

Indexes:

- `(user_id, project_id, updated_at DESC)`
- `(project_id, file_id, status)`
- `(project_id, content_hash, pipeline_version)` — idempotency lookups
- `(supersedes_id)` where not null

Unique (active identity): partial unique on `(project_id, file_id, content_hash, pipeline_version)` WHERE `status NOT IN ('superseded','rejected')` when Postgres supports it; SQLite tests may enforce in application layer.

### 2.2 `claim_reviews`

| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| evidence_object_id | INTEGER NOT NULL | |
| user_id | INTEGER NOT NULL | |
| project_id | INTEGER NOT NULL | Denormalized for authz queries |
| status | VARCHAR(20) | `accepted` \| `rejected` \| `edited` |
| reason | TEXT | Optional |
| edited_claim | TEXT | When edited |
| edited_quote | TEXT | When edited |
| reviewed_at | TIMESTAMPTZ | |

On accept: set `evidence_objects.status = 'accepted'` (and optionally sync edited fields via new superseding version if claim/quote changed — prefer create superseding object for claim/quote edits).

On reject: set `evidence_objects.status = 'rejected'`.

### 2.3 `writing_sentence_bindings`

| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| user_id | INTEGER NOT NULL | |
| project_id | INTEGER NOT NULL | |
| document_id | INTEGER NOT NULL | Writing Shell document |
| evidence_object_id | INTEGER NOT NULL | |
| block_id | VARCHAR(120) | Stable editor block / heading id |
| range_start | INTEGER | Markdown/UTF-16 offset in doc (optional) |
| range_end | INTEGER | |
| selected_text | TEXT | Display snippet |
| relation | VARCHAR(20) | `supports` \| `contradicts` \| `related` |
| created_by | VARCHAR(40) | `user` \| `system` |
| created_at | TIMESTAMPTZ | |

Indexes: `(document_id, block_id)`, `(evidence_object_id)`, `(user_id, project_id)`.

### 2.4 `evidence_extraction_runs` (idempotency / ops)

| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| user_id / project_id / file_id | INTEGER | |
| pipeline_version | VARCHAR(40) | |
| input_content_hash | VARCHAR(64) | Hash of Phase 1 artifacts + file text fingerprint |
| status | VARCHAR(20) | `queued` \| `running` \| `succeeded` \| `failed` \| `skipped` |
| objects_created | INTEGER | |
| error_json | TEXT | |
| job_id | INTEGER | UploadJob / queue id when present |
| created_at / finished_at | TIMESTAMPTZ | |

Unique: `(project_id, file_id, pipeline_version, input_content_hash)`.

---

## 3) Domain services (`backend/evidence/`)

Factory pattern — accept `SessionLocal`, model classes, `select`, permission helpers; no `import server`.

| Module | Responsibility |
|--------|----------------|
| `objects.py` | CRUD-ish loaders, serialize to API DTO, supersede helper |
| `scoring.py` | Map Phase 1.5 grades + study_type → `confidence_band` |
| `provenance.py` | Build provenance_json; content_hash |
| `extractor.py` | Research Ready gate → candidate EvidenceObjects |
| `reviews.py` | Accept / reject / edit with audit rows |
| `bindings.py` | Create/list/delete sentence bindings |
| `inspector.py` | Assemble explain response from stored data only |

Permission: mirror Writing Shell — user owns project (or project membership when that lands); evidence rows must match `user_id`/`project_id`; file must be readable by same tenant.

---

## 4) Extraction job (versioned, idempotent)

### Job type

Register `evidence_extract` (or `writing_evidence_extract`) in `worker.py` `HANDLERS`.

Payload:

```json
{
  "user_id": 1,
  "project_id": 2,
  "file_id": 10,
  "pipeline_version": "2.2.0",
  "force": false
}
```

### Algorithm

1. **Authz / gate:** file exists, owned, project-scoped association valid, **Research Ready** true. Else `skipped` with reason.
2. **Load Phase 1 artifacts** for `file_id` (document understanding spans, evidence grading, knowledge graph nodes/edges). If missing required artifacts → `failed` soft (retryable) or `skipped`.
3. **Compute `input_content_hash`** over artifact versions + file content fingerprint.
4. **Idempotency:** if extraction_run with same key succeeded and `force=false` → no-op return existing counts.
5. **Candidate build:** for each grounded claim/evidence_claim with page+quote:
   - Compose `confidence_band` via `scoring.py` (Phase 1.5 + study_type heuristics).
   - Fill supports/contradicts from KG SUPPORTS/CONTRADICTS edges (ids/labels only — no LLM invention).
   - Insert `evidence_objects` with `status=candidate`.
6. **Supersede path:** if prior objects exist for same logical keys under older pipeline or changed hash, mark prior non-rejected objects `superseded` and set `supersedes_id` on new rows — do not mutate accepted quote/claim in place.
7. **Partial failure:** log per-candidate errors; succeed run if ≥1 object or explicitly empty-but-valid (no claims found).
8. Emit activity/outbox event `evidence.extraction.completed` (optional Week 2).

### Candidate vs accepted

- Extraction **never** auto-accepts.
- Inspector explain may include candidates but labels them; “supported by” strength prefers `accepted`.

### Prompt-injection

Treat PDF/extracted text as untrusted. Extraction uses structured schema validation; discard fields that look like tool instructions; never execute paper text as commands.

---

## 5) Scoring v0

No parallel GRADE engine.

```text
inputs: Phase 1.5 study_quality / RoB / consistency + study_type
output: confidence_band ∈ {low, moderate, high}
```

Example heuristics (implementation detail; versioned in `pipeline_version`):

- RCT / systematic review + high quality + low RoB → `high`
- Observational + moderate quality → `moderate`
- Case report / high RoB / conflicting KG edges → `low` (or cap at moderate)
- Any missing grade → default `low` or `moderate` with explicit provenance note — never invent `high`

Numeric internals allowed only as private weights; API exposes ordinal band only.

---

## 6) API contract

All routes require auth session/JWT; CSRF per existing SPA rules; rate limits on extract + explain.

### 6.1 List / get objects

- `GET /api/projects/<project_id>/evidence?file_id=&status=`
- `GET /api/evidence/<evidence_id>`

### 6.2 Reviews

- `POST /api/evidence/<evidence_id>/reviews`  
  Body: `{ "status": "accepted|rejected|edited", "reason"?, "edited_claim"?, "edited_quote"? }`

### 6.3 Bindings

- `POST /api/documents/<document_id>/evidence-bindings`  
  Body: `{ "evidence_object_id", "block_id", "range_start"?, "range_end"?, "selected_text"?, "relation"? }`
- `GET /api/documents/<document_id>/evidence-bindings`
- `DELETE /api/evidence-bindings/<binding_id>`

### 6.4 Extraction enqueue

- `POST /api/projects/<project_id>/evidence/extract`  
  Body: `{ "file_id", "force"? }` → `{ "run_id", "job_id", "status" }`

### 6.5 Explain (Inspector primary)

`POST /api/evidence/explain`

Request:

```json
{
  "document_id": 55,
  "project_id": 2,
  "block_id": "blk_12",
  "range_start": 100,
  "range_end": 180,
  "selected_text": "optional"
}
```

Response:

```json
{
  "status": "ok",
  "sufficiency": "sufficient|weak|insufficient",
  "sentence": {
    "block_id": "blk_12",
    "range_start": 100,
    "range_end": 180,
    "text": "…"
  },
  "evidence": [
    {
      "id": 901,
      "status": "accepted",
      "confidence_band": "high",
      "claim": "…",
      "quote": "…",
      "page": 12,
      "section": "Results",
      "file_id": 10,
      "file_title": "…",
      "relation": "supports",
      "study_type": "RCT",
      "study_quality": "High",
      "supports": [],
      "contradicts": [],
      "limitations": [],
      "provenance": { "pipeline_version": "2.2.0" }
    }
  ],
  "chain": [
    {
      "step": "binding",
      "detail": "Matched block_id blk_12 → evidence 901"
    },
    {
      "step": "provenance",
      "detail": "Source Phase 1.5 grade High; KG SUPPORTS edge …"
    }
  ],
  "warnings": []
}
```

Rules:

- Every evidence id returned must exist, be owned, and be linked via binding **or** explicitly matched by server-side binder — never LLM-proposed ids.
- `chain` is assembled from stored provenance/bindings only.
- If no bindings / no accepted+candidate objects: `sufficiency=insufficient`, empty evidence, user-facing message — **no model prose padding**.
- Optional future: LLM explanation of *coded* chain steps only, after objects resolved — Week 2 may ship chain without LLM.

Error shapes: align with Writing Shell (`403` ownership, `404` missing, `422` validation).

---

## 7) Security checklist (backend)

- [ ] Ownership on every read/write
- [ ] Validate file_id Research Ready before extract
- [ ] Validate evidence_object_id on bind/review/explain
- [ ] No full quote in default info logs
- [ ] Rate-limit extract enqueue per project
- [ ] Account delete cascades or soft-purges evidence tables

---

## 8) Test plan (backend-focused)

- Unit: scoring bands, content_hash stability, supersede helper, explain assembly with fixtures
- Integration (Postgres): extract idempotency, cross-tenant IDOR negatives, review transitions, binding CRUD, explain authz
- Contract fixtures under `tests/fixtures/evidence/` for frontend mappers

---

## 9) Implementation order

1. Migration `0033` + SQLAlchemy models in `server.py` (wiring only)
2. `backend/evidence/` package + DI container
3. Scoring + provenance + objects serializers
4. Extractor + worker handler
5. Reviews + bindings routes
6. Explain / inspector assembly
7. Contract fixtures + Stage 4 tests
