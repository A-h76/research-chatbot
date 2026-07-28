# Week 2 Evidence Layer Implementation Board

Status: **Phase 2.2 CLOSED** — RC `v0.2.0-rc1` tagged  
Next: **Phase 2.3 OPEN** — Evidence Query → Retrieval  
Release decision: [`week2-release-decision.md`](week2-release-decision.md)  
Platform contracts: [`week2-evidence-layer-platform-contracts.md`](week2-evidence-layer-platform-contracts.md) (ADR-0005)  
RI pipeline: [`phase-2.3-research-intelligence-pipeline.md`](phase-2.3-research-intelligence-pipeline.md) (ADR-0006)

---

## Maturity

| Area | Status |
|------|--------|
| Architecture | Complete + contracts frozen |
| Backend | Complete |
| Frontend | Complete |
| Contracts | Frozen (ADR-0005) |
| Stage 4 | GO |
| Postgres staging `0033` | Applied |
| Staging smoke | STAGING_SMOKE_OK |
| RC | **`v0.2.0-rc1` tagged** |
| Phase 2.2 | **Closed** |
| Phase 2.3 | **Open** (Sprint 0) |

---

## Phase 2.2 (closed)

- [x] Design + BE/FE slices + Stage 4 + contract freeze  
- [x] RC checklist  
- [x] Tag `v0.2.0-rc1`  
- [x] Close Phase 2.2  

---

## Phase 2.3 — Research Intelligence (open)

| Sprint | Status |
|--------|--------|
| 0 — Evidence Query contract freeze | **Done** (ADR-0007) |
| 1 — Evidence Retrieval | **Done** (`/api/evidence/search`, `/retrieve`) |
| 2 — Evidence Ranking | **Done** (`/api/evidence/rank`, `default_v0`) |
| 3 — Consensus Analysis | **Done** (`/api/evidence/consensus`) |
| 4 — Conflict Analysis | **Done** (`/api/evidence/conflict`) |
| 5 — Reasoning Pipeline | **Done** (`/api/evidence/reason`) |
| 6 — Writing Intelligence integration | **Done** (`/api/evidence/writing`, `grounded_v0`) |

Contract: [`phase-2.3-evidence-query-contract.md`](phase-2.3-evidence-query-contract.md)  
**One pipeline, not modules.** RI never owns knowledge. Evidence Platform (`v0.2.0-rc1`) stays frozen.
Phase 2.3 core pipeline sprints **0–6 complete**. Next product surfaces: Reviewer / Compare / Assistant (ADD-0005 months 8+).

### RI prohibitions

May not: read PDFs directly, bypass Evidence Layer, invent EvidenceObjects, mutate accepted evidence, parallel research-knowledge storage.
