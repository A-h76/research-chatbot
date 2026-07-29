# Dhund product strategy — Cursor at the research layer

**Last updated:** 2026-07-29  
**Positioning (Phase 1):** The fastest way to produce **evidence-backed literature reviews and critical appraisals** — not “another Scholar” or “another ChatGPT.”

Cursor used a mature foundation (VS Code) and made AI-assisted coding dramatically better. Dhund already has its foundation (Import → Analysis → Extraction → Evidence Platform → RI). **Do not rewrite it.** Ship thin, complete researcher workflows one at a time.

---

## Compare: what we built vs this strategy

| We recently shipped | Fits strategy? | Gap |
|---------------------|----------------|-----|
| Foundation frozen + RI stages 0–6 | ✅ Phase 2 (already done) | Keep incremental only |
| Extract UI → accept → evidence-backed generate | ✅ Loop input | Needed for any vertical |
| Planner / Context / Section Generator | ✅ Partial v0.2.1 | Needed, not sufficient alone |
| Many `section_type`s in UI | ⚠️ Too broad early | Keep code; **ship/polish Lit Review only** |
| Writing `metrics` object | ✅ Phase 4 start | Add **edits-before-export** |
| Citation Binder / Reviewer / Export verify | ❌ Missing for v0.2.1 | **Do next** |
| Evidence Discovery / Inspector 2.0 / Research Session | Later | After Lit Review vertical ships |

**Verdict:** Architecture work is ahead of the *complete* Literature Review workflow. Next investment is finishing **one vertical slice**, not more subsystems.

---

## The Dhund Loop (wall copy)

```text
Find one researcher pain point
  → Build the smallest evidence-backed workflow
  → Ship it
  → Measure quality
  → Collect researcher feedback
  → Improve Retrieval / Reasoning / Writing
  → Ship again
  → Repeat
```

Missing from the loop (on purpose): new knowledge layers, model-first rewrites, architecture redesigns.

---

## Thin vertical releases

| Release | Researcher outcome (only) |
|---------||---------------------------|
| **v0.2.1** | Evidence-backed Literature Review (Query → Planner → Binder → Reviewer → Verify → Export) |
| **v0.2.2** | Critical Appraisal (risk of bias / evidence level) |
| **v0.2.3** | Research Gap Finder |
| **v0.2.4** | Clinical Decision Summary |
| **v0.3.x** | Reviewer depth + appraisal polish |
| **v0.4.x** | Research Gap as productized discovery |
| **v0.5.x** | Evidence Discovery & Compare |
| **v0.6.x** | Publication workflow (draft → review → export) |
| **v1.0** | End-to-end evidence-centric research workspace |

Other `section_type` machinery may exist internally; **only Lit Review is first-class until v0.2.1 ships.**

---

## Evaluation culture (every Lit Review release)

| Metric | Why |
|--------|-----|
| Grounding % | Paragraphs linked to EvidenceObjects |
| Citation coverage | Supporting corpus actually cited |
| Reviewer pass rate | Compiler checks clear |
| **User edits before export** | If they rewrite heavily, improve grounding/ranking/writing |

---

## Single Success Metric Rule

Each release declares exactly one primary success metric before implementation.

- **v0.2.1 Evidence-backed Literature Review:** 80% of generated paragraphs exported without major edits.
- **v0.2.2 Critical Appraisal:** appraisal completed 2x faster vs manual baseline.
- **v0.2.3 Research Gap Finder:** actionable gaps identified in fewer iterations.

Secondary metrics are diagnostic and cannot replace the release north-star metric.

---

## What to do now (ordered)

1. **Finish v0.2.1 Lit Review vertical** — Citation Binder + Reviewer + verify-every-paragraph UX + export path.
2. **Default product surface to Literature Review** — other section types labeled experimental.
3. **Instrument edits-before-export** beside existing writing metrics.
4. **Defer** Discovery / Inspector 2.0 / multi-workflow marketing until Lit Review loop closes.

---

## Readiness Gate Before Building

Before major feature work starts, all five checks must be true:

1. A **PD** defines the researcher problem and workflow outcome.
2. Existing **ADR(s)** support the implementation path.
3. The item appears in `ENGINEERING_ROADMAP.md`.
4. One primary success metric is defined.
5. Telemetry can validate the metric after release.

If any check is missing, the work is not ready.

---

## Related

- [PRODUCT_CAPABILITY_MILESTONES.md](PRODUCT_CAPABILITY_MILESTONES.md)  
- [ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md)  
- [EXTRACTION_QUALITY_BACKLOG.md](EXTRACTION_QUALITY_BACKLOG.md)
