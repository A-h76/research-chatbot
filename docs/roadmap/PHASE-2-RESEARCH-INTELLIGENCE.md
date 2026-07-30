# Phase 2 — Research Intelligence

**Status:** **COMPLETE / FROZEN** (Research Intelligence v3.0)  
**Date:** 2026-07-30  
**Freeze pack:** [`docs/contracts/RI-v3.0-COMPLETE-FREEZE.md`](../contracts/RI-v3.0-COMPLETE-FREEZE.md)  
**Rule:** Make Dhund **smarter**, not prettier, and not more “AI.”  
**Platform gate:** A-401–A-405 complete (`contracts_version` 1.2.0). Architecture evolves **only when product demands it**.

> **Next chapter:** Dual-track execution — [`EXECUTION-DUAL-TRACK.md`](./EXECUTION-DUAL-TRACK.md).  
> **Phase A approved:** Writing MVP + evidence accept gate + citation export + single truth path.  
> Track 2 (Memory / KG v2 / Novelty) only after usage. RI allows bugfixes/perf/quality only.

---

## Milestone (north star)

> **Dhund becomes irreplaceable when researchers stop thinking of it as “an AI writing tool” and start thinking of it as “the place where my research lives.”**

Foundation made that possible. Phase 2 must make it true.

---

## Capability map (company roadmap)

Organize work by **capabilities**, not backend/frontend ownership.

| # | Capability | Progress (indicative) | Phase 2 focus |
|---|------------|----------------------|---------------|
| 1 | **Knowledge Acquisition** | ██████████ | Maintain (library, DU, extract) |
| 2 | **Evidence Intelligence** | ████████░░ | Harden (objects, bindings, ranking) |
| 3 | **Research Intelligence** | ██████████ | **Done / frozen** (v3.0) |
| 4 | **Writing Intelligence** | █████░░░░░ | **Primary focus** — RI-009 bridge shipped; MVP next |
| 5 | **Research Workspace** | ██░░░░░░░░ | Project memory, workflows, UX |
| 6 | **Publication Intelligence** | █░░░░░░░░░ | Later (export / journal packs) |

```text
Knowledge Acquisition ██████████
Evidence Intelligence ████████░░
Research Intelligence ██░░░░░░░░   ← Phase 2
Writing Intelligence  ███░░░░░░░
Research Workspace    ██░░░░░░░░
Publication           █░░░░░░░░░
```

---

## Effort allocation (next ~6 months)

| Share | Area |
|------:|------|
| **60%** | Research Intelligence (themes, matrix, consensus, contradictions, gaps, KG, timeline, methodology) |
| **20%** | Research Workspace (project memory, collaboration, researcher experience) |
| **10%** | Writing Intelligence (grounded drafting, reviewer, citations) — *after* RI strength |
| **10%** | Platform & Operations (performance, scaling, observability, reliability) |

**Explicitly out of budget:** another large architecture refactor. Clean-ups only when a capability cannot ship without them (ADR required).

---

## What already exists (do not rebuild)

Phase 2 **extends** frozen Evidence/RI substrate:

| Substrate | Status |
|-----------|--------|
| EvidenceObject + extract + review | Shipped |
| Retrieve → Rank → Consensus → Conflict → Reason → Writing | Shipped APIs |
| Ranking strategies + consensus/conflict metrics | A-403 |
| Reviewer persistence + job observability | A-401 / A-404 |
| Contracts freeze | A-402 / A-405 |

New RI capabilities must consume **EvidenceObjects via EvidenceQuery** — never raw PDFs as a second knowledge root (ADR-0003).

---

## RI ticket map (Phase 2)

### RI-001 — Theme Discovery ✅

| | |
|--|--|
| **Input** | Project corpus (target: ~200 papers / EvidenceObjects) |
| **Output** | Named themes (Theme A–D…) with supporting evidence ids |
| **Product** | Automatic clustering / labeling researchers do by hand |
| **Depends on** | Evidence list + retrieve/rank |
| **DoD** | Deterministic or versioned theme run; reconstructable; no invented papers |
| **Status** | Shipped — `GET .../evidence/themes` (`token_jaccard_v1` + `input_hash`); Themes tab |

### RI-002 — Evidence Matrix ✅

| | |
|--|--|
| **Output** | Table: Paper \| Method \| Dataset \| Findings \| Limitations |
| **Product** | Replaces manual lit-review matrices |
| **Depends on** | EvidenceObjects + optional DU metadata |
| **DoD** | Exportable matrix; every cell cites evidence or marks unknown |
| **Status** | Shipped — `GET .../evidence/matrix` (+ md/csv); Compare page Matrix tab |

### RI-003 — Consensus Engine (product depth) ✅

| | |
|--|--|
| **Not** | “Summarize these papers.” |
| **Instead** | Stance labels: **Agree / Disagree / Mixed / Weak evidence** |
| **Depends on** | Existing `POST /api/evidence/consensus` (+ metrics) |
| **DoD** | Researcher-facing labels + Explain path; Compare UI (EPIC-0006 B-611) |
| **Status** | Shipped — `product_label` on consensus; Compare + Inspector strips |

### RI-004 — Contradiction Engine (product depth) ✅

| | |
|--|--|
| **Not** | “Paper A disagrees.” |
| **Instead** | **Why** — sample, methodology, outcome, statistics (mediators) |
| **Depends on** | Existing conflict mediators (+ A-403 catalog) |
| **DoD** | WHY panels for each conflict link; unexplained pairs surfaced |
| **Status** | Shipped — link `why` / `mediator_explanations` / `statistics_differs`; UI strip |

### RI-005 — Knowledge Graph ✅

| | |
|--|--|
| **Role** | Dhund’s connected brain (papers ↔ evidence ↔ themes ↔ gaps) |
| **Depends on** | EvidenceObjects; per-doc KG may seed |
| **DoD** | Project-level graph over Evidence — not a parallel knowledge DB without ADR |
| **Status** | Shipped — `GET .../evidence/graph`; Graph tab (papers/evidence/themes + conflict edges) |

### RI-006 — Research Gap Engine ✅

| | |
|--|--|
| **Example** | “Most work studies adults. Little on adolescents.” |
| **Depends on** | Themes + matrix + consensus coverage |
| **DoD** | Gaps with evidence density + suggested questions; never invent literature |
| **Status** | Shipped — `GET .../evidence/gaps`; Gaps tab (coverage / thin theme / matrix / conflict) |

### RI-007 — Research Timeline ✅

| | |
|--|--|
| **Output** | Evolution of a topic over years |
| **Depends on** | Paper years + evidence themes |
| **DoD** | Timeline view with paper/evidence anchors |
| **Status** | Shipped — `GET .../evidence/timeline`; Timeline tab |

### RI-008 — Methodology Intelligence ✅

| | |
|--|--|
| **Suggest** | Study design, variables, datasets, statistical tests, threats to validity |
| **Tone** | Research support — not imperative “commands” |
| **Depends on** | Matrix + gap + consensus |
| **DoD** | Advisory cards grounded in project evidence |
| **Status** | Shipped — `GET .../evidence/methodology`; Methods tab |

### RI-009 — Writing Intelligence v2 ✅

| | |
|--|--|
| **When** | After RI-001–008 have credible depth |
| **Why** | Writing improves because intelligence is strong — not because we polish prose first |
| **Depends on** | Grounded writing path + Reviewer + themes/matrix/gaps |
| **DoD** | Section drafts that consume themes/consensus/gaps; reviewer still Evidence-first |
| **Status** | Shipped — `writing_version` 2.0.0 / `grounded_v1` + `ri_context`; gap/theme-aware sections |

---

## Suggested build order

```text
RI-003 / RI-004 productize (consensus + contradiction WHY)
        ↓
RI-002 Evidence Matrix
        ↓
RI-001 Theme Discovery
        ↓
RI-006 Gaps  ←── RI-005 Knowledge Graph (incremental)
        ↓
RI-007 Timeline · RI-008 Methodology
        ↓
RI-009 Writing Intelligence v2
```

Productize **existing** consensus/conflict APIs first (fastest path to “smarter” UX), then matrix/themes, then gaps/KG, then writing v2.

---

## Workspace & writing (secondary)

| Share | Work |
|------:|------|
| 20% | Research Workspace — project memory, workflows, researcher experience ([EPIC-0003](../epics/EPIC-0003-Research-Workspace.md)) |
| 10% | Writing Intelligence — grounded drafting, reviewer UI, citations ([EPIC-0004](../epics/EPIC-0004-Writing-Engine.md), [EPIC-0005](../epics/EPIC-0005-Reviewer.md)) |

---

## Architecture policy (Phase 2)

1. **Good enough.** No six-month polish campaigns.  
2. **Evolve on demand.** New tables/APIs when a RI ticket needs them; ADR for new roots or queue rewrites.  
3. **Contracts first.** Extend `docs/contracts/` additively; bump `contracts_version`.  
4. **Evidence first.** Intelligence organizes and explains; it does not invent EvidenceObjects.

---

## Exit criteria (Phase 2 chapter)

- [x] Researchers can see themes, matrix, consensus, and contradiction **WHYs** on a real project corpus  
- [x] At least one gap insight is reconstructable from EvidenceObjects  
- [x] KG or timeline ships without a parallel knowledge root  
- [x] Writing v2 consumes RI outputs  
- [ ] Milestone language shifts: product marketed as **where research lives**, not an AI writer  

---

## Related docs

- Living contracts: [`docs/contracts/`](../contracts/README.md)  
- Stage APIs: [EPIC-0006](../epics/EPIC-0006-Research-Intelligence.md)  
- Future extensions: [IDD-0010](../idd/IDD-0010-Future-Extensions.md)  
- Foundation freeze: [A-405](../contracts/A-405-documentation-freeze.md)
