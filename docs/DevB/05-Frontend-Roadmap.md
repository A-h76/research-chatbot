# 05 — Frontend Roadmap

**Status:** Draft for review · **Principle:** maximize independent A/B work.

## Key sequencing fact

`docs/epics/EPIC-0001-Architecture-Foundation.md` is **P0 and blocking**: per
`docs/epics/README.md`, EPIC-0002 through EPIC-0006 (Evidence Layer, Research
Workspace, Writing Engine, Reviewer, Research Intelligence) may not start until
EPIC-0001 exits. EPIC-0001 already contains a Developer-B ticket list (B-001…B-009).
Rather than propose a second, competing roadmap, this document treats those tickets
as **Immediate**, and sequences the findings from
[01](01-Frontend-Architecture-Review.md)–[04](04-Design-System-Review.md) around them.

## Immediate (blocking — before any EPIC-0002+ frontend work starts)

These map directly to EPIC-0001's Developer-B tickets, adapted to what this review
found:

1. **IDD dual review** (B-001) — read `docs/idd/IDD-0001` through `IDD-0010` against
   the actual frontend code (done in this review pass — see
   [06-API-Contract-Review.md](06-API-Contract-Review.md)).
2. **Contract gap list** (B-004) — produced as [06](06-API-Contract-Review.md).
3. **Frontend type-freeze file** (B-005) — create `frontend/src/types/idd.ts` mirroring
   `docs/idd/IDD-0004-Frontend-Contracts.md` §3 verbatim. Planned in
   [07-TypeScript-Type-Plan.md](07-TypeScript-Type-Plan.md). Currently **does not
   exist** — only `frontend/src/types/api.ts` does.
4. **MSW/fixture plan** (B-006) — plan in [08-Mock-Strategy.md](08-Mock-Strategy.md).
   `frontend/src/mocks/` doesn't exist yet.
5. **Smoke path outline** (B-007) — define the minimal user path (login →
   project → upload → evidence → write → export) that must keep working through the
   EPIC-0002+ rollout. Not yet written; sequenced here as a short doc, not code.
6. **Sign-off / freeze declaration** (B-002, B-008) — these are Developer A / Architect
   coordination steps, not something Developer B can unilaterally complete; tracked in
   [HANDOFF.md](HANDOFF.md) as "waiting on."

**Not gated on EPIC-0001**, and cheap to do now because they're pure frontend hygiene
with no contract dependency:

7. Rename or implement `features/writing/state/writingStore.ts` — either wire up a
   real store or rename the file/exports so they don't imply one exists (Architecture
   Review, weakness 2). Small, isolated, zero contract risk.
8. Route the 6 raw-`fetch` call sites through `apiClient` where the response is plain
   JSON (`collectionsApi.ts`, `relatedApi.ts`, `discoverApi.ts`, the inline fetches in
   `SearchPage.tsx` and `WritingPage.tsx`) — `chat/api.ts`'s raw fetch stays as-is
   (justified, needs the raw stream). This is already an EPIC-0004 ticket
   ("replace raw fetch with apiClient") for the writing case; doing the other four now
   removes debt before EPIC-0002/0004 add more surface area on top of it.

## Sprint 1 (once EPIC-0001 exits — Evidence Layer UI, per EPIC-0002)

- Evidence list UI, Extract CTA, Evidence Inspector **as a routed page** (currently a
  panel — see [02-UI-Inventory.md](02-UI-Inventory.md)), MSW fixtures for evidence
  endpoints, query-key invalidation wiring (EPIC-0002 tickets B-211…B-215).
- Extract a shared `Panel` primitive into `components/ui/` before adding more
  Evidence panels on top of the existing 6-in-`projects/` + 5-elsewhere pattern
  (Component Inventory, reuse opportunity). Small, do-it-once cost now vs. an 8th/9th
  bespoke panel later.
- Start test coverage on `chat/` — the largest untested feature — timed to land
  before EPIC-0004 (Writing Engine) starts touching chat-adjacent evidence-in-chat
  surfaces (`ChatPage`, `PaperChatPage`).

## Sprint 2 (Research Workspace shell + start of Writing Engine, per EPIC-0003/0004)

- AppShell IA pass, Library empty/import CTAs, Paper overview tab polish, Search page
  copy (EPIC-0003 tickets B-311…B-317) — largely additive to already-built pages.
- Writing Workspace 3-column layout, grounded-generate UX, citation→Inspector deep
  link, confidence strip, autosave/version restore, export tab (EPIC-0004 tickets
  B-411…B-417) — this is where `WritingPage.tsx`'s 1,260 lines should get decomposed
  as part of the rebuild rather than as a separate refactor pass; doing the split
  opportunistically during feature work avoids a standalone "refactor WritingPage"
  PR that touches no behavior (against the charter's "avoid unrelated refactors").

## Future (Reviewer, Research Intelligence UI, and beyond — EPIC-0005/0006/EPIC-future)

- Reviewer UI as a new `features/reviewer/` surface (EPIC-0005) — currently doesn't
  exist at all.
- Selective UI for the RI pipeline stages (Retrieve→Rank→Consensus→Conflict→Reason)
  per EPIC-0006, building on the existing `pipeline/` feature's status/adapter layer.
- Longer-horizon items named in `docs/idd/IDD-0010-Future-Extensions.md` and
  `Now-Status/05-MIGRATION-ROADMAP.md` Phase 3 (Trust Center `/trust` page, Citation
  Intelligence, Compare Workspace expansion) — explicitly future, not near-term.
- Route-level code splitting (`React.lazy` per page in `router.tsx`) once bundle size
  is actually measured — currently unmeasured, flagged as a perf hypothesis in
  [01-Frontend-Architecture-Review.md](01-Frontend-Architecture-Review.md), not yet a
  confirmed problem.
- Accessibility audit (axe/Lighthouse) of the bespoke chart kit and `Sidebar.tsx`.
- Storybook or equivalent component-explorer, if the team decides the DX gap is worth
  the setup cost (not yet decided — see [10-Risks-And-Questions.md](10-Risks-And-Questions.md)).

## What this roadmap deliberately does not include

No item here requires a backend contract change, a new dependency, or a rewrite of a
working module — consistent with `docs/00-constitution.md` principle 1 ("no rewrites
without an ADR") and the charter's "no unnecessary refactors" rule. Where frontend
work is blocked on something only Developer A can provide, it's listed as a question
in [10-Risks-And-Questions.md](10-Risks-And-Questions.md) and
[docs/contracts/frontend-feedback.md](../contracts/frontend-feedback.md), not assumed
away.
