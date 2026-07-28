# Phase 2.3 Sprint 0 — Evidence Query Contract (frozen)

Status: **Frozen**  
Effective: after `v0.2.0-rc1` (Evidence Platform closed)  
Governing: ADR-0006 (staged pipeline), ADR-0007 (this freeze)  
Parent: `docs/architecture/phase-2.3-research-intelligence-pipeline.md`

---

## Purpose

Every future capability asks for evidence the same way.

```text
Writing | Reviewer | Compare | Research Assistant
                    │
                    ▼
              EvidenceQuery
                    │
                    ▼
         Research Intelligence pipeline
         (Retrieval → Ranking → …)
                    │
                    ▼
            EvidenceObject[]
```

This is the **query language** of the Evidence Layer — not an LLM prompt API.

---

## Frozen shape (v0)

```json
{
  "intent": "support_sentence",
  "scope": {
    "project_id": 2,
    "file_ids": null,
    "document_id": 55
  },
  "filters": {
    "status": ["accepted"],
    "confidence_bands": ["high", "moderate", "low"],
    "study_types": [],
    "require_page_anchor": true
  },
  "ranking_strategy": "default_v0",
  "result_limit": 20,
  "query_text": "optional match text",
  "anchors": {
    "block_id": "blk_12",
    "selected_text": "optional"
  }
}
```

### Required platform fields

| Field | Type | Meaning |
|-------|------|---------|
| `intent` | string enum | Why evidence is needed |
| `scope` | object | Project (required) + optional `file_ids` / `document_id` |
| `filters` | object | Status, bands, study types, grounding |
| `ranking_strategy` | string | Named, versioned ranker id (Ranking stage interprets) |
| `result_limit` | int | Max objects returned (1–100; default 20) |

`user_id` is **not** accepted from the client as authority — the server binds the authenticated user into scope.

### Optional presentation / match hints

| Field | Meaning |
|-------|---------|
| `query_text` | Free text to match (sentence, question, topic) |
| `anchors.block_id` | Writing block id |
| `anchors.selected_text` | Display / sticky selection hint |

These help Retrieval match; they are not model controls.

---

## Intent enum (v0)

| Intent | Typical consumer |
|--------|------------------|
| `support_sentence` | Writing Inspector / Writing Intelligence |
| `answer_question` | Research Assistant |
| `review_coverage` | Reviewer |
| `compare_topic` | Compare |
| `list_project` | Library / ops browse |

Additive intents require fixture update; removing/renaming requires ADR.

---

## Filters (v0)

| Key | Default | Notes |
|-----|---------|-------|
| `status` | `["accepted"]` | May include `candidate` when explicitly requested |
| `confidence_bands` | all bands | Subset of `low\|moderate\|high` |
| `study_types` | `[]` (any) | Strings aligned with EvidenceObject.study_type |
| `require_page_anchor` | `true` | Prefer grounded objects |

---

## Explicitly excluded from this contract

Do **not** add to EvidenceQuery v0:

- `prompt`
- `model`
- `temperature`
- `embeddings`
- `vector_index`
- provider / API keys
- raw PDF paths

Those are Retrieval **implementation** details (or later generation stages), not the platform ask interface.

---

## Response envelope (Retrieval stage — preview)

Retrieval returns Evidence Layer objects only (no parallel DTO corpus):

```json
{
  "query": { /* echo normalized EvidenceQuery */ },
  "objects": [ /* EvidenceObject public projections */ ],
  "total": 0,
  "truncated": false
}
```

Ranking may reorder `objects` in a later stage without changing object identity.
Consensus/Conflict/Reasoning consume the same object ids.

---

## Versioning

| Change | How |
|--------|-----|
| Additive optional filter / intent | Same major (`evidence_query.v0`); update fixtures |
| Remove / rename / semantic break | New ADR + `evidence_query.v1` |

Fixture: `tests/fixtures/evidence/evidence_query_v0.json`.

---

## Sprint 0 exit criteria

- [x] ADR-0007 accepted  
- [x] This contract doc frozen  
- [x] Fixture checked in  
- [x] Sprint 1 Retrieval implements against this contract (no redefinition)
