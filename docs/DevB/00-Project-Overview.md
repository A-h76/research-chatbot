# 00 — Project Overview (Developer B perspective)

**Status:** Draft for review · **Author:** Developer B (Frontend) · **Date:** 2026-07-30

## What Dhund is

Dhund is a **Research Operating System**, not a chat app. The product spine, per
`docs/idd/README.md` and `Now-Status/00-README.md`:

```
PDF → Document Understanding → Evidence Objects → Retrieval → Ranking →
Reasoning → Writing Workspace → Reviewer → Export
```

The canonical unit of knowledge is the **EvidenceObject** (frozen by ADR-0003 and
ADR-0005 — see [06-API-Contract-Review.md](06-API-Contract-Review.md)). Chat is one
surface among several, not the primary product loop.

**Important context discovered during review:** the root `README.md` still describes
an older, chat-first "ChatGPT but branded Dhund" product framing (Google login,
streaming replies, memory, citations manager) with no mention of Evidence Objects,
Research Intelligence, or the Writing Workspace. That README predates the pivot
documented in `Now-Status/03-DOMAIN-COVERAGE.md` and the `docs/idd/` pack. I have not
touched it — flagged here, and in
[10-Risks-And-Questions.md](10-Risks-And-Questions.md), since it's stale
product-facing documentation, not a frontend architecture concern.

## What already exists before I start

This is not a greenfield frontend. Two things are already true:

1. **A working, fairly mature React app** — 25 feature folders under
   `frontend/src/features/`, TanStack Query for server state, `@base-ui/react` +
   shadcn primitives, a bespoke visx chart kit, 29 test files, real (not stub) UI for
   chat, papers, library, projects, writing, evidence, and pipeline status. Full
   inventory in [01](01-Frontend-Architecture-Review.md)–[04](04-Design-System-Review.md).

2. **A same-day architecture/contract pack** authored 2026-07-30, untracked in git,
   entirely "Status: Proposed" and unsigned: `docs/idd/` (10 documents),
   `docs/contracts/` (4 living-contract READMEs), `docs/epics/` (EPIC-0001 through
   EPIC-0006), and `Now-Status/` (a Phase-0 architecture review, scorecard ~6.8/10,
   dependency graph, migration roadmap). This pack sits on top of 7 **accepted and
   git-tracked ADRs** (`docs/adr/0001`–`0007`) that already froze the Evidence Layer,
   the Postgres worker queue, and the `EvidenceQuery` contract.

That second point matters more than it might look: **`docs/epics/EPIC-0001-Architecture-Foundation.md`
already lists a Developer-B ticket set (B-001…B-009)** — IDD review, IDD sign-off,
publish living contracts, contract gap list, a frontend type-freeze file, an
MSW/fixture plan, a smoke-path outline, a freeze declaration, an exit review gate —
that is nearly a checklist for exactly the charter I'm operating under. Rather than
inventing a second, competing roadmap, [05-Frontend-Roadmap.md](05-Frontend-Roadmap.md)
proposes treating EPIC-0001's B-tickets as this workspace's Phase 1.

## Scope of this review

This documentation set (`docs/DevB/`) is Phase 1 of the charter: understand before
building. No frontend code has been changed. No backend/API contracts have been
touched or proposed to change here — where the frontend needs something the backend
doesn't yet provide, it's recorded in
[docs/contracts/frontend-feedback.md](../contracts/frontend-feedback.md) per the
charter's communication protocol, not decided unilaterally.

## Document index

| File | Purpose |
|---|---|
| [01-Frontend-Architecture-Review.md](01-Frontend-Architecture-Review.md) | Strengths/weaknesses/debt/maintainability/perf/a11y/DX assessment |
| [02-UI-Inventory.md](02-UI-Inventory.md) | Every page, Complete/Partial/Placeholder/Missing |
| [03-Component-Inventory.md](03-Component-Inventory.md) | Reusable components, duplicates, reuse opportunities |
| [04-Design-System-Review.md](04-Design-System-Review.md) | Typography, spacing, color, tokens, icons, a11y, consistency |
| [05-Frontend-Roadmap.md](05-Frontend-Roadmap.md) | Immediate / Sprint 1 / Sprint 2 / Future |
| [06-API-Contract-Review.md](06-API-Contract-Review.md) | Compatible / Needs Clarification / Missing / Deferred |
| [07-TypeScript-Type-Plan.md](07-TypeScript-Type-Plan.md) | Interfaces derived from the IDD, no invented fields |
| [08-Mock-Strategy.md](08-Mock-Strategy.md) | MSW/fixtures so frontend runs independently of backend |
| [09-DeveloperB-Notes.md](09-DeveloperB-Notes.md) | Running engineering log |
| [10-Risks-And-Questions.md](10-Risks-And-Questions.md) | Open questions, for Developer A / Architect |
| [CHANGELOG.md](CHANGELOG.md) | Dated log of this workspace's changes |
| [HANDOFF.md](HANDOFF.md) | Always-current async handoff state |
