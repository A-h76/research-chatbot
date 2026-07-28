# Phase 2.3 — Research Intelligence Pipeline (design freeze for kickoff)

Status: Accepted architecture for Phase 2.3 — **implement only after `v0.2.0-rc1`**  
Depends on: Evidence Layer platform contracts (ADR-0005), ADD-0005, ADR-0004, ADR-0006  
Audience: Staff / principal engineers opening Phase 2.3

---

## 1) Three architectural eras (clean boundaries)

```text
Phase 1 — Research Analysis
  PDF → Document Understanding → Knowledge Graph
           (and Phase 1.5 Evidence Grading)

Phase 2.2 — Evidence Platform
  Analysis → EvidenceObjects → Inspector → Explain API

Phase 2.3 — Research Intelligence
  EvidenceObjects → Retrieval → Ranking → Consensus → Conflict → Reasoning
                 → Writing / Reviewer / Compare / Assistant
```

Each phase builds on the previous one **without replacing it**.

---

## 2) One pipeline, not independent modules

Do **not** build Retrieval, Ranking, Consensus, Conflict, and Reasoning as
separate products/engines.

Treat them as **stages of a single Research Intelligence pipeline**:

```text
Evidence Layer
       │
       ▼
Evidence Retrieval
       │
       ▼
Evidence Ranking
       │
       ▼
Consensus Analysis
       │
       ▼
Conflict Analysis
       │
       ▼
Reasoning
       │
       ▼
Presentation
```

| Stage | Responsibility | Rule of thumb |
|-------|----------------|---------------|
| Retrieval | Find candidate EvidenceObjects for an Evidence Query | Returns objects |
| Ranking | Order those objects | Reorders objects |
| Consensus | Aggregate support / contradict / neutral | Aggregates objects |
| Conflict | Code conflict mediators between objects | Links objects |
| Reasoning | Structured explanation from prior stages | Explains objects |
| Presentation | UI / Writing / Reviewer / Compare / Assistant | Consumes pipeline output |

Each stage has:

- **one responsibility**
- **one API**
- **one test suite**
- **one contract**

Composable, evolvable, no dual truth.

---

## 3) Frozen principle: RI never owns knowledge

> Research Intelligence never owns knowledge; it computes over Evidence Layer objects.

Therefore:

| Stage | Must |
|-------|------|
| Retrieval | return EvidenceObjects |
| Ranking | reorder EvidenceObjects |
| Consensus | aggregate EvidenceObjects |
| Conflict | link EvidenceObjects |
| Reasoning | explain EvidenceObjects |

**Forbidden:** inventing EvidenceObjects, mutating accepted evidence, reading PDFs as the answer path, or introducing parallel research-knowledge storage (restates ADD-0005 may/may-not).

---

## 4) Evidence Query — freeze before Retrieval

Every future capability asks for evidence **the same way**. Writing, Reviewer, Compare, and Research Assistant submit an **Evidence Query** rather than custom retrieval logic.

This is the “SQL” of the Evidence Layer.

### Required query shape (v0 contract — freeze in Sprint 0 of 2.3)

```json
{
  "intent": "support_sentence | answer_question | review_coverage | compare_topic | …",
  "scope": {
    "user_id": 1,
    "project_id": 2,
    "file_ids": null,
    "document_id": null
  },
  "filters": {
    "status": ["accepted", "candidate"],
    "confidence_bands": ["high", "moderate", "low"],
    "study_types": [],
    "require_page_anchor": true
  },
  "ranking_strategy": "default_v0",
  "result_limit": 20,
  "query_text": "optional natural-language or sentence text",
  "anchors": {
    "block_id": null,
    "selected_text": null
  }
}
```

| Field | Purpose |
|-------|---------|
| `intent` | Why evidence is needed (routes presentation, not alternate stores) |
| `scope` | Tenant + project (+ optional files/document) |
| `filters` | Status, bands, study type, grounding requirements |
| `ranking_strategy` | Named, versioned ranker (Ranking stage owns interpretation) |
| `result_limit` | Cap |
| `query_text` / `anchors` | What to match; anchors preferred for Writing |

**Sprint 0 (Phase 2.3 kickoff):** publish final Evidence Query OpenAPI/fixture contract, then implement Retrieval against it.  
Do **not** start Retrieval code before that contract is checked into fixtures.

---

## 5) Implementation order (after RC)

1. Evidence Query contract freeze (Sprint 0)  
2. Evidence Retrieval  
3. Evidence Ranking  
4. Consensus Analysis  
5. Conflict Analysis  
6. Reasoning Pipeline  
7. Writing Intelligence integration (generation **last**)

Package guidance: grow under `backend/evidence/` or `backend/intelligence/` as **pipeline stages**, not five deployable services.

---

## 6) Explicit non-work before `v0.2.0-rc1`

No additional architectural ADDs/ADRs are required for RC.

Remaining work for RC:

1. Finish [`week2-rc-checklist.md`](week2-rc-checklist.md) (Postgres `0033` + ops smoke)  
2. Tag `v0.2.0-rc1`  
3. Close Phase 2.2  
4. Open Phase 2.3 at Evidence Query → Retrieval  

That sequencing keeps the platform stable while intelligence grows on a defined foundation.
