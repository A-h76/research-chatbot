# A-402 — API Contracts Freeze (v1)

**Status:** Frozen (A-402 + A-403 additives)  
**contracts_version:** `1.2.0`  
**Effective:** 2026-07-30  
**Scope:** Evidence Platform, Research Intelligence, bindings, extract, reviewer-runs  
**Parent IDD:** [IDD-0003](../idd/IDD-0003-API-Contracts.md)  
**Companion docs:** [evidence-contract.md](./evidence-contract.md) · [error-contract.md](./error-contract.md) · [versioning-policy.md](./versioning-policy.md) · [frontend-compatibility.md](./frontend-compatibility.md)

> **Compatibility promise:** Developer B may implement against this document. Breaking changes require ADR + contracts bump (see versioning-policy).

---

## 1. Global conventions (frozen)

| Rule | Value |
|------|--------|
| JSON | snake_case; UTF-8; ISO-8601 timestamps (or `null`) |
| IDs | integers |
| Auth (these routes) | Session cookie (`login_required`) |
| Unauthenticated | `401` or redirect `302` (SPA should treat both as unauth) |
| Validation (Evidence/RI) | **`422`** + `{ "error": "validation_error", "detail": "…" }` |
| Domain not found / ownership | usually **`404`** + `{ "error": "not_found" \| …, "detail": "…" }` |
| Rate limit | **`429`** (Limiter; body may not always match ErrorCode — see error-contract) |
| Response envelope | **Flat JSON** (no `{ data, meta, errors }` wrapper) |
| RI list key | **`objects`** (not `items`) |
| CRUD list key | **`items`** |

**Do not introduce** a top-level `{ data, meta, errors }` envelope on `/api` v1 — it would break the SPA and contract tests.

---

## 2. Frozen route index

### 2.1 Evidence CRUD / human review / explain / extract

| Method | Route | Request | Success |
|--------|-------|---------|---------|
| GET | `/api/projects/{project_id}/evidence` | Query: `file_id?`, `status?`, `limit?` (1–200, default 50), `offset?` (≥0) | `{ items, count, total, limit, offset }` |
| GET | `/api/projects/{project_id}/evidence/matrix` | Query: `format?` (`json`\|`markdown`\|`csv`), `file_ids?` (comma ints), `status?` | Matrix JSON **or** file download (RI-002) |
| GET | `/api/projects/{project_id}/evidence/themes` | Query: `format?` (`json`\|`markdown`), `file_ids?`, `status?`, clustering params | Themes JSON **or** markdown (RI-001) |
| GET | `/api/projects/{project_id}/evidence/gaps` | Query: `format?`, `file_ids?`, `status?` | Gaps JSON **or** markdown (RI-006) |
| GET | `/api/projects/{project_id}/evidence/graph` | Query: `file_ids?`, `status?`, `include_conflict?` | Project graph JSON (RI-005) |
| GET | `/api/projects/{project_id}/evidence/timeline` | Query: `format?`, `file_ids?`, `status?` | Timeline JSON **or** markdown (RI-007) |
| GET | `/api/projects/{project_id}/evidence/methodology` | Query: `format?`, `file_ids?`, `status?` | Methodology cards JSON **or** markdown (RI-008) |
| GET | `/api/evidence/{evidence_id}` | — | `EvidenceObject` |
| POST | `/api/evidence/{evidence_id}/reviews` | `{ status, reason?, edited_claim?, edited_quote? }` | `{ ok: true, evidence: EvidenceObject }` |
| POST | `/api/projects/{project_id}/evidence/extract` | `{ file_id, force?, sync? }` | See extract matrix |
| POST | `/api/evidence/explain` | `{ document_id, project_id, block_id? \| range_*, selected_text? }` | Explain DTO |

### 2.2 Bindings

| Method | Route | Request | Success |
|--------|-------|---------|---------|
| POST | `/api/documents/{document_id}/evidence-bindings` | `{ evidence_object_id, block_id? \| range_*, selected_text?, relation? }` | **201** binding row |
| GET | `/api/documents/{document_id}/evidence-bindings` | — | `{ items, count }` |
| DELETE | `/api/evidence-bindings/{binding_id}` | — | `{ ok: true }` |

### 2.3 Research Intelligence stages

Body = EvidenceQuery **or** `{ "query": EvidenceQuery }`.

| Method | Route | `stage` | Extra success keys |
|--------|-------|---------|-------------------|
| POST | `/api/evidence/search` | `retrieval` | `retrieval_version` |
| POST | `/api/evidence/retrieve` | `retrieval` | alias of search |
| POST | `/api/evidence/rank` | `ranking` | `ranking_version`, `ranking_strategy`, … |
| POST | `/api/evidence/consensus` | `consensus` | `consensus`, `consensus_version`, … |
| POST | `/api/evidence/conflict` | `conflict` | `conflict`, `conflict_version`, … |
| POST | `/api/evidence/reason` | `reasoning` | `reasoning`, `reasoning_version`, … |
| POST | `/api/evidence/writing` | `writing` | `writing`, `writing_version`, prior stages |

All RI responses include the **RI envelope** (§3).

### 2.4 Reviewer persistence (A-401)

| Method | Route | Success |
|--------|-------|---------|
| GET | `/api/documents/{document_id}/reviewer-runs` | `{ document_id, items, count }` (summary runs, no findings) |
| GET | `/api/documents/{document_id}/reviewer-runs/latest` | full `ReviewerRun` + `findings` + reconstructed `review` |
| GET | `/api/reviewer-runs/{run_id}` | same as latest |

---

## 3. RI response envelope (frozen)

Every RI stage returns:

```json
{
  "query": {},
  "objects": [],
  "total": 0,
  "truncated": false,
  "stage": "retrieval",
  "timing_ms": 12,
  "versions": { "retrieval": "1.0.0" }
}
```

| Field | Type | Notes |
|-------|------|--------|
| `query` | object | Normalized EvidenceQuery |
| `objects` | EvidenceObject[] | Ranked/filtered set for the stage |
| `total` | int | Full match count before truncation |
| `truncated` | bool | |
| `stage` | string | `retrieval` \| `ranking` \| `consensus` \| `conflict` \| `reasoning` \| `writing` |
| `timing_ms` | int | Server timing |
| `versions` | object | Map of stage → version string |

**Additive (kept):** legacy `*_version` fields (`retrieval_version`, …) and stage payloads (`consensus`, `conflict`, `reasoning`, `writing`).

Clients **MUST** ignore unknown top-level keys.

---

## 4. EvidenceQuery (frozen)

| Field | Required | Default / notes |
|-------|----------|-----------------|
| `intent` | yes | `support_sentence` \| `answer_question` \| `review_coverage` \| `compare_topic` \| `list_project` |
| `scope.project_id` | yes | |
| `scope.file_ids` | no | `null` or int[] |
| `scope.document_id` | no | ownership-checked when set |
| `filters.status` | no | default `["accepted"]` |
| `filters.confidence_bands` | no | default `["high","moderate","low"]` |
| `filters.study_types` | no | default `[]` |
| `filters.require_page_anchor` | no | default `true` |
| `ranking_strategy` | no | default `"default_v0"`; also `quality_first_v1`, `recency_v1`, `confidence_weighted_v1` |
| `result_limit` | no | default 20, clamp 1–100 |
| `query_text` | no | max 4000 chars |
| `anchors.block_id` / `anchors.selected_text` | no | |
| `section_type` | no | writing section; default `support_sentence` |

**Forbidden keys** (→ `422 validation_error`):  
`prompt`, `model`, `temperature`, `embeddings`, `vector_index`, `api_key`, `provider`.

> `literature_review` is a **`section_type`**, not an `intent`.

---

## 5. Extract status matrix (frozen)

| HTTP | `error` (if error) | Typical body |
|------|--------------------|--------------|
| 202 | — | `{ job_id, run_id, status: "pending", pipeline_version }` |
| 200 | — | succeeded / sync / idempotent reuse (`status`, `objects_created`, `run_id`, `job_id`, `pipeline_version`, …) |
| 400 | `not_research_ready` | + `status: "skipped"`, `reason`, `objects_created: 0`, … |
| 409 | `missing_phase1` \| `already_running` | + status/job metadata |

`pipeline_version` currently `"2.2.0"` (pipeline semver, not API version).

---

## 6. Human review request (frozen)

```json
{
  "status": "accepted",
  "reason": "optional",
  "edited_claim": "optional when status=edited",
  "edited_quote": "optional when status=edited"
}
```

`status` ∈ `accepted` \| `rejected` \| `edited`.  
`edited` requires `edited_claim` and/or `edited_quote`.

**Not frozen:** older IDD sketches using `action` / `patch` / `note` — those are **not** implemented.

---

## 7. Explain request / response (frozen)

**Request:** `document_id`, `project_id`, plus `block_id` **or** (`range_start` + `range_end`); optional `selected_text`.

**Response:** `{ status: "ok", sufficiency, sentence, evidence[], chain[], warnings[] }`  
(ADR-frozen Inspector shape — see evidence-contract for field detail.)

---

## 8. Writing nested payload (frozen keys)

RI writing responses nest generation under **`writing`** (not a flat root GroundedWritingResult).

Frozen keys under `writing`:

`status`, `blocked_reason`, `mode`, `section_type`, `paragraph`, `sections`, `plan`, `citations`, `bibliography`, `review`, `warnings`, `disclaimer`, `supporting_count`, `metrics`, optional `reviewer_run_id`, optional `writing_version`.

**Additive (RI-009 / Writing Intelligence v2):** `ri_context` (themes, gaps, methodology, timeline, consensus, conflict), `outline[]` (slot → theme_ids / evidence_ids / paper_ids), `draft_metadata` (evidence_ids, theme_ids, gap_ids, consensus/conflict versions, `prompt_version`, `reproducibility_hash`). `mode` is `grounded_v1`; `writing_version` **`2.0.0`**. This is a **Research → Writing bridge**, not a separate AI writing engine — LLM remains last; reviewer stays Evidence-first.

- `status`: `ok` \| `blocked` (still HTTP **200**)
- Citation items use **`evidence_id`** (not `evidence_object_id`)
- Blocked reasons are product strings (e.g. `insufficient_evidence`) — **not** HTTP `error` codes

Top-level also includes `writing_version` and full prior RI stages.

---

## 9. Binding DTO (frozen)

Create **201** / list item:

`id`, `document_id`, `evidence_object_id`, `block_id`, `range_start`, `range_end`, `selected_text`, `relation`

`relation` default `supports`; allowed: `supports` \| `contradicts` \| `related`.

---

## 10. ReviewerRun summary / full (frozen)

See [evidence-contract.md](./evidence-contract.md) § ReviewerRun.  
List endpoints omit `findings`/`review`; latest and get-by-id include them.

---

## 11. Explicitly out of freeze (evolving)

- Ranking strategy *internals* beyond documented registry names (new names = minor contract bump)
- Consensus/conflict algorithm internals (payload keys frozen; scores/metrics may grow additively)
- Writing section prose / metrics field synonyms
- Chat `/api/chat`, account, export-support routes (separate surfaces)
- Ideal path renames (`/api/evidence-objects`, `/api/papers`)

### Ranking strategies (A-403 registry)

| Name | Role |
|------|------|
| `default_v0` | Default — acceptance → band → quality → design → contradiction-free → recency |
| `quality_first_v1` | Study quality / design first |
| `recency_v1` | Freshest accepted first |
| `confidence_weighted_v1` | Composite score; emits `ranking_diagnostics.object_scores.*.composite` |

Unknown strategy → `422 validation_error` at EvidenceQuery normalize.  
Additive: `ranking_diagnostics` on ranking (and forwarded) stages.

---

## Change process

1. ADR (if breaking or renaming frozen fields)  
2. Update this file + companions  
3. Bump `contracts_version` in [README.md](./README.md)  
4. Update IDD-0003 to match  
5. Notify Developer B (`frontend-compatibility.md`)
