# 03 — Component Inventory

**Status:** Draft for review

## Shared UI primitives (`frontend/src/components/ui/`)

shadcn/ui on `@base-ui/react` (not Radix — confirmed via `package.json`, no
`@radix-ui/*` packages). Configured in `frontend/components.json`: style `base-nova`,
base color `neutral`, icon library `lucide`, plus a custom third-party registry
(`@bklit`). 27 primitives exist:

`accordion, alert-dialog, avatar, badge, button, card, collapsible, command (cmdk),
dialog, dropdown-menu, input-group, input, label, popover, progress, scroll-area,
select, separator, sheet, skeleton, slider, sonner (toast), switch, table, tabs,
textarea, tooltip`

**No shared `Sidebar`, `Panel`, or `EmptyState` primitive** — those are hand-built
feature/common components (see below), not part of the shadcn set.

## Cross-cutting shared components (`frontend/src/components/common/`, `layout/`)

- `common/`: `BetaBanner`, `BetaWelcomeModal`, `ConfirmDialog`, `CookieConsent`,
  `EmptyState`, `ErrorBoundary`, `LoadingSpinner`, `ResearchSkeletons`,
  `RouteErrorFallback`, `SessionExpiredModal`, `Toast.ts`
- `layout/`: `AppShell` (composes Sidebar, MobileDrawer, TopBar, RightPanel,
  CommandPalette, BetaBanner, BetaWelcomeModal), `CommandPalette`, `MobileDrawer`,
  `ObjectHeader`, `PageContainer`, `ThemeToggle`, `TopBar`

These are genuinely shared (single implementation, used across features) — the good
pattern to keep extending.

## Bespoke chart kit (`frontend/src/components/charts/`)

40+ files built on `@visx/*` + `d3-array` — **not** shadcn/ui charts, a fully custom
system: `bar-chart.tsx`, `ring-chart.tsx`, `funnel-chart.tsx`, plus
`chart-context.tsx`, `chart-config-context.tsx`, `use-chart-phase-orchestrator.ts`,
animation/tooltip submodules. This is a real, purpose-built visualization system, not
scattered one-off charts — worth knowing about before anyone reaches for a chart
library, since one already exists and is used by dashboard/pipeline surfaces.

## Feature-local reusable components with "same shape, different name" duplication

No literal file duplicates were found. What exists is **parallel, independently-built
implementations of the same conceptual component**, which is the more common and
easier-to-miss form of duplication:

**Card-shaped components** (vs. the generic `components/ui/card.tsx` primitive):
- `features/files/components/FileCard.tsx` (181 lines)
- `features/memory/components/MemoryCard.tsx`
- `features/projects/components/ProjectCard.tsx` (83 lines)
- `features/chat/components/SuggestionCards.tsx`

**Panel-shaped components** (no shared `Panel` primitive exists at all):
- Six separate implementations inside `features/projects/` alone:
  `ProjectQuestionsPanel` (191), `ProjectPapersPanel` (128), `ProjectNotesPanel` (144),
  `ProjectInsightsPanel` (272), `ProjectComparePanel` (39), `ProjectChatPanel` (104)
- `features/pipeline/components/PipelineStatusPanel.tsx`
- `features/evidence/components/EvidenceInspectorPanel.tsx` (327)
- `features/right-panel/components/RightPanel.tsx` (123)
- `features/files/components/{ConnectLibraryPanel(595), CollectionsPanel(214), LibraryDuplicatesPanel(73)}`

**Reuse opportunity (assessment, not yet actioned):** the six `Project*Panel`
components share an implicit shape (header + content + loading/empty/error states)
worth extracting into a single `components/ui/panel.tsx` (or a `layout/Panel.tsx`)
primitive with slots, the same way `card.tsx` already exists generically. This is
recommended, not decided — see [05-Frontend-Roadmap.md](05-Frontend-Roadmap.md) for
where it's sequenced (low urgency: correctness isn't at risk, only DX/consistency).
Doing this *before* EPIC-0002/EPIC-0004 land more Evidence/Writing panels would avoid
compounding the duplication further.

## Loading / empty / skeleton states

- Generic: `components/ui/skeleton.tsx`, `components/common/LoadingSpinner.tsx`,
  `components/common/EmptyState.tsx`, `components/common/ResearchSkeletons.tsx`
  (domain-flavored skeletons, plural — suggests more than one skeleton variant already
  exists for research-specific loading states).
- `features/pipeline/` additionally has its own `PipelineStepper`/`AiStateBadge`/
  `AiStateMixStrip` components representing in-progress/queued/running states — these
  are pipeline-specific status indicators, not generic loading skeletons, and
  shouldn't be collapsed into `ResearchSkeletons`.

## Dialogs / Drawers

- Primitives: `components/ui/{dialog, alert-dialog, sheet, popover, dropdown-menu}`
- Feature dialogs built on those primitives: `CitationFormDialog` (189),
  `NoteDialog` (112), `ProjectDialog` (162), `LibraryImportDialog` (136),
  `ConfirmDialog` (shared, in `common/`)
- Drawer: `components/layout/MobileDrawer.tsx` (the one drawer-shaped component;
  no feature-level drawer duplication found)

## Tables

- Primitive: `components/ui/table.tsx`
- Feature usage: `CitationTable` (198 lines) is the only dedicated table component
  found; other list-shaped UIs (file lists, conversation lists) use custom
  card/list-item layouts rather than `<Table>`, which is a stylistic choice, not
  necessarily inconsistent — worth confirming intent before treating it as debt.

## Evidence / Reviewer / Paper-specific components

- Evidence: `EvidenceInspectorPanel` (327), `ExtractEvidenceButton`
- Reviewer: **none exist** — `features/reviewer/` folder doesn't exist yet (see
  [02-UI-Inventory.md](02-UI-Inventory.md))
- Paper: 13 tab/panel components under `features/papers/components/`, the richest
  single component set in the app, topped by `PaperKnowledgeGraphTab.tsx` (836 lines
  — largest component file in the codebase)

## Summary for reuse planning

The primitive layer (`components/ui/`) is solid and consistently used — no action
needed there. The gap is one layer up: **no shared `Panel` primitive**, and Card-shaped
components are independently built per feature rather than composed from
`components/ui/card.tsx`. Both are flagged as Sprint-level (not urgent) work in
[05-Frontend-Roadmap.md](05-Frontend-Roadmap.md), timed to land before EPIC-0002/0004
add more panels that would otherwise repeat the pattern a seventh and eighth time.
