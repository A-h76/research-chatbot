# 01 — Frontend Architecture Review

**Status:** Draft for review · **Scope:** `frontend/` only · **No code changed.**

## Strengths

- **Consistent factory-free but well-separated API layer.** 18 of 24 feature `api.ts`
  files route through `frontend/src/lib/apiClient.ts`'s `api.get/post/patch/delete/postForm`,
  which centralizes 401 handling (dispatches a `soro:session-expired` window event,
  deduped, rather than a hard mid-flight redirect) and a single `ApiError` shape.
- **Server state is fully on TanStack Query v5**, with query keys centralized in
  `frontend/src/lib/queryKeys.ts` as key-factory functions rather than scattered
  string literals. No competing server-state library.
- **Explicit backend-contract-mirroring discipline already exists in places.**
  `features/pipeline/types.ts` opens with "mirror backend/analysis_pipeline contracts.
  Do not invent fields; see routes.py + models.AnalysisResult.to_api_dict()."
  `features/papers/mappers/shared.ts` enforces "components must not use these against
  raw phase JSON — mappers only." This is exactly the discipline the charter asks for
  everywhere; it just isn't universal yet (see Weaknesses).
- **shadcn/ui on `@base-ui/react`** (not Radix) is consistently used for primitives
  (`components/ui/*`, 27 files), giving a real design-system foundation rather than
  ad hoc styled divs.
- **Feature-sliced folder structure** (`frontend/src/features/<domain>/{api,hooks,components,pages}`)
  is followed consistently across all 25 feature folders — this is the right shape to
  extend, not replace.
- **The best-built features are the most architecturally central ones**: `papers/`
  (13 test files, 9 mapper modules translating raw phase JSON to typed view models)
  and `pipeline/` (typed contract mirror + tests) show the pattern working well when
  followed.
- **Routing has a real error boundary per route** (`errorElement: <RouteErrorFallback />`
  on every route in `router.tsx`) and a working alias/redirect pattern
  (`/files → /library`, `/analysis/compare → /research/compare`) instead of duplicate
  routes.

## Weaknesses / inconsistencies (facts, not yet fixes)

1. **`apiClient` bypass in 6 places.** `features/search/discoverApi.ts`,
   `features/papers/relatedApi.ts`, `features/files/collectionsApi.ts` reimplement
   their own fetch + error parsing. Worse: `features/search/pages/SearchPage.tsx`
   defines an inline `importDiscoverWork()` fetch **directly in the page component**,
   and `features/writing/pages/WritingPage.tsx` has two inline `fetch()` calls. The
   first, `fetch("/api/writing", …)` at line 348, is a genuine duplicate —
   `features/writing/api.ts` already exports `writingApi.transform(action, text)`
   wrapping the identical endpoint/body shape through `apiClient`, so this isn't a
   case the wrapper can't handle, it's just not using the wrapper that already
   exists. The second, `fetch("/api/export/notes", …)` at line 1011, is closer to
   the `chat` case: it's a file-download response, and `writingApi.exportNotes()`
   itself just returns the URL string with a comment ("handled inline in the page")
   acknowledging the wrapper isn't the right shape for a download — a defensible
   choice, not an oversight. `features/chat/api.ts`'s raw fetch is the other
   justified exception (it needs the raw streaming `Response` for `iterateSSE`).
   This is independently flagged in `Now-Status/01-ARCHITECTURE-ASSESSMENT.md` and
   in `docs/epics/EPIC-0004-Writing-Engine.md` (ticket to "replace raw fetch with
   apiClient"), so it's a known, already-scheduled gap, not a new finding.
2. **One misleadingly-named "store" with no implementation.**
   `features/writing/state/writingStore.ts` and `writingSelectors.ts` define only a
   `WritingStoreState` type and an initial-state constant — no `create()`, no
   reducer, no actual store engine. Actual guard logic lives in
   `useWritingWorkspace.ts`, deriving from `UIContext`. Anyone reading the file names
   would reasonably assume a real store exists.
3. **`WritingPage.tsx` is 1,260 lines** — the largest file in the frontend by a wide
   margin (next largest is `PaperKnowledgeGraphTab.tsx` at 836). `DashboardPage.tsx`
   (458 lines, no sub-components) and `SearchPage.tsx` (640 lines, contains its own
   inline fetch helper) are in the same category: large single-file pages that
   haven't been decomposed the way `papers/` and `projects/` have.
4. **Test coverage is skewed toward logic/mapper-heavy features, not the largest
   interactive one.** `papers/` (10 test files) and `pipeline/evidence/analysis/files`
   are well covered. **`chat/` — the single largest feature by component count and
   arguably the most complex interaction (SSE streaming, optimistic sends, outbox) —
   has zero test files.** Also untested: `citations`, `dashboard`, `memory`, `models`,
   `notes`, `profile`, `settings`, `sidebar`, `right-panel`, `support`, `legal`, and
   the routing layer itself.
5. **No dedicated `vitest.config.ts`** — config lives inline in `vite.config.ts` with
   `environment: "node"`, justified in a comment as targeting "plain fetch-wrapping
   functions, not React components." But `@testing-library/react`/`jsdom` are
   dependencies and several `.tsx` test files exist (`AiSections`, `AnalysisOutput`,
   `DomainSelector`, `MetadataInput`, `PaperRelatedTab`, `PaperOverviewPage`,
   `LibraryUploadZone`) — meaning some tests likely override environment per-file.
   Worth clarifying the actual convention before adding more component tests (see
   [10-Risks-And-Questions.md](10-Risks-And-Questions.md)).
6. **No `frontend/src/features/auth` and no client-side auth code at all.** Auth is
   entirely server-side (Flask templates at `/login`, `/logout`, `/auth`), gated by
   `RootLayout.tsx` doing `window.location.replace("/login")` on a failed `useMe()`
   query. This is a deliberate, documented boundary (confirmed by `vite.config.ts`'s
   proxy list and the in-code comment "`/login` is a Flask template route, not a
   React route") — not a gap, just worth stating explicitly since the charter lists
   "Authentication" as out of scope for Developer B in the backend sense, but the
   *client-side* auth gate (`RootLayout`) is squarely frontend-owned.
7. **No shared types folder per domain — a single 556-line `types/api.ts`.** Works
   today, but the new `docs/idd/IDD-0004-Frontend-Contracts.md` §3 and
   `docs/contracts/frontend-contracts/README.md` both specify a *separate*
   `frontend/src/types/idd.ts` as the frozen-type mirror. That file doesn't exist yet.
   See [07-TypeScript-Type-Plan.md](07-TypeScript-Type-Plan.md).
8. **Duplicated shape, not duplicated code, in Card/Panel components.** Six separate
   `*Panel.tsx` components inside `features/projects/` alone
   (`ProjectQuestionsPanel`, `ProjectPapersPanel`, `ProjectNotesPanel`,
   `ProjectInsightsPanel`, `ProjectComparePanel`, `ProjectChatPanel`), plus
   `PipelineStatusPanel`, `EvidenceInspectorPanel`, `RightPanel`,
   `ConnectLibraryPanel`, `CollectionsPanel`, `LibraryDuplicatesPanel` elsewhere —
   no shared `Panel` primitive exists in `components/ui/`. Similarly for "Card"
   (`FileCard`, `MemoryCard`, `ProjectCard`, `SuggestionCards` vs. generic
   `components/ui/card.tsx`). Not necessarily wrong (panels differ in real ways),
   but worth an explicit reuse pass — see [03-Component-Inventory.md](03-Component-Inventory.md).
9. **No route-level code splitting.** `router.tsx` statically imports every page
   component. With `WritingPage.tsx` at 1,260 lines and the papers workspace tabs
   totaling well over 3,000 lines, this is a real (if currently un-measured) initial
   bundle-size question — flagged as a perf item, not yet measured, in
   [05-Frontend-Roadmap.md](05-Frontend-Roadmap.md).

## Accessibility

Not yet audited with tooling (no axe/Lighthouse run performed in this review — that's
an activity, not a documentation fact, and belongs in Sprint work, not Phase 1). What
*is* observable from the code: shadcn/`@base-ui/react` primitives generally carry
better default a11y semantics (focus trapping in `Dialog`/`Sheet`, `Popover`) than
hand-rolled components would. The bespoke chart kit (`components/charts/`, 40+ files,
visx-based) and the bespoke `Sidebar.tsx` (536 lines) are the two areas most likely to
need a manual a11y pass since they're fully custom, not primitive-derived. Recorded as
an open item in [10-Risks-And-Questions.md](10-Risks-And-Questions.md), not assessed
further here.

## Developer experience

- `components.json` shows shadcn is live-configured with a **non-default style**
  (`base-nova`) and a **custom third-party registry** (`@bklit`) — anyone adding a new
  shadcn component needs to know this isn't the vanilla shadcn CLI experience.
- Lint is `oxlint`, not ESLint — fast, but worth confirming rule parity expectations
  before assuming ESLint-plugin ecosystem conventions apply.
- No Storybook or component-explorer found — reusable primitives and feature
  components have no isolated dev/preview surface.

## Verdict

This lines up closely with `Now-Status/01-ARCHITECTURE-ASSESSMENT.md`'s independent
scorecard (~6.8/10 overall, backend-weighted). On the frontend side specifically: the
architecture (feature slices, TanStack Query, typed API layer, shadcn primitives) is
sound and worth extending, not rewriting. The debt is concentrated and identifiable:
raw-fetch bypass in ~6 files, an empty "store" that should be renamed or implemented,
a handful of oversized page files, and a coverage gap on the single most complex
feature (`chat`). None of this requires a redesign — it requires the exact kind of
prioritized, incremental roadmap in [05-Frontend-Roadmap.md](05-Frontend-Roadmap.md).
