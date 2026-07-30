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
Phase A
  Engineering Complete
  Awaiting Product Validation
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
| **A** | First end-to-end researcher workflow (not “build Writing alone”) | Unassisted path: upload → accept evidence (as decisions) → grounded draft → revise → export | **Engineering Complete — awaiting Private Alpha validation** |
| **Alpha** | Private Alpha + Product Success Gate | Exit criteria below met | **Required before Phase B** |
| **B** | End-to-end product hardening from alpha feedback | Literature review completes in-product without help (DoD below) | Only after Success Gate |
| **C** | Research Memory + writing continuity | Returning projects retain useful context | Gated on multi-draft usage |
| **D** | KG v2 + structured entities (methods, datasets, topics) | Richer exploration if demand justifies | ADR + researcher demand quotes |
| **E** | Novelty + semantic retrieval | Only if validated by alpha feedback | Do not schedule early |

### Phase A — complete the first end-to-end researcher workflow

**Framing:** Do not think of Phase A as “building Writing.” Think of it as making this sentence true:

> A researcher can go from uploaded papers to an evidence-backed draft and export entirely within Dhund.

**Single truth path (required):**

```text
Papers → Evidence Objects → Accepted Evidence (decisions) → Analysis → Writing → Reviewer → Export
```

No second reasoning pipeline (no parallel LLM PaperAnalysis compare/gaps as primary).

#### Deliverables (implementation order — do not reorder)

1. **Writing MVP loop** (highest priority) — Project → Evidence → Generate Draft → Revise → Save (prove the workflow first; gate may be temporary initially)
2. **Research Decision model** — persist every interaction as project memory:
   - `id`, `project_id`, `evidence_id`, `type` (`ACCEPT` | `REJECT` | `IMPORTANT` | `OPEN_QUESTION` | `SUPPORT` | `CONTRADICT`), `timestamp`, `reason` (optional), `user_id`
   - Principle: decisions become permanent research memory
3. **Accepted-evidence gate** — draft context = accepted evidence only (candidates never silently influence drafts)
4. **Citation export** — Paragraph → Evidence → Paper → Citation → Export
5. **Single truth path** — retire parallel LLM PaperAnalysis compare/gaps as primary; one Evidence → Decisions → Analysis → Writing → Export chain
6. **Instrumentation** — ship with Phase A (not after): project created, papers uploaded, evidence extracted, accept/reject, draft generated/regenerated, reviewer opened, export completed, workflow abandoned

#### Phase A Definition of Done (refuse to close until all pass)

- Researcher creates a project
- Uploads papers
- Reviews extracted evidence
- Accepts/rejects evidence (as Research Decisions)
- Generates an evidence-grounded draft
- Revises the draft
- Exports with citations
- Completes the workflow without developer assistance
- Instrumentation captures the key workflow events

**Phase A status (2026-07-30):**

```text
Phase A
  Engineering Complete
  Awaiting Product Validation
```

Deliverables 1–6 are implemented in code. Phase A itself is **not** closed until an unassisted researcher path succeeds and Private Alpha + Success Gate pass. Do not start Phase B from this commit alone.

**Scope lock:** No new RI capabilities, KG expansion, or novelty until Private Alpha validates the need.  
**Not doing:** Decision Dashboard, Decision Analytics, Decision Graph — decisions accumulate quietly.

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
