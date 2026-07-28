# Week 2 / Phase 2.2 — Release Decision (Evidence Layer)

Status: **RC tagged — Phase 2.2 closed**  
Milestone: Phase 2.2 Evidence Layer  
Release Candidate: **`v0.2.0-rc1`**  
Governing freeze: ADR-0005 + `week2-evidence-layer-platform-contracts.md`

---

## Decision summary

Architecture, backend, frontend, contracts, worker integration, Inspector, and
Stage 4 automated verification are complete.

**RC outcome (2026-07-28):**

1. PostgreSQL staging applied `migrations/0033_evidence_layer.sql` (plus pending 0026–0032)
2. Evidence tables verified present
3. Regression suite: **36 passed**
4. Staging smoke: extract → bind → accept → explain (`sufficient`) + cross-user IDOR 404 — **STAGING_SMOKE_OK**
5. Checklist complete: `week2-rc-checklist.md`
6. Git tag: **`v0.2.0-rc1`**

Phase **2.2 Evidence Platform is closed.**  
Phase **2.3 Research Intelligence is open** at Evidence Query → Retrieval (ADR-0006).

---

## Why Phase 2.2 is complete

- Architecture frozen (ADD + ADR-0003 + platform contracts ADR-0005)
- Backend slices BE-0…BE-E complete
- Frontend slices FE-0…FE-C complete
- Stage 4 automated gates green
- Staging migration + smoke green
- Platform contracts frozen: EvidenceObject, Explain, bindings, reviews, provenance, confidence bands

---

## Architectural shift (recorded)

| Before 2.2 | After 2.2 |
|------------|-----------|
| Document analysis, storage, writing surfaces | Reusable Evidence Layer with provenance, review, explainability, bindings |
| AI features attached ad hoc | Defined knowledge substrate for all future intelligence |

Transition: application with AI features → **platform with a knowledge substrate**.

---

## Residual non-blocking

| Item | Notes |
|------|-------|
| Re-measure perf on sustained Postgres load | Optional before GA `v0.2.0` |
| NVDA runtime a11y | Optional residual |
| Push tag to origin | Operator choice |

---

## Approval record

- Product / Engineering / QA: Muhammad  
- Architecture: Approved; staging migration + checklist complete  
- RC tag date: 2026-07-28  

### Phase 2.3 now open

Implementation order (one pipeline — not modules):

0. Freeze Evidence Query contract (Sprint 0)  
1. Evidence Retrieval  
2. Evidence Ranking  
3. Consensus Analysis  
4. Conflict Analysis  
5. Reasoning Pipeline  
6. Writing Intelligence integration (generation last)

Detail: `docs/architecture/phase-2.3-research-intelligence-pipeline.md` (ADR-0006).

### Phase 2.3 prohibitions (binding)

**May:** retrieve, rank, aggregate, consensus, conflict, explain reasoning.  

**May not:** read PDFs directly, bypass Evidence Layer, invent EvidenceObjects, mutate accepted evidence in place, parallel research-knowledge storage.  

**Never owns knowledge:** computes only over EvidenceObjects.
