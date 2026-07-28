# Phase 2.3 Sprint 4 — Conflict Analysis

Status: **Complete**  
Depends on: Consensus (Sprint 3), Evidence Query v0 (ADR-0007)  
API: `POST /api/evidence/conflict`

---

## Responsibility

Code **why** supporting and contradicting EvidenceObjects disagree.

- **No LLM** — mediators from structured metadata + lexical facets
- **Links** object ids; does not invent EvidenceObjects
- Runs after Consensus in the pipeline

---

## Mediators (`conflict_v0`)

| Code | Signal |
|------|--------|
| `population_differs` | Population cues / provenance differ (e.g. adults vs children) |
| `dosage_differs` | Dose / regimen cues differ (e.g. 10 mg vs 5 mg) |
| `method_differs` | `study_type` (or provenance method) differs |
| `outcome_differs` | Support/contradict outcome labels differ |

Mediators are only coded when **both** sides have a non-empty facet and the sets differ. Conflict can be present with an empty mediator list (honest: disagreement observed, facets insufficient).

---

## Contract

**Request:** EvidenceQuery v0 (or `{ "query": EvidenceQuery }`)

**Response:**

```json
{
  "query": { },
  "objects": [ ],
  "total": 0,
  "truncated": false,
  "stage": "conflict",
  "conflict_version": "1.0.0",
  "conflict": {
    "has_conflict": true,
    "mediators": ["population_differs", "method_differs"],
    "links": [
      {
        "a_id": 1,
        "b_id": 2,
        "a_stance": "supporting",
        "b_stance": "contradicting",
        "mediators": ["method_differs"]
      }
    ],
    "pair_count": 1,
    "supporting_ids": [1],
    "contradicting_ids": [2]
  },
  "consensus": { },
  "consensus_version": "1.0.0",
  "ranking_version": "1.0.0",
  "ranking_strategy": "default_v0",
  "retrieval_version": "1.0.0"
}
```

Fixture: `tests/fixtures/evidence/conflict_response_v0.json`

---

## Implementation

| Piece | Path |
|-------|------|
| Stage logic | `backend/evidence/conflict.py` |
| Route | `backend/evidence/api/routes.py` (`POST /api/evidence/conflict`) |
| FE client | `frontend/src/features/evidence/api.ts` (`conflict`) |
| Unit tests | `backend/evidence/tests/test_conflict_unit.py` |
| API tests | `tests/test_evidence_conflict.py` |

Pipeline: EvidenceQuery → Retrieval → Ranking → Consensus → Conflict.

---

## Exit criteria

- [x] Four coded mediators only (no free-text LLM reasons)  
- [x] Links supporting ↔ contradicting object ids  
- [x] Dedicated Conflict API + test suite  
- [x] No invented EvidenceObjects  
- [x] Authz + forbidden model knobs unchanged  
