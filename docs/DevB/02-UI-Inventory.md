# 02 — UI Inventory

**Status:** Draft for review · Legend: ✅ Complete · 🟡 Partial · ⬜ Placeholder · ❌ Missing

Basis: file presence/size + route wiring in `frontend/src/routes/router.tsx`. "Complete"
means real, non-trivial UI exists and is wired to a route — it does **not** mean
production-hardened, tested, or design-reviewed; see
[01-Frontend-Architecture-Review.md](01-Frontend-Architecture-Review.md) for quality
caveats on specific pages.

| Route | Page component | Status | Notes |
|---|---|---|---|
| `/` (index) | `ProjectsPage` | ✅ | Deliberately the home surface per router comment ("Projects are home — research happens inside a project, not a PDF list") |
| `/home` | `DashboardPage` | 🟡 | 458-line single file, no sub-components, no tests — functional but undecomposed |
| `/chat`, `/c/:conversationId` | `ChatPage` | ✅ | Most built-out interactive feature (SSE streaming, 15 components) but **zero tests** |
| `/projects`, `/projects/:projectId` | `ProjectsPage` / `ProjectDetailPage` | ✅ | `ProjectDetailPage` is 621 lines with 8 panel sub-components — full "project hub" |
| `/library` | `FilesPage` | ✅ | 526-line page, 10 sub-components, Zotero/Mendeley connect flow (`ConnectLibraryPanel`, 595 lines) |
| `/files` | redirect → `/library` | ✅ | Alias, not a duplicate page |
| `/papers/:fileId` | `PaperOverviewPage` | ✅ | 470 lines + test; most complex workspace in the app (13 tab/panel components incl. an 836-line knowledge graph tab) |
| `/papers/:fileId/chat[/:conversationId]` | `PaperChatPage` | ✅ | 363 lines |
| `/research/compare`, `/analysis/compare` (alias) | `MultiPaperAnalysisPage` | ✅ | Thin 21-line wrapper over well-tested `analysis/` feature (4 test files) |
| `/citations` | `CitationsPage` | ✅ | 208 lines, real CRUD, no tests |
| `/notes` | `NotesPage` | ✅ | 308 lines, real CRUD, no tests |
| `/memory` | `MemoryPage` | 🟡 | 61 lines — real but shallow, no tests |
| `/search` | `SearchPage` | 🟡 | 640 lines; functional but contains an inline `fetch()` bypassing `apiClient` (see Architecture Review §Weaknesses 1) |
| `/writing` | `WritingPage` (via `WritingWorkspacePage` re-export) | 🟡 | Largest file in the app (1,260 lines), two inline `fetch()` calls bypassing `apiClient`, misleadingly-named empty "store" backing it |
| `/settings[/:section]` | `SettingsPage` | ✅ | 71 lines + `Sections.tsx`/`DataControlsSection` |
| `/privacy`, `/terms`, `/cookies`, `/about` | `LegalPage` (slug prop) | ✅ | Static copy, one shared component, no duplication |
| `/support` | `SupportPage` | ✅ | 157 lines |
| `*` (catch-all) | redirect → `/` | ✅ | |

## Product-vision pages named in the IDD but not yet routed

Per `docs/idd/IDD-0004-Frontend-Contracts.md` §2 (page-by-page contracts) and
`docs/epics/EPIC-0005-Reviewer.md`, these are named in the contract pack but have
**no corresponding route or page component today**:

| Planned surface | Status | Source |
|---|---|---|
| Reviewer UI (standalone findings/severities view) | ❌ Missing | IDD-0004 §2, EPIC-0005 tickets B-511…B-514 — no `features/reviewer/` folder exists |
| Evidence Inspector as a first-class page (currently only `EvidenceInspectorPanel`, a panel embedded elsewhere) | 🟡 Partial | IDD-0004 §2 describes it as a page-level contract; today it's `features/evidence/components/EvidenceInspectorPanel.tsx` (327 lines) used inline, not a routed page |
| `/trust` page (Trust Center) | ❌ Missing | `Now-Status/05-MIGRATION-ROADMAP.md` Phase 3, `docs/idd/IDD-0010-Future-Extensions.md` — explicitly future, not a current gap |

These are **not bugs** — EPIC-0002 (Evidence Layer UI) and EPIC-0005 (Reviewer) are
both gated on EPIC-0001 sign-off, which per its own status is still "in progress." This
table exists so Sprint planning in
[05-Frontend-Roadmap.md](05-Frontend-Roadmap.md) has an accurate before/after baseline.

## Feature-folder-to-route mismatch, noted not judged

Two feature folders don't map 1:1 to a route: `features/right-panel/` (a persistent
UI element inside `AppShell`, not a page) and `features/ai/`, `features/models/`,
`features/profile/` (small, consumed by other pages rather than routed directly). This
is expected in a feature-sliced structure and isn't a gap.
