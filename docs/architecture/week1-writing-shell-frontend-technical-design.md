# Week 1 Writing Shell Frontend Technical Design Specification (Stage 3)

Status: Planning  
Depends on:  
- `docs/architecture/week1-writing-shell-architecture.md`  
- `docs/architecture/week1-writing-shell-backend-implementation-plan.md`  
Scope: Frontend design and implementation plan only (no backend coding details)

---

## 1) Purpose and Outcomes

This document defines how the Writing Shell frontend should be built for Week 1 so it is:
- project-scoped
- reliable under autosave and reconnect conditions
- secure in tenant-aware flows
- extensible for Evidence/Citation/Reviewer phases

Expected user outcome:
- A researcher can create, open, edit, autosave, version-restore, archive, and recover project documents without silent data loss.

---

## 2) Frontend Delivery Strategy (Slices)

```text
Slice 0: Frontend foundation and module scaffolding
Slice A: Writing workspace shell and routing
Slice B: Document list/lifecycle views
Slice C: Editor state engine and autosave coordinator
Slice D: Version history and restore UX
Slice E: Conflict/recovery/offline behavior
Slice F: Hardening, observability hooks, and release gates
```

Every slice must pass functional, reliability, performance, and accessibility criteria before progressing.

---

## 3) Target Frontend Repository Layout

```text
frontend/src/
  features/writing/
    pages/
      WritingWorkspacePage.tsx
    components/
      DocumentSidebar.tsx
      DocumentList.tsx
      DocumentRow.tsx
      EditorHeader.tsx
      EditorCanvas.tsx
      SaveStatusBadge.tsx
      ConflictBanner.tsx
      VersionHistoryPanel.tsx
      RestoreDialog.tsx
      ArchivePanel.tsx
      TrashPanel.tsx
    hooks/
      useWritingWorkspace.ts
      useDocumentSelection.ts
      useEditorState.ts
      useAutosaveCoordinator.ts
      useVersionHistory.ts
      useConflictResolution.ts
      useOfflineDraftBuffer.ts
    services/
      writingApi.ts
      writingMappers.ts
    state/
      writingStore.ts
      writingSelectors.ts
    types/
      writing.ts
    utils/
      wordCount.ts
      blockTransforms.ts
      errorMap.ts
    tests/
      unit/
      integration/
      e2e/
```

### Component hierarchy (ownership map)

```text
WritingWorkspacePage
  -> EditorHeader
  -> DocumentSidebar
       -> DocumentList
            -> DocumentRow
  -> EditorCanvas
  -> SaveStatusBadge
  -> ConflictBanner
  -> VersionHistoryPanel
  -> RestoreDialog
  -> ArchivePanel
  -> TrashPanel
```

---

## 4) Dependency and Layering Rules

Allowed:

```text
Page -> Feature hooks/state -> Services(API adapters) -> transport client
Page -> Presentational components
Hooks -> Store/selectors
```

Disallowed:

```text
Components -> API calls directly
Pages -> transport client directly
Store -> UI components
Utils -> network calls
```

Implementation policy:
- UI components are presentation-only.
- Feature hooks orchestrate behavior.
- Service layer owns request/response mapping.

---

## 5) Routing and Page Architecture

Primary route model:

```text
Project Workspace
  -> Writing (project-scoped)
     -> default: active document list + editor
     -> archived view
     -> trash view
```

Routing contract:
- Writing page requires active project context.
- No project selected: show guidance state, block create/edit actions.
- Deep-link support for selected document IDs within project scope.

---

## 6) State Architecture

## Server state
- document lists by project and status
- selected document payload
- version history summaries
- restore/action responses

## Client state
- active editor content buffer
- local dirty marker
- autosave queue/in-flight status
- optimistic version token
- conflict and retry UI states

## UI state
- panel visibility (history/sidebar/archive/trash)
- selected filters/sort mode
- transient dialogs (restore confirmation)

Recommendation:
- use query cache for server state and a local feature store for editor/autosave state machine.

### Store ownership contract

Store contains:
- selected document id
- editor dirty state
- autosave status state
- optimistic version token
- conflict/offline recovery state
- version-history cache summaries

Store does not contain:
- API client instances
- transport/network concerns
- rendering components
- backend business rules

---

## 6.1) UI State Machine

```text
loading -> ready -> editing -> saving -> ready
                   \-> conflict
                   \-> offline
offline -> recovering -> ready
```

Rules:
- only one primary UI state active per document context
- transitions are event-driven and testable
- conflict/offline states must preserve local buffer

---

## 7) Domain View Models (Frontend)

Core frontend types:
- `WritingDocumentView`
- `WritingVersionView`
- `AutosaveStateView`
- `ConflictStateView`
- `OfflineRecoveryView`

Mapping rule:
- service layer transforms backend DTOs into view models.
- UI never consumes raw backend payload shapes directly.

---

## 8) Editor Architecture (Block-Ready Week 1)

Week 1 goal is not full block editor features, but the model must be block-ready.

Internal content strategy:
- canonical editor content model supports structured block envelope
- display can start with markdown-like editing surface
- block IDs and metadata slot reserved for future evidence/citation anchors

Initial block-capable envelope:
- block id
- block type
- block payload
- metadata container
- reference container

Why this matters:
- enables future Evidence and Citation insertion without rewriting persistence/UI foundations.

### Rendering architecture

```text
Editor
  -> Document
  -> Blocks
  -> Renderer
  -> Toolbar
  -> Selection model
  -> Plugin host
```

### Plugin architecture

```text
Plugin Host
  -> Evidence Plugin (future)
  -> Citation Plugin (future)
  -> Reviewer Plugin (future)
  -> Comments Plugin (future)
  -> Export Plugin (future)
```

Core rule:
- plugins extend behavior through declared interfaces and do not mutate editor core state directly.

---

## 9) Autosave Coordinator Design

Autosave state machine:

```text
idle -> dirty -> scheduled -> saving -> saved
                         \-> conflict
                         \-> retrying
                         \-> failed
```

Rules:
- debounce user edits (2-3s default)
- one in-flight save per document
- coalesce pending edits while in-flight
- unchanged buffers do not trigger save calls
- include current version token and idempotency key

UI contract:
- explicit badge states: `Saved`, `Saving`, `Retrying`, `Conflict`, `Save failed`

### Hook ownership contract

`useEditorState` owns:
- cursor/selection state
- local block/text buffer
- dirty markers
- editor interaction state

`useEditorState` does not own:
- API transport
- save scheduling
- version history retrieval

`useAutosaveCoordinator` owns:
- debounce scheduling
- in-flight queue control
- retry/backoff policy
- save status state machine

`useAutosaveCoordinator` does not own:
- JSX rendering
- request serialization details
- history rendering

---

## 10) Version History and Restore UX

History panel behavior:
- lazy-load on open
- show version number, timestamp, source
- allow preview metadata before restore

Restore behavior:
- restore action requires explicit confirmation
- post-restore UI must reflect new head version
- notify user that restore creates a new latest version

Failure handling:
- restore conflict/error must preserve current editor buffer and show deterministic next action.

---

## 11) Conflict Resolution UX

Conflict trigger:
- backend returns version conflict with current head metadata

Frontend response:
1. preserve unsaved local content
2. freeze autosave attempts for that document
3. show conflict banner with options:
   - reload latest
   - copy local draft
   - retry with merged/manual decision path

Design principle:
- never silently overwrite user buffer
- never auto-merge without explicit user decision

---

## 12) Offline and Recovery Behavior

Week 1 offline policy:
- best-effort local buffer persistence for unsent edits
- reconnect detection resumes safe save flow
- revalidate version token before replay

Recovery states:
- `offline_buffer_present`
- `reconnect_sync_pending`
- `reconnect_conflict`
- `reconnect_synced`

---

## 13) Lifecycle UX (State Machine on Client)

Document lifecycle states:

```text
draft -> active -> archived -> deleted
```

Client transition controls:
- only render actions valid for current state
- hide/disable invalid transitions
- optimistic UI only after backend confirmation for state transitions

Rejected transition handling:
- surface typed error and refresh state from server source of truth.

---

## 14) API Integration Philosophy (Frontend)

Action-oriented integration:
- create
- open
- save/autosave
- archive
- delete
- restore
- history

Request policy:
- all writes go through service adapters
- request metadata includes correlation/idempotency fields where required
- retry policy only on safe/transient classes

Error policy:
- map backend error taxonomy to user-safe messages and action prompts
- keep developer diagnostics in logs, not in user-facing text

---

## 15) Security and Safety Controls (Frontend)

Controls:
- no cross-project navigation shortcuts that bypass project context checks
- sanitize and escape render paths for rich/editor output
- never store sensitive payloads in long-lived browser storage
- avoid exposing internal IDs in logs visible to non-privileged users
- enforce CSRF-aware request client behavior

Headers and platform assumptions are backend-owned, but frontend must respect safe rendering and storage constraints.

---

## 16) Observability Hooks (Frontend)

Client telemetry events:
- document_opened
- autosave_attempted
- autosave_succeeded
- autosave_failed
- autosave_conflict
- version_restore_started
- version_restore_succeeded
- version_restore_failed

Metrics dimensions:
- project scope
- document state
- latency bucket
- outcome class

Privacy rule:
- never send full document content in telemetry.

---

## 16.1) Frontend Error Boundary Architecture

```text
App Boundary
  -> WritingWorkspace Boundary
       -> Editor Boundary
       -> VersionHistory Boundary
       -> Sidebar Boundary
```

Failure policy:
- if a sub-boundary fails, unaffected regions remain usable.
- show local fallback UI with recovery actions and error correlation id.

---

## 17) Performance Budgets

Budgets:
- workspace initial render: < 800ms p95 (warm client path)
- open document to interactive editor: < 500ms p95
- autosave roundtrip acknowledgment UI update: < 300ms p95
- history panel open: < 400ms p95
- conflict banner render after response: < 100ms

Optimization tools:
- list virtualization
- memoized selectors
- batched state updates
- lazy panels and deferred history loading
- route-level code splitting
- deferred non-critical rendering

---

## 18) Accessibility and UX Quality

Minimum requirements:
- keyboard-first navigation for list/editor/history actions
- semantic labels for save/conflict states
- accessible modal/dialog focus trapping
- adequate contrast for status badges
- screen-reader-friendly error and conflict announcements
- deterministic focus order across panels/dialogs
- live regions for autosave/conflict/recovery status
- reduced-motion compatible transitions
- high-contrast-safe status variants

No release if conflict handling or restore flow is inaccessible.

### Design system consistency rules

- shared spacing scale only
- shared typography tokens only
- approved status colors/badges only
- common button/input/dialog primitives only
- icon usage from unified icon set only

---

## 19) Testing Strategy (Frontend)

Unit (~70%):
- hooks state machines
- selector logic
- mapper and error-map utilities

Integration (~20%):
- writing workspace with mocked backend contracts
- autosave and conflict transitions
- lifecycle action visibility rules

E2E (~8%):
- create/edit/autosave/refresh/reopen
- archive/trash/restore flow
- conflict scenario with dual-session simulation

Manual exploratory (~2%):
- degraded network behavior
- offline/reconnect recovery checks

Security-focused UI tests:
- unsafe render payload handling
- client-side leakage checks in logs/storage

### Contract testing (frontend-backend drift prevention)

Contract test policy:
- frontend fixtures must match backend request/response contracts
- contract fixtures are versioned and reviewed with schema changes
- mapper updates are mandatory for contract changes
- no contract change merges without synchronized fixture updates and regression pass

Adapter strategy:

```text
Backend DTO vN -> Adapter/Mapper -> Frontend ViewModel
```

Frontend must never bind directly to raw DTO internals without adapter coverage.

---

## 20) Slice-by-Slice Implementation Checklists

## Slice 0 checklist
- [ ] module scaffolding
- [ ] feature store baseline
- [ ] shared types and mappers
- [ ] error map policy
- [ ] telemetry wrapper

## Slice A checklist
- [ ] writing workspace route/page
- [ ] project-required guard state
- [ ] shell layout and placeholders
- [ ] tests

## Slice B checklist
- [ ] active/archived/trash lists
- [ ] document selection logic
- [ ] lifecycle action visibility
- [ ] tests

## Slice C checklist
- [ ] editor state hook
- [ ] autosave coordinator
- [ ] save status badge
- [ ] tests and metrics

## Slice D checklist
- [ ] history panel
- [ ] restore flow and dialog
- [ ] post-restore state synchronization
- [ ] tests

## Slice E checklist
- [ ] conflict banner and resolution actions
- [ ] offline buffer/reconnect handling
- [ ] retry policy wiring
- [ ] tests

## Slice F checklist
- [ ] accessibility pass
- [ ] performance budget validation
- [ ] observability verification
- [ ] release gate checklist

---

## 21) Rollback Strategy per Slice

- Slice 0 failure: keep existing writing page and disable new module flag.
- Slice A failure: route fallback to existing writing experience.
- Slice B failure: keep editor enabled with simplified list.
- Slice C failure: disable autosave, keep manual save/edit.
- Slice D failure: disable restore UI, keep editing and history read-only.
- Slice E failure: disable advanced conflict/offline mode, keep conservative refresh prompts.
- Slice F failure: hold release; keep feature behind internal flag.

---

## 22) Frontend Definition of Done (Week 1)

Functional:
- full project-scoped document editing journey works end-to-end with backend contracts.

Reliability:
- no silent data loss on refresh/reconnect in supported flows.
- conflict handling deterministic and user-guided.

Security:
- no unsafe rendering paths; no sensitive content leakage in telemetry/storage.

Performance:
- p95 budgets met for open/autosave/history paths.

Accessibility:
- keyboard and assistive-tech flows pass critical path checks.

Operations:
- telemetry and alert dimensions available for autosave/conflict/recovery flows.

Developer Experience:
- layered dependency rules enforced by lint/review
- hook/service responsibilities documented
- contract fixture workflow documented and followed

Success metrics:
- autosave success >= 99%
- conflict recovery flow completion = 100% in test suite
- silent data-loss incidents = 0
- accessibility target = WCAG AA for critical writing flows

---

## 23) Handoff to Stage 4

After Stage 3 approval:
1. Produce integrated verification and QA specification (Stage 4).
2. Lock frontend-backend contract fixtures for release candidate testing.
3. Begin implementation with slice sequence 0 -> F.

### Developer workflow (execution path)

```text
Feature slice -> hook/service changes -> component wiring -> tests -> story/demo -> PR
```

