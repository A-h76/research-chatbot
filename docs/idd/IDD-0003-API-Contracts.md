# IDD-0003 — API Contracts

| Field | Value |
|-------|-------|
| **Status** | Proposed |
| **Style** | OpenAPI-oriented REST |
| **Base URL** | `/api` (app) · `/auth` (identity) |
| **Legacy aliases** | Documented where live paths differ from ideal names |

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
  "error": "insufficient_evidence",
  "detail": "Human-readable explanation",
  "fields": { "project_id": ["required"] }
}
```

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

### GET `/api/projects/{project_id}/evidence`

**Query:** `status?`, `paper_id?` / `file_id?`, `limit`, `offset`  
**Response:** `{ "items": EvidenceObject[], "total": number }`

### GET `/api/evidence/{id}`

**Response:** `EvidenceObject`  
**Errors:** `404`, `403`

### POST `/api/projects/{project_id}/evidence/extract`

**Purpose:** Enqueue Evidence extraction for a Research Ready paper.  
**Request:**

```json
{ "file_id": 123 }
```

**Response `202`:**

```json
{ "job_id": 99, "run_id": 12, "status": "pending" }
```

**Errors:** `400` not research ready; `403`; `409` already running

### POST `/api/evidence/{id}/reviews`

**Request:** `{ "action": "accept" | "reject" | "edit", "patch"?: object, "note"?: string }`  
**Response `200`:** updated `EvidenceObject` (edit may return superseding object)

### POST `/api/evidence/explain`

**Purpose:** Frozen Inspector explain (ADR).  
**Request:** `{ "evidence_id": number }` or frozen shape as implemented  
**Response `200`:** explanation DTO (quote, provenance, supports/contradicts, …)

---

## 7. Research Intelligence (EvidenceQuery stages)

### EvidenceQuery object

```json
{
  "intent": "literature_review",
  "scope": { "project_id": 1, "file_ids": null, "document_id": 10 },
  "filters": {
    "status": ["accepted"],
    "confidence_bands": ["high", "moderate", "low"]
  },
  "anchors": {},
  "section_type": "literature_review",
  "ranking_strategy": "default_v0",
  "result_limit": 20
}
```

> `intent` must be one of IDD-0002 constants (e.g. `support_sentence`, `answer_question`, …).  
> **Forbidden keys:** `prompt`, `model`, `temperature`, `embeddings`, `provider`, `api_key`.

Envelope variants: body may be the query itself **or** `{ "query": { ... } }`.

### POST `/api/evidence/search` · `/api/evidence/retrieve`

**Purpose:** Retrieval stage.  
**Response `200`:** `{ "items": EvidenceObject[], "query": EvidenceQuery }`

### POST `/api/evidence/rank`

**Response `200`:** `{ "items": EvidenceObject[], "strategy": "default_v0" }`

### POST `/api/evidence/consensus`

**Response `200`:** `{ "aggregate": object, "items": EvidenceObject[] }`

### POST `/api/evidence/conflict`

**Response `200`:** `{ "mediators": object[], "items": EvidenceObject[] }`

### POST `/api/evidence/reason`

**Response `200`:** `{ "reasoning": object, "items": EvidenceObject[] }`

### POST `/api/evidence/writing`

**Purpose:** Grounded Writing Intelligence (not freeform chat).  
**Request:** EvidenceQuery (+ optional draft constraints)  
**Response `200` — GroundedWritingResult:**

```json
{
  "status": "ok",
  "section_type": "literature_review",
  "paragraph": "...",
  "citations": [{ "evidence_object_id": 1, "label": "1" }],
  "metrics": { "grounding_pct": 0.92, "reviewer_pass_rate": 0.8 },
  "review": {
    "reviewer_version": "1.1.0",
    "issues": []
  },
  "warnings": [],
  "disclaimer": "...",
  "writing_version": "1.3.1"
}
```

**Blocked:**

```json
{
  "status": "blocked",
  "blocked_reason": "insufficient_evidence",
  "writing_version": "1.3.1"
}
```

**Status codes:** `200` (including blocked), `400` invalid query, `403`, `429`

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

**Request:** `{ "evidence_object_id": number, "block_id"?: string, "span"?: object }`  
**Response `201`:** `Citation` / binding

### DELETE `/api/evidence-bindings/{id}`

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

### GET `/api/jobs/{job_id}` _(or upload job status endpoints)_

**Response:**

```json
{
  "id": 99,
  "job_type": "evidence_extract",
  "status": "running",
  "attempts": 1,
  "error": null,
  "updated_at": "2026-07-30T10:00:00Z"
}
```

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
| 400 | Validation / contract break |
| 401 | Not authenticated |
| 403 | Forbidden / not owner / beta |
| 404 | Missing |
| 409 | Conflict (autosave, duplicate job) |
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

Frontend inserts `paragraph`, POSTs bindings, shows `review.issues`, enables Export only if `status=ok` and user acknowledged warnings.
