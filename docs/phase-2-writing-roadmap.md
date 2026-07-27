# Dhund v2 — Phase 2 Roadmap (Frozen)

**Status:** Frozen (revised 2026-07-27)  
**Companions:** [`soro-vs-jenni-roadmap.md`](./soro-vs-jenni-roadmap.md) · [`public-saas-readiness-pk.md`](./public-saas-readiness-pk.md) · [`phase-2.0-research-validation.md`](./phase-2.0-research-validation.md)

Two goals, different timing:

1. **Build the strongest first impression** → Writing Shell + Evidence before loud marketing.  
2. **Learn whether people want it** → Invite researchers once that story is visible — not after every Phase 2 feature.

---

## Positioning

Dhund is a **Research Operating System** whose publication surface helps researchers produce **defensible, evidence-backed manuscripts** — not another AI writing assistant.

**Core story (minimum launchable differentiator):**

> Import research → Analyse → Compare → Write with evidence.

**Design principle (non-negotiable):**

> Every AI action in the Writing Studio must answer: *“What evidence is this based on?”*  
> If the system cannot answer, do not present the output as research-backed.

Existing `/writing` is a **rewrite target**, not the foundation.

---

## Balanced sequence (canonical)

```text
Phase 1 ✅ Research OS (Library Bridge)

↓  parallel tracks

Public SaaS readiness (PK)     Phase 2.0 validation kit ✅
plans · quotas · JazzCash      protocol · logs · tracker
manual · deploy · monitoring   (tooling frozen — don't expand)

↓

Phase 2.1  Writing Studio Shell (no AI)

↓

Phase 2.2  Evidence Layer ⭐

↓

Invite 5–10 researchers  ← first external users on the full story
(Library + Write-with-evidence)

↓

Fix critical issues

↓

Soft launch (Founding Student / JazzCash)

↓

Phase 2.3–2.5  grow with feedback
(Citations polish · Guided gen · Reviewer)

↓

Broader public launch
```

### Extremes we reject

| Extreme | Why not |
|---------|---------|
| Launch / market loudly **today** | Writing/evidence missing → weak first impression |
| Build through **2.5 + Teams + full PSP** in isolation | 6–9 months of assumptions, no external signal |

---

## Roadmap overview

| Phase | Name | Status |
|-------|------|--------|
| 0 | Platform & Closed Beta | ✅ Complete |
| 1 | Research Operating System | ✅ Complete |
| **SaaS-PK** | Public readiness (plans, quotas, manual JazzCash/EasyPaisa, deploy, monitoring) | ⬜ Next (parallel with 2.1) |
| **2.0** | Validation **kit** | ✅ Tooling complete · sessions **after 2.2** |
| **2.1** | Writing Studio Shell | ⬜ Next |
| **2.2** | Evidence Layer ⭐ | Planned (after 2.1) |
| **2.0 sessions** | Invite 5–10 researchers | After 2.2 exists |
| Soft launch | Founding cohort | After session fixes |
| 2.3 | Citation Layer (consume existing) | With / after soft launch feedback |
| 2.4 | Guided / context-aware generation | After Evidence; never before |
| 2.5 | Research Reviewer | Last |
| — | Broader public launch | After soft launch learnings |

Do **not** build AI text generation (2.4) before the Evidence Layer (2.2).

---

## Phase SaaS-PK — Public readiness (parallel)

See [`public-saas-readiness-pk.md`](./public-saas-readiness-pk.md).

For ~100 users in Pakistan: plans + entitlements + **manual** JazzCash/EasyPaisa confirm — not Stripe. Automate merchant APIs when confirms become a weekly burden.

Can proceed **in parallel** with 2.1/2.2 so Founding checkout works at soft launch.

---

## Phase 2.0 — Research Validation

**Kit:** complete (`phase-2.0-*.md`). **Do not expand tooling.**

**Sessions:** run **after Phase 2.2**, so researchers evaluate:

> Import → Analyse → Compare → Write with evidence

Not only Library in isolation.

**Invite:** 5–10 (PhD / Masters / RA / Professor).  
**Task:** Complete a literature-review workflow **including drafting with evidence** where possible.

**Still watch:** Research Ready, PDF attach, Compare, duplicates, write-in-app desire, contradiction trust.

**Exit before soft launch:** Critical friction fixed or explicitly deferred.

---

## Phase 2.1 — Writing Studio Shell

Intentionally small. **No AI.**

| Build | Notes |
|-------|--------|
| Project documents | Scoped to project |
| Document list | Home for drafts |
| Auto-save | Reliable enough to leave Word |
| Version history | Lightweight |
| Markdown / rich text | Enough to write; polish later |

**Goal:** Researchers can write *inside* Dhund instead of exporting immediately to Word.

---

## Phase 2.2 — Evidence Layer ⭐

Heart of the product. Completes the launch story.

```
Paragraph → Claim → Supporting evidence → Contradicting evidence → Confidence
```

Reuse Paper Workspace ViewModels / `WorkspaceReference`. Prefer Research Ready papers.

**Gate for researcher invites and soft marketing:** 2.2 must exist (even MVP).

---

## Phase 2.3 — Citation Layer

Consume existing Citations / Crossref / BibTeX — insert from library, styles, bibliography. Connect, don’t reimplement.

---

## Phase 2.4 — Guided Generation

AI only with mandatory research context (“Using these N Research Ready papers…”). Never freeform “write my introduction” as research-backed.

---

## Phase 2.5 — Research Reviewer

Strengthen the draft — unsupported claims, missing evidence, weak coverage, etc. Last major Phase 2 piece; shape with soft-launch feedback.

---

## Sequencing rules (frozen)

1. **SaaS-PK ∥ 2.1 → 2.2** — platform money path parallel with Writing MVP.  
2. **Evidence before guided AI** — 2.2 before 2.4.  
3. **External users after 2.2** — first 5–10 see the differentiator.  
4. **Soft launch before 2.5** — don’t wait for Reviewer/Teams/full PSP.  
5. **2.0 kit stays frozen** — no more validation dashboards.

---

*End of frozen Phase 2 roadmap (balanced timeline).*
