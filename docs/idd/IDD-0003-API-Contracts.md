# IDD-0003 — API Contracts

| Field | Value |
|-------|-------|
| **Status** | Active (Evidence/RI sections frozen A-402 → `docs/contracts/`) |
| **Style** | OpenAPI-oriented REST |
| **Base URL** | `/api` (app) · `/auth` (identity) |
| **Legacy aliases** | Documented where live paths differ from ideal names |
| **contracts_version** | 1.2.0 |

---

## 1. Global conventions

### 1.1 API naming rules

1. Nouns are plural: `/api/projects`, `/api/evidence-objects`.
2. Nested resources for ownership: `/api/projects/{project_id}/evidence`.
3. Actions as sub-resources or RPC-style POST when not CRUD: `/api/evidence/retrieve`.
4. snake_case JSON; ISO-8601 timestamps; UTF-8.
5. IDs are integers unless noted.
6. **Paper** in docs ≡ `file_id` in many legacy routes—clients MUST accept both `paper_id` and `file_id` in responses during transition.

### 1.2 Authentication

| Scheme | Header / cookie | Used for |
|--------|-----------------|----------|
| Session | Cookie (same-origin) | Most SPA calls |
| Bearer JWT | `Authorization: Bearer <access>` | Upload, bulk, pipeline, RAG |

Unauthenticated → `401` with standard error body (IDD-0007 / §11).

### 1.3 Versioning

See [IDD-0008](./IDD-0008-Versioning.md). Current surface is **unversioned path** (`/api/...`) treated as **v1**. Breaking changes require `/api/v2` or negotiated headers after approval.

### 1.4 Pagination

Default envelope:

```json
{
  "items": [],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

Query: `limit` (1–100, default 50), `offset` (≥0). Some list endpoints use `page`/`page_size`—normalize in v1.1.

### 1.5 Filtering & sorting

- Filter: query params named after fields (`status=accepted`, `project_id=1`).
- Sort: `sort=field` or `sort=-field` (descending). Allowed fields listed per endpoint.
- Unknown sort → `400 validation_error`.

### 1.6 Error body

```json
{
  "error": "validation_error",
  "detail": "Human-readable explanation",
  "fields": { "project_id": ["required"] }
}
```

`fields` is optional/reserved. Evidence/RI routes emit `{ error, detail }` today — see [error-contract.md](../contracts/error-contract.md).  
EvidenceQuery validation uses **HTTP 422** (not 400).
---

## 2. Identity

### GET `/api/me`

**Purpose:** Current user + session validity (SPA boot gate).  
**Auth:** Session or JWT  
**Response `200`:**

```json
{
  "id": 1,
  "email": "a@univ.edu",
  "name": "Ada",
  "picture": null,
  "plan": "beta",
  "is_admin": false
}
```

**Errors:** `401 not_authenticated`

### GET `/api/auth/jwt`

**Purpose:** Mint Bearer access for JWT-required routes.  
**Auth:** Session  
**Response `200`:** `{ "access": "<jwt>", "expires_in": 3600 }`

---

## 3. Projects

### GET `/api/projects`

List projects for user.  
**Response:** `{ "items": [ Project ] }` or array (legacy)—**Frontend MUST handle both**; Backend SHOULD converge to envelope.

### POST `/api/projects`

**Request:** `{ "name": string, "emoji"?: string }`  
**Response `201`:** `Project`

### GET `/api/projects/{project_id}`

**Response `200`:** `Project` (+ hub extras if present)  
**Errors:** `404`, `403`

### PATCH `/api/projects/{project_id}`

**Request:** partial `name`, `emoji`, `instructions`  
**Response `200`:** `Project`

---

## 4. Library / Papers

> Live paths often use `/api/files`. Contract name **Paper**; path alias `/api/files` ≡ `/api/papers` until rename ADR.

### GET `/api/files` _(alias: Papers list)_

**Purpose:** Library search/list.  
**Query:** `project_id?`, `q?`, `sort?`, `limit`, `offset`, `import_source?`, `tag?`, `doi?`, `author?`, `year?`, `venue?`, `recent_days?`  
**Response `200`:** `{ "items": Paper[], "total": number, "facets"?: object }`

### POST `/api/files` _(session upload)_

**Purpose:** Upload PDF (multipart).  
**Auth:** Session  
**Response `201`:** `Paper` (+ job id if async)

### POST `/api/documents/upload` _(JWT upload)_

**Auth:** Bearer  
**Purpose:** Same domain outcome as session upload—creates Paper + `import` job.  
**Response:** `{ "file": Paper, "job_id": number }`

### GET `/api/files/{paper_id}`

**Response `200`:** `Paper` detail (+ readiness)

### DELETE `/api/files/{paper_id}`

**Response `204` or `200`:** `{ "ok": true }`

### GET `/api/files/{paper_id}/pipeline` _(JWT may be required)_

**Purpose:** Document Understanding / job progress.  
**Response:** pipeline phases + status (see Frontend loading contracts).

---

## 5. Library bridge

### GET `/api/library/connections`

**Response:** `{ "zotero": ConnectionStatus, "mendeley": ConnectionStatus, ... }`

### POST `/api/library/zotero/connect` · Mendeley equivalent

Starts OAuth; returns `{ "authorize_url": string }` or redirects.

### POST `/api/library/zotero/import` · folders/collections variants

**Request:** collection keys + `project_id?`  
**Response:** `{ "created": n, "skipped": n, "created_ids": number[] }`

---

## 6. Evidence Platform

> **A-402:** Authoritative shapes → [`docs/contracts/api-contracts.md`](../contracts/api-contracts.md) + [`evidence-contract.md`](../contracts/evidence-contract.md).  
> Sketches below are aligned to **live** behavior (2026-07-30).

### GET `/api/projects/{project_id}/evidence`

**Query:** `status?`, `file_id?`, `limit` (1–200, default 50), `offset`  
**Response:** `{ "items": EvidenceObject[], "count": number, "total": number, "limit": number, "offset": number }`

### GET `/api/evidence/{id}`

**Response:** `EvidenceObject` ([evidence-contract](../contracts/evidence-contract.md))  
**Errors:** `404`

### POST `/api/projects/{project_id}/evidence/extract`

**Request:** `{ "file_id": 123, "force"?: bool, "sync"?: bool }`  
**Response `202`:** `{ "job_id", "run_id", "status": "pending", "pipeline_version" }`  
**Also:** `200` succeeded/idempotent/sync; `400` `not_research_ready`; `409` `missing_phase1` \| `already_running`

### POST `/api/evidence/{id}/reviews`

**Request:** `{ "status": "accepted"|"rejected"|"edited", "reason"?: string, "edited_claim"?: string, "edited_quote"?: string }`  
**Response `200`:** `{ "ok": true, "evidence": EvidenceObject }`

### POST `/api/evidence/explain`

**Request:** `{ "document_id", "project_id", "block_id"? | "range_start"+"range_end", "selected_text"? }`  
**Response `200`:** `{ "status": "ok", "sufficiency", "sentence", "evidence", "chain", "warnings" }`

---

## 7. Research Intelligence (EvidenceQuery stages)

### EvidenceQuery object

```json
{
  "intent": "support_sentence",
  "scope": { "project_id": 1, "file_ids": null, "document_id": 10 },
  "filters": {
    "status": ["accepted"],
    "confidence_bands": ["high", "moderate", "low"]
  },
  "anchors": {},
  "section_type": "literature_review",
  "ranking_strategy": "default_v0",
  "result_limit": 20,
  "query_text": "optional"
}
```

> `intent` ∈ `support_sentence` \| `answer_question` \| `review_coverage` \| `compare_topic` \| `list_project`.  
> `literature_review` is a **`section_type`**, not an intent.  
> **Forbidden keys:** `prompt`, `model`, `temperature`, `embeddings`, `provider`, `api_key`, `vector_index`.

Envelope variants: body may be the query itself **or** `{ "query": { ... } }`.

### Shared RI response envelope

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

List key is **`objects`** (not `items`). Stage payloads are additive (`consensus`, `conflict`, `reasoning`, `writing`, legacy `*_version` fields).

### POST `/api/evidence/search` · `/api/evidence/retrieve`

**Response `200`:** RI envelope, `stage: "retrieval"`

### POST `/api/evidence/rank`

**Response `200`:** RI envelope + `ranking_strategy`, `ranking_version`

### POST `/api/evidence/consensus`

**Response `200`:** RI envelope + `consensus` object (not `aggregate`)

### POST `/api/evidence/conflict`

**Response `200`:** RI envelope + `conflict` (`has_conflict`, `mediators`, `links`, …)

### POST `/api/evidence/reason`

**Response `200`:** RI envelope + `reasoning`

### POST `/api/evidence/writing`

**Response `200`:** RI envelope with nested **`writing`** (not a flat root GroundedWritingResult):

```json
{
  "stage": "writing",
  "writing_version": "1.3.1",
  "objects": [],
  "writing": {
    "status": "ok",
    "section_type": "literature_review",
    "paragraph": "...",
    "citations": [{ "evidence_id": 1, "file_id": 2, "page": 3, "claim": "...", "quote": "..." }],
    "metrics": {},
    "review": { "reviewer_version": "1.1.0", "issues": [] },
    "warnings": [],
    "disclaimer": "...",
    "reviewer_run_id": 42
  }
}
```

**Blocked** (still HTTP 200): `writing.status = "blocked"`, `writing.blocked_reason` set, `paragraph` null.

**Status codes:** `200` (including blocked), `422` invalid query, `404`, `429`

### Reviewer persistence

- `GET /api/documents/{id}/reviewer-runs`
- `GET /api/documents/{id}/reviewer-runs/latest`
- `GET /api/reviewer-runs/{id}`

See [evidence-contract.md](../contracts/evidence-contract.md) §5.

---

## 8. Writing Studio

### GET `/api/writing/documents`

**Query:** `project_id?`, `status?`  
**Response:** `{ "items": WritingDocument[] }`

### POST `/api/writing/documents`

**Request:** `{ "project_id": number, "title"?: string }`  
**Response `201`:** `WritingDocument`

### GET `/api/writing/documents/{id}`

### PATCH `/api/writing/documents/{id}` _(autosave)_

**Request:** `{ "title"?: string, "body"?: string, "autosave_key"?: string }`  
**Response `200`:** document · `409` conflict if autosave key mismatch

### GET `/api/writing/documents/{id}/versions`

### POST `/api/writing/documents/{id}/restore`

**Request:** `{ "version_id": number }`

### POST `/api/documents/{id}/evidence-bindings`

**Request:** `{ "evidence_object_id": number, "block_id"?: string, "range_start"?: number, "range_end"?: number, "selected_text"?: string, "relation"?: string }`  
**Response `201`:** binding DTO (`id`, `document_id`, `evidence_object_id`, `block_id`, `range_start`, `range_end`, `selected_text`, `relation`)

### GET `/api/documents/{id}/evidence-bindings`

**Response:** `{ "items": Binding[], "count": number }`

### DELETE `/api/evidence-bindings/{id}`

**Response:** `{ "ok": true }`

---

## 9. Search contracts

### POST `/api/search` _(Library + notes + …)_

**Request:** `{ "q": string, "kinds"?: string[], "project_id"?: number }`  
**Response:** `{ "results": SearchResult[], "total": number, "q": string }`

### GET `/api/documents/search` _(JWT)_

Semantic paper chunk search.  
**Query:** `q`, `project_id?`, `limit?`

### POST `/api/rag` _(JWT)_

RAG answer grounded in library chunks—**tool surface**, not Evidence SoT. Prefer Evidence writing for lit review.

### GET `/api/discover`

OpenAlex discover.  
**Query:** `q`, `page?`  
**Response:** `{ "results": DiscoverWork[], ... }`

### Ranking

Use `POST /api/evidence/rank` with `ranking_strategy`. Do not invent client-side ranking of Evidence beyond display sort.

---

## 10. Jobs

### GET `/api/jobs/{job_id}/status`

**Auth:** Session  
**Response `200` (A-404):**

```json
{
  "job_id": 99,
  "status": "pending",
  "job_type": "evidence_extract",
  "attempts": 1,
  "last_error": "OpenAI timeout…",
  "progress": 0,
  "updated_at": "2026-07-30T10:00:00+00:00",
  "cached": false,
  "lifecycle": "retry_wait",
  "retry": {
    "attempts": 1,
    "max_attempts": 5,
    "run_after": "…",
    "backoff_seconds": 60,
    "will_retry": true
  },
  "timings": {
    "created_at": "…",
    "started_at": "…",
    "finished_at": "…",
    "duration_ms": 1200,
    "queue_wait_ms": 400
  },
  "error": { "message": "…", "code": "provider_timeout", "retriable": true },
  "file_id": 12,
  "max_attempts": 5
}
```

`status` remains `pending|running|done|failed`. `lifecycle` is additive (`queued|scheduled|retry_wait|running|succeeded|dead_letter`).  
Clients MUST keep reading `status` / `last_error`; new fields are optional.

Poll ≤ 2s while `pending|running`. Terminal: `done|failed`.

---

## 11. Export

### POST `/api/writing/documents/{id}/export`

**Request:** `{ "format": "markdown" | "docx" | "bibtex", "citation_style"?: "apa" }`  
**Response `202`:** `{ "export_job_id": number }` **or** `200` sync `{ "content": string, "filename": string }` for small markdown.

### GET `/api/export-jobs/{id}`

Status + `download_url` when `done`.

---

## 12. Status code summary

| Code | Meaning |
|------|---------|
| 200 | OK (incl. business `blocked` where documented) |
| 201 | Created |
| 202 | Accepted async |
| 204 | No content |
| 400 | Bad request / extract not research ready |
| 401 | Not authenticated |
| 403 | Forbidden / beta (Evidence ownership often surfaces as 404) |
| 404 | Missing / inaccessible |
| 409 | Conflict (autosave, extract already running, missing phase1) |
| 422 | Validation (EvidenceQuery, bindings, reviews) |
| 429 | Rate limited |
| 500 | Internal |
| 503 | Dependency unavailable |

---

## 13. Example: grounded lit review (happy path)

```http
POST /api/evidence/writing
Authorization: Bearer …
Content-Type: application/json

{
  "query": {
    "intent": "support_sentence",
    "scope": { "project_id": 7, "document_id": 3 },
    "filters": { "status": ["accepted"] },
    "section_type": "literature_review",
    "ranking_strategy": "default_v0",
    "result_limit": 20
  }
}
```

Frontend inserts `writing.paragraph`, POSTs bindings, shows `writing.review.issues`, enables Export only if `writing.status=ok` and user acknowledged warnings.
