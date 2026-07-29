# Product Workflows

**Last updated:** 2026-07-29  
**Canonical strategy:** [PRODUCT_STRATEGY.md](PRODUCT_STRATEGY.md)  
**North star (now):** Evidence-backed **Literature Review** end-to-end — every paragraph traceable to EvidenceObjects.

Architecture stays boring. Ship **thin, complete researcher workflows**, not feature collections. Each workflow is a full loop: problem → evidence → draft → verify → export.

---

## Workflow status

| Workflow | Status |
|----------|--------|
| Evidence Platform | Frozen `v0.2.0-rc1` |
| Evidence Extraction Pipeline | Continuous quality |
| Research Intelligence core | Sprints 0–6 complete |
| Writing Intelligence modules | Planner / Context / Section Generator / Binder / Reviewer |
| **v0.2.1 Evidence-backed Literature Review** | **Current** — verify/export remaining |
| Other section types | Internal / experimental until later releases |
| Evidence Discovery | After Lit Review ships |
| Evaluation embedded | Grounding % · reviewer pass · edits-before-export |

---

## v0.2.1 — Evidence-backed Literature Review (current)

```text
Import papers → Extract → Accept evidence
  → Evidence Query
  → Writing Planner (literature_review)
  → Context Builder
  → Section Generator
  → Citation Binder
  → Reviewer
  → Verify every paragraph
  → Export
```

**In-scope:** Literature Review only.  
**Out of scope:** Discovery UI, Inspector 2.0, Critical Appraisal, Research Session persistence.  
**Success metric:** 80% of generated paragraphs exported without major edits.  
**Release criteria:** `RELEASE_CRITERIA.md`  
**Execution plan (Frozen):** [`docs/BETA_EXECUTION_PLAN_v0.2.1.md`](../docs/BETA_EXECUTION_PLAN_v0.2.1.md)  
**Validation (Active):** [`docs/RESEARCHER_VALIDATION_v0.2.1.md`](../docs/RESEARCHER_VALIDATION_v0.2.1.md)

---

## Later workflows (ordered)

| Release | Workflow | Success metric |
|---------|----------|----------------|
| v0.2.2 | Critical Appraisal | 2× faster vs manual |
| v0.2.3 | Research Gap Finder | Fewer iterations to actionable gaps |
| v0.2.4 | Clinical Decision Summary | — |
| v0.5.x | Evidence Discovery + Compare | — |
| v0.6.x → v1.0 | Publication workspace | — |

A workflow only opens when the previous one is measurable.

---

## Evaluation (every PR / release)

| Metric | Stage |
|--------|-------|
| Grounding % · citation coverage · unsupported rate | Writing |
| Reviewer pass rate | Reviewer |
| Edits before export | Product signal |
| Recall@k / MRR (when retrieval changes) | Retrieval / Ranking |

---

## Related

- [PRODUCT_STRATEGY.md](PRODUCT_STRATEGY.md)
- [ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md)
- [EXTRACTION_QUALITY_BACKLOG.md](EXTRACTION_QUALITY_BACKLOG.md)
- [`RELEASE_CRITERIA.md`](../RELEASE_CRITERIA.md)
