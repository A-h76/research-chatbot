# Phase 2.3 Sprint 5 — Reasoning Pipeline

Status: **Complete**  
Depends on: Conflict (Sprint 4), Consensus (Sprint 3), Evidence Query v0 (ADR-0007)  
API: `POST /api/evidence/reason`

---

## Responsibility

Produce a **structured explanation chain** from prior RI stages.

```text
Retrieve → Rank → Consensus → Conflict → Reason
```

- **No LLM / no generation** — templated steps from coded outputs only
- Explains EvidenceObjects; does not invent them
- Writing Intelligence (Sprint 6) may narrate later; this stage stays compiler-shaped

---

## Reasoning payload (`reasoning_v0`)

| Field | Meaning |
|-------|---------|
| `summary_code` | Ordinal conclusion code |
| `sufficiency` | `sufficient` \| `weak` \| `insufficient` |
| `steps` | Ordered `{step, detail[, code]}` templates |
| `evidence_ids` | Ids from the ranked object set only |
| `mediator_labels` | Fixed labels for conflict mediators |

### Step order

`retrieval` → `ranking` → `consensus` → `conflict` → `conclusion`

### Summary codes

| Code | When |
|------|------|
| `insufficient` | No objects |
| `none` | Consensus none |
| `opposed` | Contradicting only |
| `contested` | Contested without coded mediators |
| `contested_with_mediators` | Contested + mediators |
| `moderate` / `strong` | From consensus label |

---

## Contract

**Request:** EvidenceQuery v0 (or `{ "query": EvidenceQuery }`)

**Response:** echoes prior stage envelopes + `reasoning` (see fixture).

Fixture: `tests/fixtures/evidence/reasoning_response_v0.json`

---

## Implementation

| Piece | Path |
|-------|------|
| Stage logic | `backend/evidence/reasoning.py` |
| Route | `backend/evidence/api/routes.py` (`POST /api/evidence/reason`) |
| FE client | `frontend/src/features/evidence/api.ts` (`reason`) |
| Unit tests | `backend/evidence/tests/test_reasoning_unit.py` |
| API tests | `tests/test_evidence_reasoning.py` |

---

## Exit criteria

- [x] Structured chain from prior stages only  
- [x] No LLM / no invented EvidenceObjects  
- [x] Dedicated Reasoning API + test suite  
- [x] Authz + forbidden model knobs unchanged  
- [x] Generation deferred to Sprint 6  
