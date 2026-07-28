# ENGINEERING_ROADMAP

**Last updated:** 2026-07-28  
**Canonical product writing sequence:** `docs/phase-2-writing-roadmap.md`  
**RI detail:** `docs/architecture/add-0005-research-intelligence-pipeline.md`

Keep this file scannable: **Completed · Current · Next · Later**. Historical week boards stay under `docs/architecture/`.

---

## Completed

| Milestone | Tag / marker |
|-----------|----------------|
| Platform & closed beta | Phase 0 |
| Library Bridge (Research OS hub) | Phase 1a–1c (2026-07-27) |
| Writing Studio Shell | **`v0.1.0`** (2026-07-28) |
| Writing Shell hardening | Week 1.1 |
| Evidence Platform | **`v0.2.0-rc1`** — Phase 2.2 **CLOSED**, contracts frozen |
| Research Intelligence core pipeline | Phase 2.3 Sprints **0–6** |
| | Query → Retrieval → Ranking → Consensus → Conflict → Reasoning → Writing Intelligence |

Phase 2.0 validation **kit** remains frozen; researcher sessions gated by product ops, not missing kit docs.

---

## Current

| Track | Focus |
|-------|--------|
| **RI productization** | Surface Evidence / reason / writing APIs in Writing Studio UX |
| **Ops hardening** | Verify live host checklist (migrations ≤0033, secrets, metrics) |
| **SaaS-PK (parallel)** | Plans / quotas / manual JazzCash-EasyPaisa — `docs/public-saas-readiness-pk.md` |
| **Stabilization** | Keep Evidence contracts frozen; no dual knowledge stores |

---

## Next

| Item | Notes |
|------|--------|
| **Research Reviewer** | Compiler-shaped: search → coverage → support checks → warnings (ADD Month 8) |
| **Compare consistency** | Same EvidenceObject representation for papers/methods/findings |
| **Research Assistant** | Question → Evidence Query → … → Reasoning → Answer (no PDF-as-answer) |
| **Citation insert into draft** | Connect existing citation manager; don’t rebuild |

---

## Later

| Item | Notes |
|------|--------|
| Publication engine | Journal rules, reporting guidelines |
| Broader public multi-tenant launch | After SaaS-PK + security/ops bar |
| Vector / ANN retrieval | Implementation detail behind Retrieval — not a second knowledge store |
| Optional LLM narration over Writing Intelligence | Must remain **gated** by RI sufficiency; never invent EvidenceObjects |

---

## Sequencing rules (frozen)

1. Evidence before guided AI (2.2 before freeform writing AI).  
2. Intelligence before generation (2.3 before treating Phase 2.4 as “done”).  
3. Generation last in the pipeline.  
4. No rewrites of working Importer / StorageProvider / worker HANDLERS without ADR.  
5. Platform contracts append-only.

---

## Related

- [PROJECT_STATUS.md](PROJECT_STATUS.md)  
- [FEATURE_MATRIX.md](FEATURE_MATRIX.md)  
- `docs/architecture/week2-evidence-layer-implementation-board.md`
