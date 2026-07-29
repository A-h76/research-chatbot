# PRODUCT_DECISIONS

Purpose: product equivalent of ADRs.  
Rule: each major product decision records the researcher problem, evidence, one success metric, and what is deliberately postponed.

Status lifecycle: **Proposed → Accepted → Shipped → Superseded → Retired**.

---

## PD-0001 — v0.2.1 target workflow

- **Date:** 2026-07-29
- **Status:** Accepted
- **Owner:** Product

## Decision

First public workflow is **Evidence-backed Literature Review**.

### Problem
Researchers need a trustworthy way to move from evidence to draft without jumping across disconnected tools.

### Evidence
- Literature review drafting is a high-frequency researcher workflow.
- Existing Dhund architecture already supports this flow end-to-end.
- Current bottleneck is trust + verification UX, not missing core architecture.

### Why this workflow?
It uses existing Dhund foundations end-to-end and solves a high-value pain point with one complete vertical.

### Why now?
Core platform + RI stages are already built; the bottleneck is productizing one complete researcher outcome.

### Success metric
80% of generated paragraphs are exported without major edits.

### Impact
Engineering
- Prioritize Citation Binder, Reviewer, verify/export path for v0.2.1.

UX
- Literature Review is the default polished writing surface; other section types remain experimental.

Positioning
- External promise centered on trustworthy evidence-backed literature reviews.

Documentation
- Roadmap and milestones align to thin vertical slices.

### Deliberately postponed
- Evidence Discovery product surface
- Inspector 2.0 full chain UX
- Critical Appraisal workflow
- Research Session persistence layer

### Related
- `docs/adr/0005-freeze-evidence-layer-platform-contracts.md`
- `docs/adr/0006-research-intelligence-staged-pipeline.md`
- `Dhund-Flow/PRODUCT_STRATEGY.md`
- `Dhund-Flow/ENGINEERING_ROADMAP.md`

---

## Template

```markdown
## PD-XXXX — <Decision title>

- Date:
- Status: Proposed | Accepted | Shipped | Superseded | Retired
- Owner:

## Decision

### Problem

### Evidence

### Why this workflow?

### Why now?

### Success metric

### Impact

### Deliberately postponed

### Related
- ADR-XXXX
- ROADMAP
- PRODUCT_STRATEGY
```
