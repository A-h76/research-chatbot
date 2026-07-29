# Phase 2.3 Sprint 6 — Writing Intelligence

Status: **Complete**  
Depends on: Reasoning (Sprint 5) + full RI pipeline  
API: `POST /api/evidence/writing`

---

## Responsibility

**Generation last.** Produce a grounded writing suggestion only after:

```text
Retrieval → Ranking → Consensus → Conflict → Reasoning → Writing
```

- Does **not** invent EvidenceObjects or freeform research facts
- Mode `grounded_v0`: assembles paragraph + citations from supporting EvidenceObject claims/quotes
- Blocks generation when evidence is insufficient / opposed / no supporting objects
- Contested consensus may still generate with warnings + conflict mediator notes

Unlocks safe entry to roadmap Phase 2.4 (optional LLM narration can wrap this later without bypassing the gate).

**Milestone 1 + Sprint A:** Writing Intelligence is Planner → Context Builder
(structured argument: themes / consensus / conflict / methodology / chronology) →
Section Generator with Gateway synthesis (`[#id]` markers; heuristic fallback).
`writing_version` **1.3.0**.

---

## Gate

| Condition | Result |
|-----------|--------|
| `sufficiency=insufficient` / empty support | `status=blocked` |
| Consensus `opposed` | `status=blocked` |
| Supporting claims available | `status=ok` + paragraph + citations |

---

## Contract

**Request:** EvidenceQuery v0 (or `{ "query": EvidenceQuery }`)

**Response (ok):**

```json
{
  "stage": "writing",
  "writing_version": "1.0.0",
  "writing": {
    "status": "ok",
    "blocked_reason": null,
    "mode": "grounded_v0",
    "paragraph": "…",
    "citations": [{ "evidence_id": 1, "page": 2, "claim": "…" }],
    "warnings": [],
    "disclaimer": "…"
  },
  "reasoning": { },
  "objects": [ ]
}
```

Fixture: `tests/fixtures/evidence/writing_intelligence_response_v0.json`

---

## Implementation

| Piece | Path |
|-------|------|
| Stage logic | `backend/evidence/writing_intelligence.py` |
| Route | `backend/evidence/api/routes.py` (`POST /api/evidence/writing`) |
| FE client | `frontend/src/features/evidence/api.ts` (`writing`) |
| Unit tests | `backend/evidence/tests/test_writing_intelligence_unit.py` |
| API tests | `tests/test_evidence_writing_intelligence.py` |

---

## ADD-0005 compliance

1. **Stages called:** Retrieval → Ranking → Consensus → Conflict → Reasoning → Writing  
2. **Evidence APIs:** EvidenceQuery → EvidenceObjects only  
3. **Insufficient UX:** `writing.status=blocked` + `blocked_reason` (no invented paragraph)  
4. **NL generation seat:** last stage only (`grounded_v0`; no PDF/chat-only bypass)

---

## Exit criteria

- [x] Generation only after Reasoning  
- [x] Grounded citations from EvidenceObject ids  
- [x] Block path when evidence inadequate  
- [x] Dedicated API + tests  
- [x] Phase 2.3 sprint map complete through Writing Intelligence  
