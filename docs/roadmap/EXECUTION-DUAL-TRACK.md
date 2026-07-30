# Dhund Execution Roadmap — Dual Track

**Status:** **Canonical execution plan** through Private Alpha  
**Date:** 2026-07-30  
**RI:** Frozen at v3.0 — see [`docs/contracts/RI-v3.0-COMPLETE-FREEZE.md`](../contracts/RI-v3.0-COMPLETE-FREEZE.md)

> The next stage of Dhund is no longer about proving the intelligence.  
> It's about proving that researchers can successfully complete their work using it.

Architecture audit scores live only in the RI Engine Audit canvas. **They are not roadmap KPIs.** They must not appear in execution progress reporting.

---

## Principle

Biggest unknown today:

> Will researchers actually use Dhund to complete a literature review?

Not:

> Can we build KG v2?

**Freeze RI. Ship Writing. Validate with researchers. Let usage choose platform depth.**

---

## Tracks

### Track 1 — Product (now)

```text
Dashboard → Projects → Evidence → Analysis → Writing → Reviewer → Export
```

**Goal:** A researcher completes an end-to-end literature review in Dhund.

Within Track 1, UX is continuous:

```text
Product → UX → Validation → Iteration
```

Every researcher session produces friction points, confusion, navigation problems, and terminology issues. Those become the next sprint backlog. At this stage, the biggest improvements are likely usability—not new algorithms.

### Track 2 — Platform (later)

Only after usage:

```text
Research Memory → KG v2 → Structured datasets/methods → Novelty → Semantic retrieval
```

Deepens the platform after learning from users. No hard schedule until alpha evidence.

---

## Phases

```text
Phase A (ship)
      ↓
Private Alpha
      ↓
Product Success Gate
      ↓
Phase B (E2E hardening / iteration from alpha)
      ↓
Phases C–E (usage-gated platform)
```

| Phase | Goal | Primary KPI | Commitment |
|-------|------|-------------|------------|
| **A** | Writing Intelligence MVP + accepted evidence workflow + citation export + single evidence truth path | Researchers can produce an evidence-grounded draft | **APPROVED — ship now** |
| **Alpha** | Private Alpha + Product Success Gate | Exit criteria below met | **Required before Phase B** |
| **B** | End-to-end product hardening from alpha feedback | Literature review completes in-product without help (DoD below) | Only after Success Gate |
| **C** | Research Memory + writing continuity | Returning projects retain useful context | Gated on multi-draft usage |
| **D** | KG v2 + structured entities (methods, datasets, topics) | Richer exploration if demand justifies | ADR + researcher demand quotes |
| **E** | Novelty + semantic retrieval | Only if validated by alpha feedback | Do not schedule early |

### Phase A deliverables (exact)

1. Writing Intelligence MVP (generate → bind → revise → export)
2. Accepted-evidence gate (drafts require accepted EvidenceObjects)
3. Citation / bibliography export from bindings
4. Single evidence-based truth path (Evidence RI is primary for Compare/Gaps; no dual LLM PaperAnalysis root)

---

## Private Alpha — Product Success Gate

Do **not** automatically enter Phase B when Phase A code ships. Run Private Alpha and pass this gate first:

| # | Exit criterion |
|---|----------------|
| 1 | 10 researchers onboarded |
| 2 | 5 completed literature reviews (see Definition of Done) |
| 3 | ≥80% finish without developer help |
| 4 | ≥1 exported manuscript |
| 5 | Top 10 UX issues documented (feeds Track 1 UX backlog) |

---

## Definition of Done — Literature Review Complete

A literature review is **complete** when a researcher can finish this path **inside Dhund**:

```text
Create project
      ↓
Upload papers
      ↓
Review extracted evidence
      ↓
Accept evidence
      ↓
Explore themes
      ↓
Understand consensus
      ↓
Review conflicts
      ↓
Identify research gaps
      ↓
Generate outline
      ↓
Write literature review
      ↓
Run reviewer
      ↓
Export document
```

**Without:**

- terminal
- admin tools
- database edits
- manual developer intervention

This path is the product acceptance test for Phase B.

---

## Concrete milestones (track these)

1. Writing MVP shipped  
2. Evidence acceptance workflow shipped  
3. Research workflow completed (Definition of Done path)  
4. 10 researchers onboarded  
5. First successful literature review in Dhund  
6. First exported paper (grounded + citations)  
7. Private Alpha Success Gate passed  
8. Top 10 UX issues backlog opened and triaged  

---

## KG v2 caution

Start Phase D only if researchers say things like:

- “I can’t see relationships between methods.”
- “I wish datasets were connected.”
- “I need author-level exploration.”

Otherwise project KG v1 may be sufficient much longer.

---

## Exit Criteria for Productization

Dhund reaches **Product Validation** when:

- Research Intelligence remains frozen.
- Writing Intelligence MVP is production ready.
- End-to-end workflow completes inside Dhund (Definition of Done).
- Researchers no longer need external tools for a first literature review draft.
- Feedback from real researchers—not internal architecture goals—determines the next platform investment.

---

## Related

- Freeze: [`docs/contracts/RI-v3.0-COMPLETE-FREEZE.md`](../contracts/RI-v3.0-COMPLETE-FREEZE.md)
- Phase 2 (historical RI chapter): [`PHASE-2-RESEARCH-INTELLIGENCE.md`](./PHASE-2-RESEARCH-INTELLIGENCE.md)
- Canvas: `Dhund-Execution-Roadmap`
- Architecture audit only (not execution KPIs): canvas `RI-Engine-Audit`
