# PROJECT_STATUS — Executive engineering index

**Document type:** Executive status only (not a wiki)  
**Audience:** Staff / senior engineers onboarding or auditing  
**Last updated:** 2026-07-29  
**Detail docs:** [`Dhund-Flow/`](./) (this folder)

Branding: product is **Dhund**. Code/docs may still say Personal AI / Soro / ResearchOS — same app, not forks.

---

## Current Platform State

| Field | Value |
|-------|--------|
| **Platform** | Evidence Platform |
| **Status** | **Frozen** |
| **Current development** | **Milestone 1 — Research Writing** (WI modules + section intents) |
| **Phase 2.3 sprints** | **0–6 complete** + productization Waves A–D |
| **Last release (Evidence)** | `v0.2.0-rc1` |
| **Writing Shell baseline** | `v0.1.0` (+ Week 1.1 hardening) |
| **Architecture status** | Stable |
| **Next product surfaces** | Reviewer · Compare polish · Research Assistant |

---

## Architecture Principles

1. **Evidence First** — Research answers come from stored EvidenceObjects, not freeform model invention.  
2. **Research Intelligence computes over evidence** — retrieve, rank, aggregate, conflict-code, reason, then (last) write.  
3. **Research Intelligence never owns knowledge** — no parallel research corpus; no inventing EvidenceObjects.  
4. **Platform contracts are append-only** — breaking changes need an ADR (or equivalent).  
5. **All AI research features consume Evidence Query** — Writing, Reviewer, Compare, Assistant submit the same ask shape.  
6. **No layer may bypass the one directly beneath it without an approved ADR** — enforces the dependency map in [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md).

Read these before changing Evidence / RI code.

---

## Architecture eras (permanent framing)

```text
Era 1 — Analysis
  PDF → Document Understanding → Knowledge Graph (+ Evidence Grading)

Era 2 — Evidence Platform
  Analysis → EvidenceObjects → Inspector → Explain API
  (frozen at v0.2.0-rc1)

Era 3 — Research Intelligence
  EvidenceObjects → Retrieval → Ranking → Consensus → Conflict
                 → Reasoning → Writing Intelligence
```

Each era builds on the previous **without replacing it**.

---

## Version / maturity (one table)

| Layer | Version / state | Notes |
|-------|-----------------|--------|
| **Platform** | `v0.2.0-rc1` | Evidence Platform **Frozen** (ADR-0005) |
| **Evidence Platform** | Frozen | Objects, Explain, bindings, reviews, provenance, bands |
| **Research Intelligence** | Sprint 0–6 **Done** | Pipeline + Writing Extract / Grounded Generate / Inspector RI |
| **Evidence Extraction Pipeline** | Continuous | Quality backlog — not an architecture reopen |
| **Contracts** | Frozen + Query v0 | Evidence Layer + Evidence Query (ADR-0007) |
| **Writing Studio Shell** | `v0.1.0` | Autosave / versions / lifecycle (no freeform AI shell) |
| **Schema migrations** | through **0033** | Writing 0031–32; Evidence 0033 |
| **Analysis engines** | Phase 1.1–1.7 | Feed Evidence; not the answer path for RI |

---

## Frozen Contracts

Changing any of these requires an ADR (or equivalent architectural decision):

| Contract | Governing |
|----------|-----------|
| EvidenceObject | ADR-0003 / ADR-0005 |
| Explain API | ADR-0005 |
| Evidence Query | ADR-0007 |
| Bindings | ADR-0005 |
| Reviews | ADR-0005 |
| Provenance | ADR-0005 |
| Confidence bands (`low` \| `moderate` \| `high`) | ADR-0005 |

Additive fields need fixture + mapper updates in the same change set. Removals/renames need a new ADR.

---

## Roadmap (scan)

| | |
|--|--|
| **Completed** | Platform/beta · Library Bridge · Writing Shell `v0.1.0` · Evidence Platform `v0.2.0-rc1` · RI Sprints 0–6 |
| **Current** | Stabilize RI APIs in product UI; ops/SaaS-PK parallel track |
| **Next** | Reviewer (compiler-shaped) · Compare consistency · Research Assistant |
| **Later** | Publication engine · broader public multi-tenant SaaS |

Full roadmap: [ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md)

---

## Current risks (summary)

| Area | Top risk |
|------|----------|
| Security | Open signup / cost abuse if allowlist unset on public deploy |
| Scaling | O(n) RAG cosine; single-node worker model |
| AI | Hallucinated citations if features bypass Evidence Query |
| Infra | Worker needs Postgres; no Sentry yet |
| Product | Branding inconsistency (Dhund vs legacy names) |

Detail: [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md) · [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md)

---

## Where to go next

| Need | Document |
|------|----------|
| Stack, eras, flows | [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) |
| What exists vs planned | [FEATURE_MATRIX.md](FEATURE_MATRIX.md) |
| Deploy / checklist / scores | [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md) |
| Why debt remains | [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md) |
| Sequencing | [ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md) |

Root pointer: [`../PROJECT_STATUS.md`](../PROJECT_STATUS.md) redirects here.
