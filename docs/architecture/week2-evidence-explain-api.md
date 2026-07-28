# Week 2 Evidence Layer — Explain API Contract

Status: Frozen  
Parent: `docs/architecture/week2-evidence-layer-backend-technical-design.md` §6.5  
Consumer: Writing Studio Evidence Inspector

---

## Endpoint

`POST /api/evidence/explain`

Auth: session / JWT (same as Writing Shell). CSRF: required for cookie session from SPA.

---

## Request

```json
{
  "document_id": 55,
  "project_id": 2,
  "block_id": "blk_12",
  "range_start": 100,
  "range_end": 180,
  "selected_text": "optional display hint"
}
```

| Field | Required | Notes |
|-------|----------|-------|
| document_id | yes | Writing document |
| project_id | yes | Must match document project |
| block_id | preferred | Stable editor anchor |
| range_start / range_end | optional | Used when block_id absent or for precision |
| selected_text | optional | Never sole identity for authz |

Validation: at least one of `block_id` or (`range_start` + `range_end`).

---

## Response (`200`)

```json
{
  "status": "ok",
  "sufficiency": "sufficient",
  "sentence": {
    "block_id": "blk_12",
    "range_start": 100,
    "range_end": 180,
    "text": "…"
  },
  "evidence": [],
  "chain": [],
  "warnings": []
}
```

### `sufficiency`

| Value | Meaning |
|-------|---------|
| `sufficient` | ≥1 **accepted** supporting object for the anchor |
| `weak` | Only candidates, low band, or contradict-heavy without accepted support |
| `insufficient` | No usable bindings/objects — **empty `evidence`**, no model padding |

### `evidence[]`

Each item is a stored EvidenceObject projection + `relation` from binding. Server validates ownership of every id. Order is server-defined (accepted first, then by confidence band, then id) — client must not re-rank.

### `chain[]`

Steps assembled from bindings + provenance fields only, e.g.:

```json
[
  { "step": "binding", "detail": "block_id blk_12 → evidence 901 (supports)" },
  { "step": "provenance", "detail": "pipeline 2.2.0; Phase 1.5 study_quality High" }
]
```

Week 2: no LLM required. If an LLM is later used, it may only narrate **already coded** steps after ids resolve.

---

## Errors

| Code | When |
|------|------|
| 401 | Unauthenticated |
| 403 | Document/project not owned |
| 404 | Document missing |
| 422 | Missing anchor / invalid body |

Error body shape matches Writing Shell conventions (`error`, `message`, optional `code`).

---

## Invariants (Principle 0)

1. No evidence id appears unless loaded from DB under tenant scope.
2. No claim/quote text invented in this handler.
3. Insufficient ⇒ honest empty state.
4. Candidates labeled via `status`; “supported by” product copy prefers accepted.

---

## Fixture names

- `tests/fixtures/evidence/explain_sufficient.json`
- `tests/fixtures/evidence/explain_insufficient.json`
- `tests/fixtures/evidence/explain_candidates_only.json`
