# HANDOFF — Developer B ↔ Developer A

**Always keep this file current.** Last updated: 2026-07-30.

## What I'm working on

Phase 1 review complete: full `docs/DevB/` documentation workspace written
(00 through 10, plus this file and `CHANGELOG.md`). No implementation started.
Waiting on user (acting as Architect/coordinator) to confirm before I begin any
code changes.

## What's completed

- Full frontend architecture review — [01-Frontend-Architecture-Review.md](01-Frontend-Architecture-Review.md)
- UI inventory (every route: Complete/Partial/Placeholder/Missing) — [02-UI-Inventory.md](02-UI-Inventory.md)
- Component inventory + reuse opportunities — [03-Component-Inventory.md](03-Component-Inventory.md)
- Design system review — [04-Design-System-Review.md](04-Design-System-Review.md)
- Roadmap aligned to existing `docs/epics/EPIC-0001` Developer-B tickets — [05-Frontend-Roadmap.md](05-Frontend-Roadmap.md)
- API contract gap analysis against `docs/idd/IDD-0003` — [06-API-Contract-Review.md](06-API-Contract-Review.md)
- TypeScript type plan (`frontend/src/types/idd.ts`, not yet created) — [07-TypeScript-Type-Plan.md](07-TypeScript-Type-Plan.md)
- Mock strategy (MSW, not yet a dependency) — [08-Mock-Strategy.md](08-Mock-Strategy.md)

## What's blocked

- **All Sprint 1+ frontend implementation work is blocked on `docs/epics/EPIC-0001`
  exiting** — its own status field says "In progress (docs exist; review pending)."
  This isn't a Developer-B-specific blocker; it applies to the whole EPIC-0002+
  sequence per `docs/epics/README.md`'s own rule.
- Four contract questions block confidently writing `frontend/src/types/idd.ts` and
  the Evidence Inspector page work in EPIC-0002 — see items 1–5 in
  [10-Risks-And-Questions.md](10-Risks-And-Questions.md).

## What I need from Developer A

1. Resolve the writing-document autosave endpoint discrepancy (PATCH vs. POST
   `/autosave`, `autosave_key` vs. `current_version`) — [10-Risks-And-Questions.md](10-Risks-And-Questions.md) item 1.
2. Confirm whether `POST /api/writing/documents/{id}/export` exists yet, or whether
   IDD-0003 should instead document the live `/api/export/*` routes — item 2.
3. Confirm the actual live shape of `/api/evidence/*` responses (page range vs.
   single page, `study_type`/`study_quality`/`relation` vs.
   `evidence_type`/`finding`/`pipeline_version`) so `EvidenceObject` in
   `frontend/src/types/idd.ts` can be written without guessing — item 3.
4. Confirm whether `GET /api/writing/documents/{id}` and
   `DELETE /api/evidence-bindings/{id}` exist on the backend — item 5.

See [docs/contracts/frontend-feedback.md](../contracts/frontend-feedback.md) for the
same list in the charter's required feedback format.

## Next planned task (pending confirmation to proceed)

Per [05-Frontend-Roadmap.md](05-Frontend-Roadmap.md)'s Immediate tranche, in
priority order once approved:
1. Two small, isolated, zero-contract-risk fixes: remove the duplicate raw
   `fetch("/api/writing", …)` in `WritingPage.tsx` (use `writingApi.transform`
   instead), and rename or implement `features/writing/state/writingStore.ts`.
2. Add MSW as a devDependency and scaffold `frontend/src/mocks/idd/` per
   [08-Mock-Strategy.md](08-Mock-Strategy.md).
3. Create `frontend/src/types/idd.ts` — blocked on Developer A's answers to
   questions 3–4 above for the `EvidenceObject`/`WritingDocument` fields
   specifically; the other 15 interfaces have no known discrepancy and could be
   added immediately if partial progress is preferred over waiting for all answers.
