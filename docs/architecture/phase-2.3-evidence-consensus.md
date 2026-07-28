# Phase 2.3 Sprint 3 — Consensus Analysis

Status: **Complete**  
Depends on: Evidence Ranking (Sprint 2), Evidence Query v0 (ADR-0007)  
API: `POST /api/evidence/consensus`

---

## Responsibility

Aggregate ranked EvidenceObjects into supporting / contradicting / neutral counts and an ordinal consensus label.

- **No LLM** — pure aggregation over stored fields + binding relations
- Does **not** invent objects or mutate accepted evidence
- Consumes Ranking output; preserves object order and identity

---

## Classification (`consensus_v0`)

Preference order per object:

1. Writing binding / explicit `relation` (`supports` | `contradicts` | `related`)
2. Non-empty `supports` / `contradicts` arrays on the EvidenceObject
3. Otherwise `neutral`

### Labels

| Label | Rule |
|-------|------|
| `none` | No supporting and no contradicting |
| `opposed` | Contradicting only |
| `contested` | Contradicting ≥ supporting (both > 0 or equal) |
| `strong` | Supporting ≥ 2 and supporting ≥ 2 × contradicting |
| `moderate` | Supporting > contradicting but not strong |

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
  "stage": "consensus",
  "consensus_version": "1.0.0",
  "consensus": {
    "label": "strong",
    "supporting": 8,
    "contradicting": 2,
    "neutral": 1,
    "supporting_ids": [],
    "contradicting_ids": [],
    "neutral_ids": []
  },
  "ranking_version": "1.0.0",
  "ranking_strategy": "default_v0",
  "retrieval_version": "1.0.0"
}
```

Fixture: `tests/fixtures/evidence/consensus_response_v0.json`

---

## Implementation

| Piece | Path |
|-------|------|
| Stage logic | `backend/evidence/consensus.py` |
| Route | `backend/evidence/api/routes.py` (`POST /api/evidence/consensus`) |
| FE client | `frontend/src/features/evidence/api.ts` (`consensus`) |
| Unit tests | `backend/evidence/tests/test_consensus_unit.py` |
| API tests | `tests/test_evidence_consensus.py` |

Pipeline: EvidenceQuery → Retrieval → Ranking → Consensus.

---

## Exit criteria

- [x] Supporting / contradicting / neutral aggregation  
- [x] Ordinal label without LLM  
- [x] Dedicated Consensus API + test suite  
- [x] Object ids only from Ranking/Retrieval (no invention)  
- [x] Authz + forbidden model knobs unchanged  
