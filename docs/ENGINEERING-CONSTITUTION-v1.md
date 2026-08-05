# Dhund Engineering Constitution v1

**Status:** **Frozen** — binding for all backend evolution after this date.  
**Date:** 2026-08-05  
**Type:** Architecture governance (not a rewrite plan)  
**Companions:** [`00-constitution.md`](00-constitution.md) · [`DHUND-DESIGN-LANGUAGE-v1.md`](DHUND-DESIGN-LANGUAGE-v1.md) · [`ENGINEERING-EVOLUTION-TRACKER.md`](ENGINEERING-EVOLUTION-TRACKER.md) · [`ARCHITECTURE-HEALTH.md`](ARCHITECTURE-HEALTH.md) · [`adr/`](adr/) · [`audit/03-TECHNICAL-DEBT-REPORT.md`](audit/03-TECHNICAL-DEBT-REPORT.md)

**Intent:** Make Dhund feel like an **engineering platform** — every package answers *“Which business capability owns this?”* — without demolishing a working Research OS.

**Doctrine freeze:** High-level constitutions for product, UI, AI execution, and engineering evolution are **enough**. Further gains come from **implementing** them (Evolution Tracker + Architecture Health), not writing more doctrine docs.

---

## 0. The one rule

> **Don't clean for aesthetics. Clean to strengthen architecture.**

A “beautiful folders” week that breaks a stable system is a failure.  
Dhund renovates **room by room**. It does **not** demolish the house.

```text
Current house
    ↓
Renovate room by room
NOT
Demolish the house
```

---

## 1. Relationship to Master Constitution

[`00-constitution.md`](00-constitution.md) remains binding (no rewrite without ADR, extend interfaces, Postgres worker, Evidence First, platform freeze, …).

This document **adds** Platform Layer vs Product Domain ownership and the **80/20 debt** operating model. Where they conflict, the Master Constitution + an ADR win — open an ADR; don’t silently diverge.

**Living pictures (not more constitutions):**

| Doc | Answers |
|-----|---------|
| [`ENGINEERING-EVOLUTION-TRACKER.md`](ENGINEERING-EVOLUTION-TRACKER.md) | Current → Target → Priority per area |
| [`ARCHITECTURE-HEALTH.md`](ARCHITECTURE-HEALTH.md) | Scored KPIs (ownership, pipelines, SoT, replaceability, …) |

---

## 2. Platform Layers vs Product Domains

A flat priority chain (AI → Discovery → Library → …) mixed **infrastructure that serves everything** with **what users experience**. Split them.

### Platform Layers (serve everything)

```text
AI Platform          Capability Router, gateway, registries, ledger, policies, providers
Storage              Object storage backends / façades (unify over time — ADR-0014)
Trust                Security events, compliance hooks, audit surfaces
Infrastructure       App composition, config, shared runtime
Worker + Queue       worker.py HANDLERS, outbox, Postgres SKIP LOCKED (ADR-0001)
Observability        Metrics, structured logs, job health
Auth                 Identity, sessions, invites, tokens
Shared               logging, security, pdf, retry, cache, validation, types
```

### Product Domains (what users experience)

```text
Discovery            Find / resolve works — providers only at the edges
Library              Researcher’s corpus — connections, imports, collections, sync, files
Evidence             EvidenceObjects, RI stages, bindings (frozen contracts)
Research Intelligence  SUE / analysis / quality / methodology (isolated)
Writing              Binder, composer, grounding, citations, exports
Reviewer             Critique writing vs evidence (may nest under Writing until extract)
Workspace            Projects, notes, annotations, reading, compare, timeline
Ecosystem (UX)       Catalog honesty — Live vs Coming soon (not a dump of SDKs)
```

**Billing** (when unlocked) is a Platform Layer concern that Product Domains consume — not a researcher “surface” by itself.

### North-star `backend/` layout (evolve toward — do not big-bang)

```text
backend/
  # --- Platform Layers ---
  ai/
  storage/                 # or unified façade over time
  trust/
  auth/
  shared/
  ecosystem/               # catalog / integration honesty

  # --- Product Domains ---
  discovery/
  library/
  evidence/
  research_intelligence/
  writing/
  reviewer/                # optional extract
  workspace/

  # --- Thin HTTP (optional umbrella) ---
  api/
```

**Today’s code already has many of these.** Grow and extract **into** layers/domains; do not invent parallel dumps.

### Forbidden as default homes

```text
routes/   helpers/   models/   utils/   services/   common/
random.py   helper.py   utils.py (400 functions)
```

Nobody can answer ownership. Prefer `shared/<concern>/` or a named layer/domain.

---

## 3. Evolution priority (renovate deliberately)

Track Current → Target in the [Evolution Tracker](ENGINEERING-EVOLUTION-TRACKER.md). Default engineering focus:

| Priority | Focus |
|----------|--------|
| **High** | AI Invocation (dual → Router/Gateway) · Cost Ledger unify · Research Scope coverage |
| **Medium** | Thin `server.py` · Library ownership · Discovery shared pipelines · Writing/Reviewer · Trust surfaces |
| **Low** | Upload unify (ADR-0014) · Workspace extract · Celery-never · aesthetic renames |

Do not jump to Workspace folder polish while High AI Platform rows are still dual.

**Product-domain build order** (when shipping user capability): Discovery/Library hygiene → Evidence (maintain) → Writing/Reviewer → Workspace — always with Platform AI/Trust/Queue underneath.

---

## 4. Keep — never rewrite as “cleanup”

| Keep | Why |
|------|-----|
| Database schema + migrations | Source of truth; extend with migrations |
| Public / frozen APIs (`docs/contracts/`) | Platform freeze |
| Postgres queue + `worker.py` HANDLERS | ADR-0001 |
| Outbox pattern | Transactional job creation |
| Evidence / RI contracts | ADR-0003 / 0005 / 0006 / 0007 |
| Capability Router + Research Scope | ADR-0016 / 0017 |
| Dual upload stacks (for now) | ADR-0014 — unify later with ADR, not aesthetic merge |

**Refactor around them. Do not replace them to look tidy.**

---

## 5. Hard rules (guardrails)

### 5.1 Bounded context

Every new feature belongs to **exactly one** primary home — either one **Platform Layer** or one **Product Domain** (§2).  

Cross-cutting needs go to `shared/<concern>/` or an explicit published interface — not copy-paste into a second package.

### 5.2 No new `utils.py` dumping grounds

New shared code must land in a **named concern** under `shared/` (or an existing package’s private `_internal/`).  
A 400-function `utils.py` is a constitution violation.

### 5.3 No direct provider SDK calls outside the AI Gateway

```text
Feature code
    ↓
Capability Router
    ↓
Gateway
    ↓
Provider (openai / anthropic / google / …)
```

**Never** `from openai import OpenAI` (or equivalent) inside Library, Writing, Evidence product features.  
You already locked this (ADR-0016) — **never break it.**

### 5.4 Discovery providers discover only

No duplicate business logic per connector. Shared pipelines (import, metadata, fulltext, UFTR) sit **above** provider-specific clients.

### 5.5 Shared pipelines before provider-specific implementations

If two providers need the same step, extract the step once. Provider folders stay thin.

### 5.6 Incremental refactor only

Architectural **rewrites** require an ADR (Master Constitution §1).  
Moving a route cluster into a blueprint factory is renovation — still prefer small PRs and a bootable app after every milestone (Master §8).

### 5.7 Every package has an owner sentence

Each top-level capability package should state in a one-line README or module docstring:

> **Owns:** …  
> **Does not own:** …

### 5.8 Dual paths — strengthen, don’t aesthetic-merge

Dual upload/storage, dual AI invoke, dual cost ledgers are **named debt**.  
Closing them is an architecture milestone (often under AI Platform / Library), not a “tidy folders” PR. Prefer consolidating **write sites and policies** over renaming directories.

---

## 6. `server.py` endgame (deliberate, incremental)

**Do not** split `server.py` randomly by line count.

Target shape:

```text
server.py / create_app()
    → register_extensions()
    → register_blueprints()   # factory/DI — never import server from packages
    → run()
```

HTTP adapters live under capability blueprints (`backend/<capability>/` or `backend/api/<capability>/`).  
Models may remain on the shared Base longer than routes — **extracting models is a separate ADR** (Master Constitution import constraint).

Milestone rule: each PR that peels a route cluster must leave `/` and critical APIs green.

---

## 7. AI Platform target (priority #1 detail)

Evolve `backend/ai/` toward:

```text
ai/
  capability_router/
  gateway/
  model_registry/
  prompt_registry/
  ai_ledger/          # converge dual ledgers here over time
  evaluations/
  policies/           # includes Research Scope enforcement points
  providers/
    openai/
    anthropic/
    google/
```

**Success looks like:** one invocation story, one attribution story, provider SDKs only under `providers/`.

---

## 8. Discovery / Library split (priorities #2–#3)

**Discovery** — find and resolve scholarly / external works (OpenAlex, PubMed, arXiv, UFTR, …).  
**Library** — own the researcher’s corpus (files, connections, collections, sync, storage keys).

Do not keep growing forever as flat `google_drive.py` / `pubmed.py` siblings without shared pipelines.

---

## 9. Debt operating model — 80 / 20

**Do not** schedule a sprint named only “Cleanup.”

Every capability milestone should roughly:

```text
~80%  New or hardened capability
~20%  Debt reduction in the same neighborhood
```

Examples of valid 20%:

- delete or wire a dead helper touched by the feature  
- move related routes into the owning blueprint  
- deprecate an unused model only when the milestone proves it  
- route a chat/WI call through the gateway instead of a new direct SDK use  
- document Live vs Soon honesty in ecosystem catalog  

Continuous improvement beats a rewrite branch.

---

## 10. Scoring (honest)

| Lens | Today | Aim |
|------|-------|-----|
| Doctrine / product maturity (narrative) | ~8.5/10 | 9.5+ by *applying* doctrines |
| [Architecture Health](ARCHITECTURE-HEALTH.md) KPI | **3.0 / 5** baseline | **≥ 4.0 / 5** without rewrite |

Move High rows on the [Evolution Tracker](ENGINEERING-EVOLUTION-TRACKER.md); rescore Health when Current changes.

---

## 11. What this constitution does *not* authorize

- Renaming folders “because Linear does it”  
- Celery migration for aesthetics (ADR-0001)  
- Unifying upload stacks without ADR (ADR-0014)  
- Breaking Evidence / RI freezes for structure  
- Microservices split as a cleanup project  
- Deleting dual ledgers before a consolidation design  
- **Writing another high-level constitution** instead of implementing Tracker / Health rows  

---

## 12. Checklist — before merging architecture-shaped work

1. Platform Layer or Product Domain — which **one** owns this?  
2. Does it move an Evolution Tracker row Current → Target — or only rearrange files?  
3. Any new `utils.py` / direct provider SDK / duplicate connector logic? → reject or redesign.  
4. Rewrite vs extend? If rewrite → ADR first.  
5. Is there a **20% debt** bite in the same area (or explicitly deferred with reason)?  
6. App still boots; contracts still hold; worker HANDLERS still the queue spine.  
7. If architecture behavior changed → update Tracker and/or Health scores.  

---

## 13. Amendment

Amendments require the same discipline as Master Constitution changes: explicit edit to this file + ADR when behavior or freeze boundaries change. Do not “quietly” invent a second folder taxonomy in a PR description.

**Doctrine set is closed for net-new “constitution-class” docs.** Prefer updating Tracker, Health, ADRs, and contracts.
