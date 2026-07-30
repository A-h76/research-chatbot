# 08 — Mock Strategy

**Status:** Draft for review · **Goal: frontend runs and is testable independently
of the live backend.**

## Current state

- **MSW is not currently a dependency** — confirmed absent from `frontend/package.json`
  (verbatim dependency list in [01-Frontend-Architecture-Review.md](01-Frontend-Architecture-Review.md)).
  It needs to be added as a devDependency. This is a real new-dependency addition;
  the charter explicitly calls for MSW by name ("Use: MSW, Fixtures, Mock Services"),
  so it's pre-approved rather than a judgment call, but it's recorded here so it's
  visible in `CHANGELOG.md` when it lands rather than appearing unannounced in a
  `package.json` diff.
- `frontend/src/mocks/` does not exist at all — confirmed via direct directory check.
- `docs/idd/IDD-0004-Frontend-Contracts.md` §5 already specifies the target shape:
  fixtures under `frontend/src/mocks/idd/` (`papers.json`, `evidence.json`,
  `grounded-ok.json`, `grounded-blocked.json`) plus MSW handlers matching the
  IDD-0003 routes, with an explicit "definition of ready-for-UI": mocks must satisfy
  the loading/empty/error/optimistic cases listed per page in IDD-0004 §2.
- `docs/epics/EPIC-0001-Architecture-Foundation.md` ticket B-006 ("MSW/fixture plan")
  and `docs/epics/EPIC-0002-Evidence-Layer.md` ticket B-214 ("MSW fixtures [for
  evidence endpoints]") both already name this as required, blocking, work.

## Plan

1. **Structure**, following IDD-0004 §5 and the existing `frontend/src/lib/` layout
   conventions:
   ```
   frontend/src/mocks/
     idd/
       fixtures/
         papers.json
         evidence.json
         grounded-ok.json
         grounded-blocked.json
         writing-documents.json      (needed for Writing Studio coverage, not named
                                       in IDD-0004 §5's initial list but required by
                                       the same section's "Writing Workspace" row)
       handlers/
         evidence.ts       — MSW handlers for /api/evidence/*, /api/projects/{id}/evidence
         writing.ts         — MSW handlers for /api/writing/documents/*
         projects.ts, papers.ts, search.ts, jobs.ts  — one file per IDD-0003 section
       browser.ts    — setupWorker() for dev-mode mocking
       server.ts     — setupServer() for Vitest
   ```
2. **Handlers implement the frozen IDD-0003 contract, not the current live backend
   quirks.** Where [06-API-Contract-Review.md](06-API-Contract-Review.md) found a
   discrepancy (e.g., writing-document autosave endpoint/field-name mismatch), the
   mock should follow whichever shape Developer A confirms is authoritative — not
   silently pick one, since that would let a wrong assumption pass tests undetected.
3. **Wire into Vitest**, not just dev-mode browsing: `frontend/vite.config.ts`'s
   inline `test` config currently runs with `environment: "node"` — MSW's `setupServer`
   works fine under `node`, so this doesn't require the jsdom/component-test
   environment question in [10-Risks-And-Questions.md](10-Risks-And-Questions.md) to
   be resolved first; that question only matters for component-render tests, not for
   API-mocking tests.
4. **Dev-mode toggle**: gate MSW's `setupWorker().start()` behind an env var (e.g.
   `VITE_USE_MOCKS`) in `main.tsx`, off by default, so the existing Vite-proxies-to-Flask
   dev workflow (`npm run dev` + `python server.py`) is unaffected unless a developer
   explicitly opts into mock mode — this preserves the current, working dev setup
   rather than replacing it.

## Sequencing

Sequenced as part of [05-Frontend-Roadmap.md](05-Frontend-Roadmap.md)'s Immediate
tranche (EPIC-0001 ticket B-006) with the fixture set expanding per-feature as each
EPIC-0002+ ticket lands (e.g., B-214 adds evidence fixtures specifically). Not a
big-bang mock-everything effort — fixtures get added alongside the UI that needs them.

## Explicitly not doing

- Not mocking endpoints that already work reliably against the real dev backend
  today (e.g., `/api/me`, `/api/projects` CRUD) unless a specific test needs
  isolation from the database — MSW is for unblocking frontend work on
  not-yet-built or flaky backend surfaces, not a wholesale replacement for
  integration testing against real Postgres (which remains Developer A's domain per
  `docs/00-constitution.md`'s "real containers over mocks" principle for
  backend/integration tests — that principle governs backend test strategy, not
  frontend unit/component test strategy, so there's no conflict here).
