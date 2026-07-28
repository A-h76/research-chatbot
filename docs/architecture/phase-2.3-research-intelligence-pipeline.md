# Phase 2.3 — Research Intelligence Pipeline (design freeze for kickoff)

Status: **Active** — Phase 2.3 open after `v0.2.0-rc1`; Sprint 0 Evidence Query **frozen** (ADR-0007)  
Depends on: Evidence Layer platform contracts (ADR-0005), ADD-0005, ADR-0004, ADR-0006, ADR-0007  
Audience: Staff / principal engineers implementing Phase 2.3

---

## 0) Sprint status

| Sprint | Item | Status |
|--------|------|--------|
| 0 | Evidence Query contract | **Frozen** — `phase-2.3-evidence-query-contract.md` |
| 1 | Evidence Retrieval | **Done** — `phase-2.3-evidence-retrieval.md` |
| 2 | Evidence Ranking | **Done** — `phase-2.3-evidence-ranking.md` |
| 3 | Consensus Analysis | **Done** — `phase-2.3-evidence-consensus.md` |
| 4–6 | Conflict → … → Writing Intelligence | Planned |

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

## 4) Evidence Query — frozen (Sprint 0 complete)

Canonical contract: [`phase-2.3-evidence-query-contract.md`](phase-2.3-evidence-query-contract.md) (ADR-0007).

Minimal platform fields:

```text
intent | scope | filters | ranking_strategy | result_limit
```

Optional: `query_text`, `anchors`.  
**Not** in contract: prompt, model, temperature, embeddings, vector_index.

Fixture: `tests/fixtures/evidence/evidence_query_v0.json`.  
Normalizer: `backend/evidence/query.py`.

**Sprint 1:** Retrieval implements this contract — does not redefine it.

---

## 5) Implementation order

1. ~~Evidence Query contract freeze (Sprint 0)~~ **Done**  
2. ~~Evidence Retrieval~~ **Done** (`phase-2.3-evidence-retrieval.md`)  
3. ~~Evidence Ranking~~ **Done** (`phase-2.3-evidence-ranking.md`)  
4. ~~Consensus Analysis~~ **Done** (`phase-2.3-evidence-consensus.md`)  
5. Conflict Analysis  
6. Reasoning Pipeline  
7. Writing Intelligence integration (generation **last**)

Package guidance: grow under `backend/evidence/` or `backend/intelligence/` as **pipeline stages**, not five deployable services.

---

## 6) Platform freeze reminder

Evidence Platform (`v0.2.0-rc1`) remains frozen (ADR-0005). Phase 2.3 computes over EvidenceObjects; it does not reopen Phase 2.2 architecture.
