# ENGINEERING_ROADMAP

**Last updated:** 2026-07-29  
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
| RI Writing productization (Wave A–D) | Extract UI · Grounded Generate · Inspector RI · naming/smoke docs |

Phase 2.0 validation **kit** remains frozen; researcher sessions gated by product ops, not missing kit docs.

---

## Current

| Track | Focus |
|-------|--------|
| **Milestone 1 — Research Writing** | **v0.2.1** — Sprints A–C done; **Researcher Validation Active** ([protocol](../docs/RESEARCHER_VALIDATION_v0.2.1.md): smoke → 5 → friction → 20) |
| **Platform discipline** | Freeze active — see [PLATFORM_FREEZE_v1.0.md](PLATFORM_FREEZE_v1.0.md) |
| **Evaluation (every PR)** | Name a metric improved (retrieval / ranking / consensus / writing) |
| **Evidence Extraction quality** | Continuous — [EXTRACTION_QUALITY_BACKLOG.md](EXTRACTION_QUALITY_BACKLOG.md) |
| **Ops hardening** | Verify live host checklist (migrations ≤0033, secrets, metrics) |
| **SaaS-PK (parallel)** | Plans / quotas / manual JazzCash-EasyPaisa — `docs/public-saas-readiness-pk.md` |

---

## Next

| Item | Notes |
|------|--------|
| **M1 Sprint 3** | Citation Binder · Reviewer · paragraph-level insert |
| **Milestone 2 — Evidence Discovery** | Search → cards → consensus/conflict → Inspector → jump into Writing |
| **Milestone 3 — Explainability** | Inspector full RI chain → generated paragraph |
| **Research Session** | Orchestration layer (query history, accepted evidence, draft links) — not a knowledge store |
| **Compare / Assistant** | Same EvidenceObject representation; no PDF-as-answer |

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
