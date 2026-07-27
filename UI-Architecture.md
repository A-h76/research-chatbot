# Soro UI Architecture

**Product specification:** [Soro Product Spec **v1.0**](PRODUCT-SPEC.md) — Part 2 of 3  
**Document type:** Target product & frontend architecture specification  
**Product:** Soro  
**Audience:** Product, design, frontend engineering  
**Spec version:** 1.0  
**Date:** 2026-07-26  
**Status:** **Locked in Product Spec v1.0** — baseline for implementation (this document is not code)  
**Companions:** [`UI-State.md`](UI-State.md) · [`DESIGN-SYSTEM.md`](DESIGN-SYSTEM.md) · [`docs/DESIGN-SYSTEM-v2.md`](docs/DESIGN-SYSTEM-v2.md) (workstation UX v2 — approve before chrome rewrite)

**Constraint:** Backend Phase 1.1–1.7, Phase 2, PromptBuilder, and Security PR1–PR4 are treated as **stable contracts**. This architecture designs the UI to **reveal** that capability, not reinvent it.

---

# 1. Product Vision

## How Soro should feel

Soro is a **private research instrument**, not a chat box with file attachments.

Emotional / experiential targets:

| Quality | Meaning in product |
|---------|-------------------|
| **Grounded** | Every claim can open evidence, a span, a grade, or a graph node |
| **Inspectable** | Understanding is layered (structure → class → entities → grade → graph → narrative) |
| **Calm** | Dense science, quiet chrome; progress is honest, never theatrical |
| **Owned** | Papers, projects, memories, and exports feel like *my* research OS |
| **Conversational when useful** | Chat is a *mode of inquiry*, not the only home screen |

Primary metaphor: **Paper Workspace** (understand a document) and **Project Studio** (think across documents), with Chat as a rail or mode that always points back to structure.

## Positioning vs competitors

| Product | They optimize for | Soro differentiates by |
|---------|-------------------|-------------------------|
| **ChatGPT** | Fluent general dialogue | Structured private corpus + inspectable pipeline, not generic chat |
| **NotebookLM** | Source-studio / overviews from *your* docs | Deeper scientific structure (PICO, grades, graph) + general agentic chat when needed |
| **SciSpace** | PDF reading + explain-this-paper | Full workspace: projects, memory, writing, multi-paper synthesis, private pipeline |
| **Elicit** | Extraction tables & research workflows | Companion chat + personal library OS, with extraction/grades as first-class panels |
| **Perplexity / Consensus** | Web / literature Q&A with citations | **Private** papers first; citations + grades from *your* uploads |
| **Jenni AI** | Manuscript autocomplete + cite-while-writing | **Evidence-first writing**: grades/entities/graph → claim blocks → draft; see [`docs/soro-vs-jenni-roadmap.md`](docs/soro-vs-jenni-roadmap.md) |

**One-line vision:**  
*Soro turns every uploaded paper into a navigable research object—then lets you talk to it, compare it, and export it—without hiding how the system understood it.*

**Anti-vision (explicitly avoid):**  
A purple chat UI whose “analysis” is only a long markdown essay.

---

# 2. User Personas

## 2.1 Researcher (general academic)

- **Goals:** Build a literature base, extract methods/results, cite accurately, write related work.  
- **Needs:** Fast upload → structure → summary; project folders; export to citation managers.  
- **Success:** “I can open a paper and see what it is, what it claims, and chat against it.”  
- **Risk if UI fails:** Treats Soro as Dropbox + ChatGPT.

## 2.2 Medical / clinical researcher

- **Goals:** PICO, study design, risk of bias, GRADE-like signals, outcome consistency.  
- **Needs:** Evidence panels, confidence, classification (RCT vs review), guideline hints.  
- **Success:** “I can trust or distrust a claim with a grade and a span.”  
- **Risk if UI fails:** LLM medical prose looks authoritative without structure → **unsafe UX**.

## 2.3 Student (thesis / coursework)

- **Goals:** Understand papers, find gaps, draft notes, ask clarifying questions.  
- **Needs:** Plain-language overview *plus* ability to dig deeper; compare 2–5 papers; writing help.  
- **Success:** “I finish a reading list with notes and a gap list.”  
- **Risk if UI fails:** Overwhelmed by 11 nav items and opaque processing.

## 2.4 Knowledge worker (analyst / strategist)

- **Goals:** Cross-document Q&A, synthesis, searchable library, shareable exports.  
- **Needs:** Search + Ask, projects as workstreams, light graph/themes, citations.  
- **Success:** “I ask across my corpus and leave with a cited brief.”  
- **Risk if UI fails:** Can’t find upload; can’t see when docs are “ready.”

### Persona → surface priority

| Surface | Researcher | Medical | Student | Knowledge worker |
|---------|:----------:|:-------:|:-------:|:----------------:|
| Library + upload | ●●● | ●●● | ●●● | ●●● |
| Paper workspace (Phase 1) | ●●● | ●●● | ●● | ●● |
| Evidence / grade | ●● | ●●● | ● | ● |
| Knowledge graph | ●● | ●●● | ● | ●● |
| Chat (paper / global) | ●●● | ●● | ●●● | ●●● |
| Compare / gaps | ●●● | ●● | ●●● | ●● |
| Projects | ●●● | ●●● | ●● | ●●● |
| Writing / export | ●●● | ●● | ●●● | ●●● |

---

# 3. User Journeys

Canonical happy path:

```
Upload paper → Understand paper → Explore evidence → Chat → Compare papers → Projects → Export
```

## 3.1 Upload paper

**Intent:** Get files into the corpus with clear ownership (Library is the home).

**Steps**
1. Enter **Library** (or Dashboard “Add papers”).  
2. Drop files / pick files (single or bulk).  
3. See queue: validation → storage → **Phase 1 pipeline** → optional LLM overview.  
4. Open first Ready paper into **Paper Workspace**.

**States:** validating · uploading · queued · running phases · ready · failed (with retry).  
**Outcomes:** `UserFile` + pipeline row; Library badge updates.

## 3.2 Understand paper

**Intent:** Know *what this document is* before chatting.

**Steps**
1. Land on Paper Workspace **Overview** (biblio + readiness).  
2. Open **Structure** (sections, quality).  
3. Open **Classify** (type, domain, design, guidelines + confidence).  
4. Skim **Overview** narrative (LLM) only after structure is Ready (or in parallel with clear labels).

**Outcome:** User can answer: genre, domain, quality caveats, main sections.

## 3.3 Explore evidence

**Intent:** Inspect claims/grades/entities—not just prose.

**Steps**
1. **Entities** tab (PICO / medical / stats as available).  
2. **Evidence** tab (grades, RoB, consistency; confidence).  
3. Optional **Graph** for relationships.  
4. Click row → provenance (phase, span/section if present).

**Outcome:** Trust calibration; notes pinned from evidence rows.

## 3.4 Chat

**Intent:** Ask questions *against* understanding.

**Modes**
- **Paper chat:** grounded in one file; evidence rail shows Phase 1 + RAG chunks.  
- **Global chat:** corpus/project scoped; same rail patterns.

**Outcome:** Answers with inspectable sources; optional “save citation / note.”

## 3.5 Compare papers

**Intent:** Synthesis across N papers.

**Steps**
1. Multi-select from Library or Project → **Compare**.  
2. Or open **Research → Compare & gaps**.  
3. Review compare / gaps outputs; jump back to per-paper Evidence.

**Outcome:** Shared themes, contradictions, gap list for thesis/writing.

## 3.6 Projects

**Intent:** Long-lived research containers.

**Steps**
1. Create/open project.  
2. Attach papers / chats / notes.  
3. Use project-scoped search, compare, and (later) project graph summary.

**Outcome:** Workstream continuity.

## 3.7 Export

**Intent:** Leave with artifacts.

**Paths:** Citation export · analysis/export dossier · writing outputs · notes.  
**Outcome:** BibTeX/APA/IEEE, markdown/PDF briefs, writing drafts.

### Journey friction to design out (from audit)

| Friction | Architecture response |
|----------|----------------------|
| Upload only in Composer | Library is primary upload surface; Composer attach remains secondary |
| Opaque processing | Pipeline stepper + phase names everywhere Ready matters |
| Analysis = markdown only | Paper Workspace tabs; LLM overview is one tab |
| Nav overload | Grouped IA (see §4) |

---

# 4. Information Architecture

## 4.1 Design principles

1. **≤5 primary destinations** in the default sidebar.  
2. **Paper Workspace** is hierarchical (tabs), not 7 top-level routes.  
3. **Research tools** (compare, search, writing) nest under Research or overflow.  
4. **Chat is always one click away**, not the only organizing principle.  
5. One brand: **Soro** everywhere in product chrome.

## 4.2 Desktop navigation hierarchy

```
Soro
├── Home                         → /
├── Library                      → /library  (alias today’s /files)
│     └── [paper]                → /papers/:id/*  (workspace)
├── Projects                     → /projects
│     └── [project]              → /projects/:id
├── Chat                         → /chat , /c/:conversationId
└── Research ▾                   (group)
      ├── Search                 → /search
      ├── Compare & gaps         → /research/compare
      ├── Citations              → /citations
      ├── Writing & export       → /writing
      ├── Notes                  → /notes
      └── Memory                 → /memory
Settings                         → /settings
Account                          (menu)
```

**Secondary / utility (not primary nav):** Legal, Support (footer / account).

## 4.3 Sidebar structure (desktop)

| Zone | Contents |
|------|----------|
| **Brand** | Soro wordmark |
| **Primary** | Home, Library, Projects, Chat |
| **Research** | Collapsible group (Search, Compare, Citations, Writing, Notes, Memory) |
| **Recents** | Recent papers + recent chats (compact) |
| **Footer** | Settings, Account |

Default expanded: Primary only. Research collapsed for students; power users can pin.

## 4.4 Mobile navigation

- **Bottom bar (4):** Home · Library · Chat · More  
- **More sheet:** Projects, Research group, Settings, Account  
- Paper Workspace: tab strip becomes **horizontal scroll** or **“Sections” sheet**  
- No persistent 3-pane; Evidence rail becomes a **bottom sheet**

## 4.5 Paper workspace hierarchy

```
/papers/:fileId
├── Overview          biblio, readiness, LLM executive summary
├── Structure         document understanding
├── Classify          classification (+ analysis context summary)
├── Entities          medical / PICO / stats
├── Evidence          evidence grading
├── Graph             knowledge graph
├── Narrative         full LLM paper analysis (legacy accordion, renamed)
└── Chat              /papers/:fileId/chat[/:conversationId]
```

**URL strategy (recommended):**  
`/papers/:fileId?tab=evidence` or `/papers/:fileId/evidence` — pick one scheme and stick to it (query tabs are easier for incremental migration).

## 4.6 Project hierarchy

```
/projects/:projectId
├── Overview          progress, counts, readiness mix
├── Papers            scoped library
├── Chats             scoped conversations
├── Notes             scoped notes
├── Insights          compare/gaps shortcuts + (later) project graph
└── Settings          instructions, members (future)
```

---

# 5. Screen Inventory

Every screen in the target architecture (includes evolved existing screens).

| Screen ID | Route | Purpose | Responsibilities | Nav in / out |
|-----------|-------|---------|------------------|--------------|
| **Home** | `/` | Orientation | Stats, “continue,” upload CTA, Ready/Needs-attention | → Library, Chat, Paper |
| **Library** | `/library` | Corpus home | Upload, filters, pipeline badges, multi-select → Compare | → Paper, Compare, Project attach |
| **Paper · Overview** | `/papers/:id` | Entry to understanding | Biblio, status stepper, CTA to deeper tabs | ↔ other tabs, Chat |
| **Paper · Structure** | tab | DU | Sections, quality, language, warnings | ↔ |
| **Paper · Classify** | tab | Pass1/2 + context | Labels, confidence, analysis-context summary | ↔ |
| **Paper · Entities** | tab | Medical understanding | PICO/entities/stats lists | ↔ Evidence, Graph |
| **Paper · Evidence** | tab | Grading | Grade matrix, RoB, confidence | ↔ Viewer highlight |
| **Paper · Graph** | tab | KG | Read-only graph + node detail | ↔ Entities |
| **Paper · Narrative** | tab | LLM analysis | Existing AnalysisOutput experience | ↔ Chat |
| **Paper · Chat** | `/papers/:id/chat…` | Grounded Q&A | Stream + evidence rail | → Citations/Notes |
| **Chat · Welcome** | `/chat` | Start dialogue | Prompts, attach (secondary upload) | → `/c/:id` |
| **Chat · Thread** | `/c/:id` | Global chat | Stream, right rail, model controls | → Papers via sources |
| **Projects list** | `/projects` | Workstreams | CRUD | → Detail |
| **Project detail** | `/projects/:id` | Scoped studio | Papers/chats/notes/insights | → Paper, Compare |
| **Search** | `/search` | Find + Ask | Filters, hits, RAG ask | → Paper |
| **Compare & gaps** | `/research/compare` | Multi-paper | Selection, compare/gaps tabs | → Paper evidence |
| **Citations** | `/citations` | Reference mgr | CRUD, formats, export | ← Paper |
| **Notes** | `/notes` | Capture | CRUD, file filter | ← Evidence pin |
| **Memory** | `/memory` | Long-term facts | Edit/forget; explain source | ← Chat |
| **Writing & export** | `/writing` | Produce artifacts | Writing actions + exporters | ← Paper/Project |
| **Settings** | `/settings/*` | Preferences | Appearance, models, privacy, advanced prompts | — |
| **Session expired** | modal | Auth recovery | Explain idle/absolute TTL | → Login |
| **Legal / Support** | public | Compliance | Static / form | Footer |

**Deprecated as top-level (absorbed):** today’s flat 11-item sidebar labels; “Multi-Paper Analysis” renamed under Research.

---

# 6. Data Flow

## 6.1 Frontend ↔ backend map

| UI concern | Backend contract |
|------------|------------------|
| Auth session | Cookie session; handle `401 session_expired` |
| Upload | `POST /api/files`, `POST /api/documents/upload`, `POST /api/uploads/bulk`, batch status |
| Phase 1 run | `POST /api/documents/:id/analyze` (`?sync=1` optional) |
| Phase 1 read | `GET /api/documents/:id/pipeline`, `GET …/phases/:phase` |
| LLM narrative | `GET/POST …/analysis` (existing) |
| Chat | `POST /api/chat` SSE |
| RAG / search | `POST /api/search`, `POST /api/rag` |
| Compare / gaps | existing `/api/analysis/compare*`, `/gaps*` |
| Citations / notes / memory / projects | existing REST |

Phase keys (from pipeline):  
`document_understanding` · `classification` · `analysis_context` · `medical_understanding` · `evidence_grading` · `prompt_assembly` · `knowledge_graph`

## 6.2 How Phase 1 APIs appear in UI

```
Library / Paper header
    │
    ├─ POST /analyze          → start or refresh Phase 1
    ├─ poll job / GET pipeline → PipelineStatus model
    │
    └─ Tabs bind to GET /phases/:phase
           Structure  ← document_understanding
           Classify   ← classification (+ analysis_context summary)
           Entities   ← medical_understanding
           Evidence   ← evidence_grading
           Graph      ← knowledge_graph
           (prompt_assembly: advanced/debug, not primary tab)
```

**Narrative tab** remains on LLM analysis endpoints—**labeled** “AI overview,” not “understanding.”

## 6.3 Pipeline status flow

```
Upload success
  → enqueue import (+ phase1_analysis on worker path)
  → UI subscribes: batch status and/or file meta + pipeline GET
  → derive UI status: idle | queued | running(phase) | ready | error
  → badges on Library cards + Paper stepper
  → on ready: enable Evidence/Graph tabs; soft-prompt Chat
```

## 6.4 Chat flow

```
User message
  → POST /api/chat (SSE)
  → stream deltas to message store
  → on done: sources → Evidence rail
  → optional: if paper-scoped, prefetch GET /pipeline summary for rail chips
  → user opens source → Paper tab + highlight if span available
```

PromptBuilder stays **server-side**; UI does not expose assembly internals by default (optional Settings → Advanced).

---

# 7. State Management

Architectural state domains (implementation-agnostic: React Query + lightweight UI stores recommended).

## 7.1 Global app state

- Auth/me  
- Theme  
- Sidebar collapsed / Research group open  
- Active project scope (optional filter chip)  
- Toasts / modal stack (session expired, confirms)

## 7.2 Per-paper state

- File record  
- Pipeline document (`pipeline` payload + per-phase cache)  
- Pipeline UI status  
- Active tab  
- LLM analysis document  
- Viewer cursor (page/section id)  
- Local UI: selected evidence row, selected graph node  

**Cache key shape (conceptual):** `paper(id)`, `pipeline(id)`, `phase(id, name)`, `analysis(id)`.

## 7.3 Project state

- Project record  
- Scoped paper/chat/note lists  
- Insights shortcuts (compare selection defaults)

## 7.4 Streaming state

- Per-conversation: connection, abort controller, partial assistant message, status events, sources  
- UI flags: isStreaming, canStop, error  

Isolated from pipeline state (different lifetimes).

## 7.5 Upload state

- Queue items: localFile → server ids → batchId  
- Per-item validation errors (MIME/virus messages)  
- Progress pollers for bulk batches  

## 7.6 Pipeline state

Machine per `fileId`:

| State | Meaning |
|-------|---------|
| `absent` | No pipeline row |
| `queued` | Job pending |
| `running` | Phase in progress (optional phase name) |
| `ready` | Usable Phase 1 JSON |
| `stale` | File changed / user requested re-run |
| `error` | Failed; retry available |

---

# 8. Component Hierarchy

Architecture-only — **no visual design**. Names are logical modules.

```
AppShell
├── SidebarNav
│     ├── PrimaryNav
│     ├── ResearchNavGroup
│     └── RecentsList
├── TopBar
│     ├── ContextTitle
│     ├── ProjectScopeChip
│     └── AccountMenu
└── MainOutlet
      ├── HomePage
      ├── LibraryPage
      │     ├── UploadZone
      │     ├── PipelineBadge
      │     ├── FileCard
      │     └── ProcessingQueueDrawer
      ├── PaperWorkspace
      │     ├── PipelineStepper
      │     ├── PaperTabNav
      │     ├── DocumentViewerHost      (structure/PDF host)
      │     ├── StructurePanel
      │     ├── ClassificationPanel
      │     ├── EntitiesPanel
      │     ├── EvidencePanel
      │     ├── KnowledgeGraphPanel
      │     ├── NarrativePanel          (wraps existing analysis output)
      │     └── PaperChatLayout
      │           ├── MessageStream
      │           ├── Composer
      │           └── EvidenceRail
      ├── ChatLayout
      │     ├── MessageStream
      │     ├── Composer
      │     └── EvidenceRail
      ├── ProjectStudio
      ├── SearchPage
      ├── CompareGapsPage
      ├── CitationsPage
      ├── NotesPage
      ├── MemoryPage
      ├── WritingPage
      └── SettingsPage

Shared cross-cutting
├── ConfidenceIndicator
├── EmptyState / ErrorState / SkeletonState
├── SessionExpiredModal
├── ErrorBoundary
└── ConfirmDialog
```

**Reuse rules**
- `EvidenceRail` shared by global and paper chat.  
- `PipelineBadge` / `PipelineStepper` shared by Library and Paper.  
- `NarrativePanel` reuses current analysis markdown pipeline initially.  
- Graph/Evidence panels consume phase JSON adapters—**no** markdown conversion for Phase 1.

---

# 9. Responsive Strategy

## Desktop (≥1280px)

- AppShell: Sidebar + Main (+ optional right rail on chat/paper-chat).  
- Paper Workspace: optional **split**—viewer left / panel right when Structure/Evidence active.  
- Compare: wide two-column results.

## Tablet (768–1279px)

- Collapsible sidebar (icon rail).  
- Paper tabs scroll horizontally.  
- Viewer and panel stack (panel full-width under viewer).  
- Evidence rail → dismissible sheet.

## Mobile (&lt;768px)

- Bottom nav (Home, Library, Chat, More).  
- Paper Workspace: one panel at a time; “Document” as separate sheet.  
- Upload: full-screen drop / system picker.  
- Graph: simplified list/neighborhood view before full canvas (progressive enhancement).  
- Prefer vertical timelines over wide tables; Evidence matrix → card list.

### Responsive priorities

1. Don’t hide upload on small screens.  
2. Don’t require hover to reach Evidence.  
3. Chat composer always reachable on Chat and Paper Chat.

---

# 10. Implementation Roadmap

PR-sized milestones. Each is **reviewable alone**, ships user-visible value or a hard foundation, and avoids big-bang rewrites.

| ID | Milestone | Scope | Depends on | Exit criteria |
|----|-----------|-------|------------|---------------|
| **M0** | IA shell rename | Sidebar groups (Primary + Research), route aliases (`/library`→files), brand string pass | — | Nav matches §4; no feature regressions |
| **M1** | Pipeline API client | Types + `analyze` / `pipeline` / `phases` hooks; React Query keys | — | Can fetch/display raw phase JSON in a **dev-only** panel on paper page |
| **M2** | Library upload | Upload zone on Library; reuse bulk progress; composer attach unchanged | — | Users can upload without opening Chat |
| **M3** | Pipeline status UX | `PipelineBadge` + stepper; wire worker/job/pipeline status | M1 | Library/Paper show Ready/Running/Error |
| **M4** | Paper tabs shell | Tab nav + URL; move existing overview/narrative into tabs | M0 | Old paper page reachable as Overview + Narrative |
| **M5** | Document Understanding | Structure tab bound to `document_understanding` phase JSON | M1, M4 | Structure shows sections/quality/warnings when Ready |
| **M6** | Classification | Classify tab (+ analysis context summary) | M1, M4 | Non-empty Ready papers show labels/confidence |
| **M7** | Entities | Medical / PICO / stats panel via domain-neutral `mapEntities()` | M1, M4 | Entities visible without markdown |
| **M8** | Evidence | Evidence grading panel via `mapEvidence()`; confidence indicator | M1, M4 | Grades/RoB visible without markdown |
| **M9** | Knowledge Graph | Read-only graph via `mapKnowledgeGraph()` | M1, M4 | Graph tab renders nodes/edges for Ready papers |
| **M10** | Explainable Chat | `mapExplainableChat` + `WorkspaceReference` rail; navigate into M5–M9 tabs | M3–M9 | Paper chat answers + workspace refs; tabs own rendering |
| **M11** | Session + errors | Session expired modal; app ErrorBoundary | Security PR4 | No silent hard bounce without copy |
| **M12** | Polish / a11y | Labels, skip link, remove dead components | M0+ | Audit items from UI-State closed |
| **M13** | Compare → writing seed | Compare/gaps outline export with `WorkspaceReference[]` | M8, M10 | Outline → Writing; refs open paper tabs |
| **M14** | Evidence-linked claims | `ClaimBlockViewModel` from Evidence/Entities/Chat | M7–M10 | Insert claim carries grade + refs; no invented refs |
| **M15** | Writing Studio MVP | `/writing` compose from claims + outlines; `.md` export | M13–M14 | Defensible draft home (not a Docs clone) |
| **M16** | Citations CSL + Zotero | Core CSL styles; BibTeX; Zotero file import; cite in draft | M15 | Switcher table-stakes vs Jenni citations |
| **M17** | Grounded autocomplete | Suggestions only from selected library evidence | M15–M16 | Every accept has refs (or explicit ungrounded warn) |
| **M18** | Manuscript review | Unsupported / weak / conflict checks vs Evidence VMs | M8, M15–M16 | Review deep-links to claims + Evidence |
| **M19** | Stretch export/collab | `.docx`/LaTeX; collab; live Zotero (optional) | M16 | Only after cite/write loop is solid |

**Competitive track detail:** [`docs/soro-vs-jenni-roadmap.md`](docs/soro-vs-jenni-roadmap.md) — positioning vs Jenni AI, ViewModel reuse contract, acceptance criteria.

### Sequencing diagram

```
M0 ──┬── M2
     ├── M1 ── M3 ── M4 ──┬── M5 ── M6 ── M7 ── M8 ── M9 ── M10
     │                    └── (viewer)
     ├── M11 → M12
     └── M8+M10 ── M13 ── M14 ── M15 ── M16 ── M17 ── M18 ── (M19)
```

### Explicit non-goals per early milestones

- No PromptBuilder UI redesign (M0–M8).  
- No admin analytics UI.  
- No enforced CSP visual work.  
- No mobile graph canvas perfection before M7 list fallback.  
- No Jenni-style autocomplete before M15–M16 (evidence-linked claims first).  
- No invented citations in chat or writing.

### Definition of done (architecture program)

A new user can: **upload in Library → watch phases → inspect Structure/Classify/Evidence/Graph → chat with an evidence rail → compare → write a grounded draft → export**—without opening Settings or reading API docs.

---

# Appendix A — Mapping current → target

| Current | Target |
|---------|--------|
| `/files` | `/library` (alias) |
| `/papers/:id` monolithic | Paper Workspace tabs |
| `/analysis/compare` | `/research/compare` (alias OK) |
| Composer-only upload | Library primary + Composer secondary |
| `AnalysisOutput` as “the analysis” | Narrative tab only |
| 11 sidebar items | 4 primary + Research group |

# Appendix B — API phase → tab binding

| Phase key | Primary tab | Secondary |
|-----------|-------------|-----------|
| `document_understanding` | Structure | Overview readiness |
| `classification` | Classify | Library filters (future) |
| `analysis_context` | Classify (summary strip) | Advanced |
| `medical_understanding` | Entities | Evidence links |
| `evidence_grading` | Evidence | Chat rail |
| `knowledge_graph` | Graph | Project insights (future) |
| `prompt_assembly` | Advanced / hidden | Devtools |

---

*End of Soro UI Architecture — specification only; no code generated.*
