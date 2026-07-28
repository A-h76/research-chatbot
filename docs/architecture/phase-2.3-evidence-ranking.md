# Phase 2.3 Sprint 2 — Evidence Ranking

Status: **Complete**  
Depends on: Evidence Retrieval (Sprint 1), Evidence Query v0 (ADR-0007)  
API: `POST /api/evidence/rank`

---

## Responsibility

Reorder EvidenceObjects returned by Retrieval.

- Does **not** invent objects or change object identity / field values
- Does **not** re-read PDFs
- Interprets `ranking_strategy` (named, versioned)
- `/search` and `/retrieve` remain Retrieval-only; Ranking is its own stage API

---

## Strategy `default_v0`

Strongest first (ADD-0005):

```text
Acceptance → confidence band → study quality → study design
→ contradiction-free → recency → stable id
```

Unsupported strategies → `422`.

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
  "stage": "ranking",
  "ranking_version": "1.0.0",
  "ranking_strategy": "default_v0",
  "retrieval_version": "1.0.0"
}
```

Fixture: `tests/fixtures/evidence/ranking_response_v0.json`

---

## Implementation

| Piece | Path |
|-------|------|
| Stage logic | `backend/evidence/ranking.py` |
| Route | `backend/evidence/api/routes.py` (`POST /api/evidence/rank`) |
| FE client | `frontend/src/features/evidence/api.ts` (`rank`) |
| Unit tests | `backend/evidence/tests/test_ranking_unit.py` |
| API tests | `tests/test_evidence_ranking.py` |

Pipeline composition: EvidenceQuery → Retrieval → Ranking (reorder only).

---

## Exit criteria

- [x] Reorders Retrieval EvidenceObjects only  
- [x] `default_v0` factors quality / design / acceptance / contradictions / recency  
- [x] Dedicated Ranking API + test suite  
- [x] Authz + forbidden model knobs unchanged from Query contract  
- [x] Search/retrieve stage identity preserved (`stage: retrieval`)  
