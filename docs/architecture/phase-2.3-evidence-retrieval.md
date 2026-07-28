# Phase 2.3 Sprint 1 — Evidence Retrieval

Status: **Complete**  
Depends on: Evidence Query v0 (ADR-0007), Evidence Platform contracts (ADR-0005)  
APIs: `POST /api/evidence/search`, `POST /api/evidence/retrieve`

---

## Responsibility

Find EvidenceObjects for a normalized EvidenceQuery.

- Returns EvidenceObjects only (no parallel DTO corpus)
- Never invents objects, never reads PDFs
- Lexical overlap + binding preference = **retrieval relevance** (implementation detail)
- `ranking_strategy` is echoed for Sprint 2 Ranking — not fully interpreted here

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
  "stage": "retrieval",
  "retrieval_version": "1.0.0"
}
```

Fixture: `tests/fixtures/evidence/retrieval_response_v0.json`

---

## Implementation

| Piece | Path |
|-------|------|
| Stage logic | `backend/evidence/retrieval.py` |
| Routes | `backend/evidence/api/routes.py` |
| FE client | `frontend/src/features/evidence/api.ts` (`search` / `retrieve`) |
| Tests | `tests/test_evidence_retrieval.py` |

---

## Exit criteria

- [x] Implements Evidence Query without redefining it  
- [x] Both `/search` and `/retrieve` live  
- [x] Authz: project ownership; cross-user 404  
- [x] Rejects forbidden model knobs (422)  
- [x] Tests green  
