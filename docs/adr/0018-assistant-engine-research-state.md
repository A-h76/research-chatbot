# ADR-0018: Assistant Engine + Research State (decision brain)

Status: accepted (freeze architecture; implement iteratively)  
Date: 2026-08-08  
Relates: ADR-0012 (chat orchestration), ADR-0016 (Capability Router), Bite 15 Workflow Engine

## Context

Home “Research Mentor” UI proved the product thesis — Dhund should feel like a
research supervisor, not ChatGPT-in-a-panel — but the first ship put **decision
policy in React** (intent gating, experience tone, next-action copy). That is
unstable: full chat, Writing assist, Library, RI, and future clients can still
emit capability dumps and ignore project journey.

Dhund already freezes:

- **Capability Router** (ADR-0016) — how to execute a Research Job  
- **Workflow Engine** (Bite 15) — long-running research pipeline steps  
- **Evidence First** (constitution §11) — LLMs explain; evidence is fact  

Missing: a **decision brain** that runs *before* language generation and is
shared by every surface.

## Decision

### Separation of brains (binding)

> **The Assistant Engine decides *what* help the researcher needs.  
> The Capability Router decides *how* to execute that help.**

And:

> **LLMs generate language. Dhund generates decisions.**

And:

> **Research State is computed from system signals, never guessed by an LLM.**

### Naming

| Layer | Public / docs name | Internal nickname OK |
|-------|--------------------|----------------------|
| Decision brain | **Assistant Engine** | “mentor” as *behavior*, not package name |
| HTTP surface | `POST /api/assistant/turn` (and/or chat preparation port) | not `/mentor/*` |
| Shared domain object | **Research State** | — |

“Mentor” describes tone (Teacher / Coach / Reviewer / Partner / Companion).  
Architecture components age better as Assistant Engine + Research State.

### Canonical flow

```text
User
  ↓
Assistant Turn API   (/api/assistant/turn — domain-oriented)
  ↓
Assistant Engine
  • Intent detection
  • Research State (computed)
  • Journey stage
  • Experience / goals
  • Mode selection
  • Local reply vs LLM job
  ↓
Capability Router     (only if LLM / tools needed)
  • Capability, model, tools
  ↓
Prompt Builder        (composed: base + profile + state + stage + intent + mode)
  ↓
AI Gateway → LLM
  ↓
Response (+ optional action card / CTA payload)
```

Later (already sketched by Bite 15 — do **not** rebuild):

```text
Assistant Engine  →  “what should happen”
Workflow Engine   →  “perform the long-running research job”
```

### Research State (first-class domain object)

Not a free-form JSON blob invented per UI. A computed aggregate every surface
may consume (Home, Writing, Library, RI, Review, Chat, mobile):

```text
ResearchState
├── User        (experience, goals, fields, …)
├── Project     (title, discipline, …)
├── Corpus      (papers, evidence, themes, gaps, contradictions, coverage)
├── Workflow    (stage, completion, nextAction, blockers)  ← derived rules
└── Writing     (manuscript presence, review, …)
```

**Stage derivation example (correct):**

```text
papers > 0 ∧ evidence == 0  →  stage = Evidence Extraction
evidence > 0 ∧ writing exists ∧ review incomplete  →  stage = Writing
```

**Incorrect:** `stage = "Writing"` because a model said so.

### Modes (prompt composition, not one mega-prompt)

Assistant Engine selects one mode per turn:

| Mode | When |
|------|------|
| Companion | Greetings, small talk — prefer **local** replies |
| Coach | Progress / “what next” / “I don’t know” — decide CTA from Research State |
| Teacher | Explain concepts |
| Research Partner | Technical research Q&A |
| Reviewer | Critique writing (with evidence/writing context) |

Modes are **policies** for Prompt Builder + local handlers, not cosplay.

### Intent gating

Greetings and pure workflow uncertainty **must not** call the LLM by default:

```text
Hi → Intent=Greeting → Companion → local Research-State reply
I don't know → Coach → structured profile/journey questions → persist → continue
What is YOLO? → Teacher → Research Job → Router → LLM
```

### Frontend rule

> Frontend decides how Dhund **looks**. Backend decides how Dhund **thinks**.

Cards, layout, motion stay in UI. Intent routing, journey, next-action,
mode, and local-vs-LLM are Assistant Engine responsibilities. Home React
helpers are a temporary façade until the API owns them.

## Ship slices (no big-bang rewrite)

1. **Research State** service — compute + contract; expose read API / embed in `/api/me` or home bootstrap  
2. **`POST /api/assistant/turn`** — returns `local_reply | action_card | start_job`  
3. **Intent gating** — greetings / uncertain never burn tokens  
4. **Mode-based prompt composition** — wire into Prompt Builder / chat preparation (ADR-0012)  
5. **Every surface** consumes the same Assistant Engine (retire frontend-only mentor policy)

Do **not**: fork a second chat stack forever; merge Assistant Engine into Capability Router; guess stages with an LLM.

## Alternatives considered

1. **Keep mentor policy in frontend** — Rejected: inconsistent identity across surfaces.  
2. **One mega system prompt “be a mentor”** — Rejected: still capability-dumps; no computed journey; hard to maintain.  
3. **Name the package Mentor Engine** — Soft-rejected: fine as behavior nickname; docs/packages use Assistant Engine.  
4. **Replace Capability Router with mentor** — Rejected: violates ADR-0016 separation.

## Consequences

- Dhund’s differentiator becomes **journey-aware decisions**, not model brand.  
- Home UI becomes a thin renderer of Assistant Turn + Research State.  
- Chat preparation (ADR-0012) gains an Assistant Engine call as the first orchestration step.  
- Workflow Engine remains the long-running executor; Assistant Engine does not own extraction/UFTR pipelines.

## Four permanent cores (stop thinking in “slices”)

Slices 1–5 were a ship sequence. The lasting architecture is four cores:

| Core | Owns |
|------|------|
| **Assistant Engine** | Intent, mode, policy, local vs LLM |
| **Research State** | Computed corpus/writing truth, stage, next action |
| **Capability Router** | Models, tools, execution plans (ADR-0016) |
| **Workflow Engine** | Long-running research jobs (Bite 15) |

Future product layers *extend* these cores — they are not a fifth brain.
**Do not build them now** (Journey Engine, Skill Registry, Research Memory, Mentor Analytics)
until the frontend has been perfected and real researcher friction demands them.

| Layer (deferred) | Extends | When justified |
|------------------|---------|----------------|
| Research Journey Engine | Research State | After FE workflow is stable and pages need richer stage UI |
| Proactive recommendations | Assistant + State | After Home/Writing/RI already show one clear CTA well |
| Skill Registry | Assistant modes | When mode prompts become hard to maintain |
| Research Memory | Memory + State | When Writing/chat need durable researcher preferences |
| Mentor analytics | Ledger / events | After 20–50 real researchers; learn from usage |

### UI doctrine (binding) — never Jira for research

> **The system may know everything. The UI should only show what helps the current task.**

> **Design from the researcher's brain. Engineer from the engineer's brain.**

Research State is an **internal** object for Assistant / Router / Workflow.
Pages must **not** render the full state (stage + journey + health + coverage +
confidence + blockers + milestones). That path turns Dhund into a dashboard.

Canonical path:

```text
Research State  →  Decision  →  UI Hint / View Model  →  Render
```

Not:

```text
Research State  →  Render everything
```

**Per-page budget (hard cap):**

1. **One status** (e.g. Ready / Needs review / Processing / Writing)  
2. **One recommendation** (one CTA)  
3. **One context** (e.g. “9 papers”)

Example — Home shows “Continue research · Review evidence from 2 papers”, not a journey board.
Research Intelligence may show slightly more corpus context; it still must not become a KPI wall.

Prefer **surface view models** (`title`, `subtitle`, `primaryAction`) over exposing
Research State JSON to every React page. `/api/assistant/research-state` remains for
engine/debug; product UI should consume session/turn hints or thin view endpoints.

**Strategic priority after Slice 5:** Phase 2 = frontend UX (Home → Projects → Library →
Paper → RI → Writing → Review → mobile → polish). Treat the four cores as a **stable
platform**. Resume deferred backend layers only when the UI says “I wish the backend knew this.”

Product doctrine: [`PRODUCT-CONSTITUTION-v1.md`](../PRODUCT-CONSTITUTION-v1.md) — especially
Invisible Intelligence and One Purpose Per Screen.

## Cost / Security / Observability / Extensibility

- **Cost:** Local intents reduce greeting tokens; ledger still records LLM turns (ADR-0016).  
- **Security:** Same authz as chat/project; Research State must not leak other users’ corpora.  
- **Observability:** Log `intent`, `mode`, `stage`, `local_vs_llm` on every turn.  
- **Extensibility:** New modes / journey stages are registry entries; public API stays `/api/assistant/*`.

## Contract

Living contract: [`docs/contracts/assistant-engine-contract.md`](../contracts/assistant-engine-contract.md) (v0 → v1 as slices land).
