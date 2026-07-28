# Evidence Layer — Frozen Platform Contracts (v0.2.0)

Status: **Frozen**  
Effective: Evidence Layer RC (`v0.2.0-rc1`)  
Governing ADRs: ADR-0003 (canonical EvidenceObject), ADR-0005 (this freeze)  
Related: ADD-0005 / ADR-0004 (Research Intelligence must consume, not bypass)

Breaking changes require a new ADR. Additive fields require fixture + mapper updates in the same change set.

---

## 1) EvidenceObject

Canonical unit of research knowledge. Claims/findings/results are fields or views — not competing roots.

### Required public fields

| Field | Contract |
|-------|----------|
| `id` | Stable integer id |
| `user_id` / `project_id` / `file_id` | Tenant + Library paper identity (no `papers` table) |
| `page` | Page anchor when known; never invent |
| `char_start` / `char_end` | Optional span |
| `section` | Optional |
| `quote` | Non-empty grounded excerpt |
| `claim` | Normalized claim text |
| `study_type` / `study_quality` | Strings from Phase 1 / heuristics |
| `supports` / `contradicts` / `limitations` | Arrays |
| `confidence_band` | `low` \| `moderate` \| `high` only |
| `status` | `candidate` \| `accepted` \| `rejected` \| `superseded` |
| `pipeline_version` | Extraction method version |
| `content_hash` | Grounded identity hash |
| `supersedes_id` | Append-only lineage |
| `provenance` | Object (see §5) |
| `source_kg_node_id` | Optional Phase 1.7 link |

### Hard semantics

- Always page-anchored when extracted (`file_id` + `quote`; prefer `page`).
- Auto-extract creates **`candidate` only**.
- Accepted objects are never silently mutated; edits create a superseding row.
- Reference `file_id`, never a parallel paper identity store.

Fixture: `tests/fixtures/evidence/` + serializers in `backend/evidence/objects.py`.

---

## 2) Explain API

`POST /api/evidence/explain`

Frozen request (minimum):

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

Frozen response envelope:

```json
{
  "status": "ok",
  "sufficiency": "sufficient|weak|insufficient",
  "sentence": { "block_id": "", "range_start": 0, "range_end": 0, "text": "" },
  "evidence": [ /* EvidenceObject projections + relation */ ],
  "chain": [ { "step": "", "detail": "" } ],
  "warnings": []
}
```

### Invariants

- Every returned evidence id exists and is owned.
- `chain` assembled from stored bindings/provenance only — no invented facts.
- `insufficient` ⇒ empty `evidence`, no model padding.
- Client must not re-rank `evidence[]`.

Canonical detail: `docs/architecture/week2-evidence-explain-api.md`.  
Fixtures: `explain_sufficient.json`, `explain_insufficient.json`, `explain_candidates_only.json`.

---

## 3) Sentence bindings

Table / resource: `writing_sentence_bindings`

| Field | Contract |
|-------|----------|
| `document_id` | Writing Shell document |
| `evidence_object_id` | Owned EvidenceObject in same project |
| `block_id` | Preferred stable anchor |
| `range_start` / `range_end` | Optional |
| `selected_text` | Display hint — not sole authz identity |
| `relation` | `supports` \| `contradicts` \| `related` |

Routes:

- `POST/GET /api/documents/<id>/evidence-bindings`
- `DELETE /api/evidence-bindings/<id>`

---

## 4) Review workflow

Table: `claim_reviews`

| Review status | Effect on EvidenceObject |
|---------------|--------------------------|
| `accepted` | `status=accepted` |
| `rejected` | `status=rejected` |
| `edited` | Prior → `superseded`; new row with edited claim/quote, typically `accepted` |

Route: `POST /api/evidence/<id>/reviews`

Inspector prefers **accepted** for “supported by” / `sufficient`.

---

## 5) Provenance model

`provenance` / `provenance_json` MUST be able to carry:

```json
{
  "pipeline_version": "2.2.0",
  "document_understanding": "…",
  "evidence_grading": "…",
  "knowledge_graph": "…",
  "extraction_prompt_version": "…"
}
```

Plus object-level `pipeline_version`, `content_hash`, `created_by`, `supersedes_id`.

Extraction identity: `(project_id, file_id, content_hash, pipeline_version)` for active rows; runs keyed by input content hash (see extraction job spec).

---

## 6) Confidence bands

Public API exposes **only**:

```text
low | moderate | high
```

Composed from Phase 1.5 + study-type heuristics (+ contradiction flags).  
Uncalibrated floats (e.g. `0.92`) are not part of the public contract.

---

## Versioning policy

| Change type | Allowed how |
|-------------|-------------|
| Additive optional field | Same major; update fixtures + mappers |
| Rename / remove / semantic break | New ADR + explicit migration path |
| New RI APIs (`/search`, `/retrieve`) | Additive; must return frozen EvidenceObject refs |

Module: `backend/evidence/`. Umbrella name: **Evidence Layer**.
