# UI-State.md

**Product specification:** [Soro Product Spec **v1.0**](PRODUCT-SPEC.md) — Part 1 of 3  
**Document type:** Frontend + UX architecture audit (current state)  
**Product:** Soro  
**Audience:** Product, design, frontend, and leadership  
**Spec version:** 1.0  
**Audit date:** 2026-07-26  
**Method:** Code inspection of `frontend/` only — no implementation, no code changes  
**Backend context:** Phase 1.1–1.7, Phase 2 integration, PromptBuilder, security hardening are complete; frontend largely does not surface them  
**Companions:** [`UI-Architecture.md`](UI-Architecture.md) · [`DESIGN-SYSTEM.md`](DESIGN-SYSTEM.md)

**Branding note:** UI shell brands as **Soro**; login/legal/support and some copy still say **Personal AI** / **Research Workspace**. Same app.

---

# 1. Executive Summary

Soro’s frontend is a competent **research workspace shell**: chat-first streaming, library, projects, citations, notes, memory, search/RAG, writing/export, and multi-paper compare/gaps. Visually it is a polished dark-default SPA (Creato Display + purple accent + shadcn/Tailwind).

The strategic gap is severe: the **backend now understands documents structurally** (sections, classification, medical entities, evidence grades, knowledge graphs, analysis context, prompt assembly), but the **UI still presents a legacy LLM “paper overview” markdown accordion**. Users cannot inspect *why* the system believes something, see confidence, walk a knowledge graph, or open Phase 1 phase results. Upload is buried in the chat composer. There is no dedicated document viewer, no pipeline progress beyond bulk job status, and no explainability surfaces.

**Verdict:** Strong chat/productivity UX for a personal research assistant; **weak AI research product UX** relative to the engine already running behind it. Closing the Phase 1 surface area is the highest-leverage product work left.

---

# 2. Scorecard

| Dimension | Score | Rationale |
|-----------|------:|-----------|
| **Current UX** | **6.0 / 10** | Coherent workspace journeys for chat/library/projects; friction on upload, processing transparency, and analysis depth |
| **Visual Design** | **7.0 / 10** | Distinct type, consistent tokens, dark mode; purple-on-dark is familiar AI-assistant vernacular; card-heavy dashboard |
| **Information Architecture** | **5.5 / 10** | 11+ top-level nav items; analysis intelligence hidden; upload not on Library; brand inconsistency |
| **AI Explainability** | **2.5 / 10** | Chat sources chips + search % match only; Phase 1 evidence/confidence/KG/classification invisible |
| **Production Readiness (frontend)** | **5.5 / 10** | Core flows work; missing Phase 1 UI, a11y gaps, dead components, no React error boundary, no admin UI |

**Overall product–frontend readiness for “AI research OS” promise: ~4.5 / 10**  
**Overall readiness as “personal research chat + library”: ~6.5 / 10**

---

# 3. Phase 1 Feature Coverage

Legend: stars = quality of that layer; **User value** = value *if exposed well*.

| Capability | Backend | Frontend | Visible | Useful today | Discoverable | Production UI | Notes |
|------------|---------|----------|---------|--------------|--------------|---------------|-------|
| **1.1 Document Understanding** | ★★★★★ | ★☆☆☆☆ | No | Latent | No | No | Sections/quality/meta exist server-side; UI only shows bibliographic fields on `UserFile` |
| **1.2 Classification** | ★★★★★ | ☆☆☆☆☆ | No | Latent | No | No | No types, no `/pipeline` or `/phases` calls |
| **1.3 Analysis Context** | ★★★★★ | ☆☆☆☆☆ | No | Latent | No | No | Invisible |
| **1.4 Medical Understanding** | ★★★★★ | ★☆☆☆☆ | Partial* | Misleading* | Low | No | *LLM narrative medical strings in markdown ≠ structured extractors |
| **1.5 Evidence Grading** | ★★★★★ | ☆☆☆☆☆ | No | Latent | No | No | LLM `grade_assessment` text only |
| **1.6 Prompt Assembly** | ★★★★★ | ☆☆☆☆☆ | No | Latent | No | No | Settings “AI Prompts” is admin/prompt-registry, not research AssembledPrompt |
| **1.7 Knowledge Graph** | ★★★★★ | ☆☆☆☆☆ | No | Latent | No | No | Zero graph UI |
| **Phase 2 pipeline APIs** (`/analyze`, `/pipeline`, `/phases/*`) | ★★★★★ | ☆☆☆☆☆ | No | Latent | No | No | Not in `files/api.ts` |
| **LLM Paper Analysis** | ★★★★☆ | ★★★★☆ | Yes | High | Medium | Yes | `PaperOverviewPage` + `AnalysisOutput` |
| **PromptBuilder chat** | ★★★★★ | ★★★★☆ | Indirect | High | N/A | Yes | Streaming chat works; users don’t see assembly |
| **RAG / Search** | ★★★★☆ | ★★★★☆ | Yes | High | Medium | Yes | `% match` score shown |
| **Citations** | ★★★★☆ | ★★★★☆ | Yes | High | Yes | Yes | Cards + export formats |
| **Compare / Gaps** | ★★★★☆ | ★★★☆☆ | Yes | High | Medium | Partial | Solid page; not linked from paper overview strongly |
| **Chat streaming** | ★★★★★ | ★★★★☆ | Yes | High | Yes | Yes | No tool-call inspector |
| **Upload / bulk** | ★★★★★ | ★★☆☆☆ | Partial | High | Low | Partial | Composer-only; Library has no upload CTA |
| **Security hardening** | ★★★★★ | ★★☆☆☆ | Indirect | N/A | No | N/A | Session expiry → hard redirect; no UX copy for `session_expired` |

### Rating vignettes (requested style)

**Document Understanding**  
Backend: ★★★★★ · Frontend: ★☆☆☆☆ · User value: **Low (today)** — capability exists but is invisible; value would be **High** if surfaced.

**Evidence Grading**  
Backend: ★★★★★ · Frontend: ☆☆☆☆☆ · **Missing**

**Knowledge Graph**  
Backend: ★★★★★ · Frontend: ☆☆☆☆☆ · **Missing** (not even a prototype in SPA)

**Classification**  
Backend: ★★★★★ · Frontend: ☆☆☆☆☆ · **Missing**

**Medical Understanding (structured)**  
Backend: ★★★★★ · Frontend: ★☆☆☆☆ · **Prototype-adjacent only via LLM markdown**

**Paper Analysis (LLM overview)**  
Backend: ★★★★☆ · Frontend: ★★★★☆ · User value: **High** — primary analysis surface today

---

# 4. Complete Screen Inventory

Auth gate for AppShell routes: `RootLayout` + `useMe` → unauthenticated users redirected to Flask `/login` (not a React route).

| Route | Purpose | Primary components | Hierarchy | Problems | Missed opportunities |
|-------|---------|-------------------|-----------|----------|----------------------|
| `/` | Dashboard home | `DashboardPage`, stat cards, recent lists | Stats → recent papers/chats/citations/projects | Card grid noise; doesn’t surface “needs analysis” or pipeline status | “Research pulse”: papers awaiting Phase 1 / analysis; confidence alerts |
| `/chat`, `/c/:id` | General AI chat | `WelcomeView`, `ConversationView`, `Composer`, `MessageList`, `RightPanel` | Composer-centric | Tool calls invisible; upload only here | Attach → auto-open paper workspace |
| `/files` | Knowledge library | `FilesPage`, `FileCard` | Filters → grid | **No upload**; empty state points to chat | Primary upload + processing queue |
| `/papers/:fileId` | Paper overview | metadata, `DomainSelector`, `MetadataInput`, `AnalysisOutput` | Meta → analyze CTA → markdown accordion | No Phase 1; no PDF viewer; analysis = LLM only | Tabbed “Understand / Grade / Graph / Chat” |
| `/papers/:id/chat…` | Paper-grounded chat | `PaperChatPage`, shared chat stack | Paper header → messages | Search/memory forced off (OK) without explaining why | Cite-from-passage; evidence drawer |
| `/analysis/compare` | Multi-paper compare + gaps | `MultiPaperAnalysisPage` | Select papers → tabs | Separated from single-paper IA | Entry from project + library multi-select |
| `/projects`, `/projects/:id` | Project workspace | cards, progress, scoped lists | List → detail | Weak link to analysis intelligence | Project-level evidence synthesis |
| `/citations` | Citation manager | cards, form dialog, format tabs | List CRUD | `CitationTable` dead | Inline cite from chat/paper |
| `/notes` | Notes | list + dialog | CRUD | Secondary to chat | Note ↔ evidence anchors |
| `/memory` | Long-term memory | `MemoryCard`, stars | List edit/delete | No create; opaque how memories appear | “Why I remember this” + source chat |
| `/search` | Corpus search + Ask AI | filters, results, RAG panel | Search → results → Ask | Dual modes can confuse | Unified “Ask with citations” |
| `/writing` | Writing assist + export | actions + exporters | Tools list | Feels bolted-on | Writing grounded in Phase 1 PICO/GRADE |
| `/settings`, `/settings/:section` | Preferences | sectioned settings, AI prompts | Many sections | Prompt admin ≠ research UX | Hide prompt engine from default users |
| `/privacy` `/terms` `/cookies` `/about` | Legal | `LegalPage` | Static | Outside shell | Brand alignment |
| `/support` | Support | FAQ + form | Form | Fine | In-app ticket status |

---

# 5. User Journey & Friction

```
Landing (none in SPA) → Flask Login → Dashboard → Upload(?) → Processing(?) → Analysis → Chat → Projects → Search → Export
```

| Step | Current state | Friction |
|------|---------------|----------|
| **Landing** | No marketing SPA; jump to login | Brand/story not established in React |
| **Login** | Server-rendered OAuth/magic/dev | Theme/brand mismatch with SPA; session expiry dumps to `/login` without friendly SPA state |
| **Dashboard** | Stats + recents | Doesn’t teach the research workflow or Phase 1 value |
| **Upload** | Composer attachments / bulk progress | Users looking at Library cannot upload; discoverability fail |
| **Processing** | `meta_status` / bulk batch poll | No phase timeline (DU → classify → medical → grade → KG); “still processing” is opaque |
| **Analysis** | LLM markdown on paper page | Looks like a chatbot summary, not a research instrument; no confidence/evidence links |
| **Chat** | Excellent streaming | Hard to connect answers to Phase 1 structure; no tool inspector |
| **Projects** | Functional | Not the home of multi-paper intelligence |
| **Search** | Good | RAG answers lack deep evidence panels |
| **Export** | Writing page | Easy to miss; not “Export dossier” from paper |

**Top journey killers**
1. Upload not on Library  
2. Phase 1 invisible after upload  
3. Analysis page sells the wrong artifact (LLM prose vs structured understanding)  
4. 11-item sidebar buries Multi-Paper and Writing  
5. Branding split (Soro vs Personal AI)

---

# 6. Visual Design Evaluation

| Area | Score /10 | Notes |
|------|----------:|-------|
| Typography | 8 | Creato Display is distinctive; good display/body contrast |
| Spacing | 7 | Generally generous; some dense settings/analysis forms |
| Hierarchy | 6 | Uppercase micro-labels help; dashboard stats compete with content |
| Cards | 6 | Default pattern everywhere; hero moments rare |
| Tables | 4 | Table component exists; citations abandoned table for cards |
| Charts | 2 | No charting for evidence/confidence/trends |
| Icons | 7 | Lucide consistent |
| Color | 6 | Purple primary (`#7c3aed`) — competent but generic AI palette; dark default `#212121` |
| Contrast | 7 | Mostly OK; muted labels can be thin on dark |
| Consistency | 7 | shadcn tokens help; brand strings don’t |
| Navigation | 5 | Overloaded sidebar |
| Professional appearance | 7 | Looks like a real product; not yet like a scientific instrument |

---

# 7. AI UX / Explainability

| Question | Answer |
|----------|--------|
| Understand **why** an answer was produced? | **Mostly no** — chat may show source chips; no reasoning/trace UI |
| Inspect **evidence**? | **No** structured evidence objects; only markdown claims |
| Inspect **citations**? | **Yes** — dedicated manager + save-from-paper |
| Inspect **confidence**? | **Almost no** — search similarity only; no Phase 1 confidence |
| Inspect **document understanding**? | **No** |
| Inspect **classification**? | **No** |
| Inspect **knowledge graph**? | **No** |
| Inspect **reasoning**? | **No** (no chain-of-thought / phase audit panel) |

**What is missing (concrete)**
- Types + API clients for `/pipeline` and `/phases/*`  
- Paper workspace tabs: Overview · Structure · Classification · Entities · Evidence · Graph · Chat  
- Confidence badges and “open supporting span”  
- Graph canvas (even read-only node-link)  
- Chat “Evidence” drawer binding RAG hits ↔ file offsets  
- Processing timeline with phase status from pipeline job  

Without these, Soro **feels** like ChatGPT-with-PDFs, while the backend is closer to Elicit/Consensus-class infrastructure.

---

# 8. Information Architecture

**Duplicates / overlaps**
- Chat attach vs Library (upload ownership unclear)  
- Dashboard recents vs Sidebar recents vs Library  
- Writing export vs Citations export  
- Settings AI Prompts vs invisible research prompt assembly  

**Confusing navigation**
- “Knowledge Library” vs “Projects” vs “Multi-Paper Analysis” — three homes for papers  
- Analysis intelligence lives under a single paper URL but isn’t named as such in nav  

**Hidden features**
- Bulk upload progress (only after composer attach)  
- `useRefreshAnalysis` API unused by pages  
- Domain/metadata overrides on paper page (power-user, easy to miss)  

**Missing dashboards**
- Pipeline / processing ops for the user  
- Evidence quality dashboard per project  
- “What changed in understanding” after re-analyze  

**Unused backend capabilities (frontend)**
- Full Phase 1.1–1.7 outputs  
- Phase 2 analyze/pipeline/phases endpoints  
- Structured medical extractors & graders  
- Knowledge graph  
- Admin prompt analytics (partial settings only)

---

# 9. Component Audit (inventory)

### Layout / shell
| Component | Purpose | Reusable | Redesign? | Debt |
|-----------|---------|----------|-----------|------|
| `AppShell` | 3-pane shell | Yes | Minor | — |
| `TopBar` | Titles / theme / panel | Yes | Yes — contextual actions | Static title map |
| `Sidebar` | Primary nav | Yes | **Yes** — IA collapse | Overloaded |
| `MobileDrawer` | Mobile nav | Yes | Minor | — |
| `PageContainer` | Page chrome | Yes | No | — |
| `ThemeToggle` | Dark/light | Yes | a11y labels | Icon-only |
| `RightPanel` | Chat context | Yes | Yes — evidence drawer | Chat-only |

### Common
| Component | Purpose | Reusable | Redesign? | Debt |
|-----------|---------|----------|-----------|------|
| `EmptyState` | Empty UX | Yes | No | — |
| `LoadingSpinner` | Loading | Yes | No | — |
| `ConfirmDialog` | Destructive confirm | Yes | No | — |
| `CookieConsent` | Cookies | Yes | No | — |
| `Toast` | Notifications | Yes | No | — |
| `MarkdownRenderer` | MD + KaTeX | Yes | No | — |

### Feature (selected)
| Component | Purpose | Reusable | Redesign? | Debt |
|-----------|---------|----------|-----------|------|
| `Composer` | Input + attach + model | Yes | Upload IA | Upload owns library |
| `MessageList` / bubbles | Chat transcript | Yes | Tool inspector | No tools UI |
| `BulkUploadProgress` | Batch poll | Yes | Elevate to Library | Hidden |
| `FileCard` | Paper card | Yes | Show pipeline badge | Meta-only |
| `AnalysisOutput` | Accordion markdown | Yes | Replace w/ structured views | Wrong abstraction for Phase 1 |
| `DomainSelector` / `MetadataInput` | Analyze params | Yes | Clarify vs classification | Confusable |
| `CitationFormDialog` | Citation CRUD | Yes | No | — |
| **`CitationTable`** | Table citations | — | — | **Dead** |
| **`FilePreviewDialog`** | Preview | — | — | **Dead** |
| **`ProjectList`** | Project nav | — | — | **Dead** (Sidebar inline) |

### shadcn UI kit
`button`, `card`, `dialog`, `tabs`, `accordion`, `skeleton`, `badge`, `input`, `select`, `table`, `progress`, etc. — reusable foundation; **table underused**, **no chart primitive**.

---

# 10. Competitive Review

| Product | Strength vs Soro | Weakness vs Soro |
|---------|------------------|------------------|
| **ChatGPT** | Simpler chat UX, memory, multimodal polish | Weak private research library / project corpus |
| **Claude** | Artifacts, long-context clarity | Not a citation/project research OS |
| **NotebookLM** | Source-grounded studio, audio overviews, clear “from your sources” | Less general chat/agent flexibility |
| **Perplexity** | Citation-first answers, discovery | Weaker private PDF pipeline depth |
| **Elicit** | Research workflows, extraction tables | Less conversational companion |
| **Consensus** | Evidence-oriented paper Q&A | Narrower workspace |
| **SciSpace** | PDF-native reading + explain | Less project/memory/writing suite |

**Where Soro is already stronger**
- Integrated **projects + notes + memory + writing + citations + multi-paper compare/gaps** in one shell  
- **Paper-scoped chat** with explicit grounding mode  
- Backend depth (Phase 1 stack) **exceeds** what most competitors expose — if/when UI catches up  

**Where Soro is weaker**
- No **PDF-native reader** with highlights  
- No **citation-first** answer layout (Perplexity)  
- No **extraction tables** / study cards (Elicit)  
- No **source studio** metaphor (NotebookLM)  
- Explainability near-zero despite having the data model  

---

# 11. UX Problems (ranked)

1. Phase 1 intelligence invisible after years of backend investment  
2. Upload discoverability (Library empty → “use chat”)  
3. Analysis UX = markdown essay, not inspectable research object  
4. No document viewer / page anchoring  
5. Sidebar IA overload (11 destinations)  
6. Processing opacity (`meta_status` only)  
7. Brand fragmentation (Soro / Personal AI)  
8. Memory create/explain gap  
9. Share = copy URL stub  
10. a11y: icon buttons, no skip link, limited live regions beyond chat  
11. Dead components confuse maintainers  
12. No global error boundary  
13. Session expiry UX not designed  
14. Compare/gaps far from single-paper flow  
15. Settings exposes prompt-admin complexity to all users  

---

# 12. Technical Frontend Debt

| Debt | Severity |
|------|----------|
| No clients/types for Phase 2 pipeline endpoints | **Critical** |
| `AnalysisOutput` markdown bridge fights structured data | **High** |
| Dead: `ProjectList`, `FilePreviewDialog`, `CitationTable` | Medium |
| `useRefreshAnalysis` unwired | Low |
| Dual upload transports (JWT documents vs session files) leak into UX | Medium |
| ApiError message-as-code mapped ad hoc on PaperOverview | Medium |
| Branding strings inconsistent | Medium |
| Vitest coverage uneven (some analysis tests; many pages untested) | Medium |
| No React error boundary | Medium |
| Default dark + purple accent = generic AI look (product risk, not bug) | Low |

---

# 13. Missing Phase 1 Features (UI checklist)

- [ ] Pipeline status timeline on paper + library  
- [ ] Document structure / sections browser  
- [ ] Classification chips (domain, study design, guideline)  
- [ ] Analysis-context summary (routing/prompt profile)  
- [ ] Medical entity & PICO panels (structured)  
- [ ] Evidence grading matrix (GRADE/RoB/etc.) with confidence  
- [ ] Knowledge graph visualization + filters  
- [ ] Phase detail drawers (`/phases/:phase`)  
- [ ] Trigger/re-run Phase 1 (`POST …/analyze`) with job UX  
- [ ] Chat citations linked to Phase 1 evidence IDs  

---

# 14. Missing Components (build list)

1. `PipelineStatusStepper`  
2. `PhaseResultPanel` (generic JSON→UI mapper per phase)  
3. `DocumentStructureNav`  
4. `ClassificationBadgeGroup`  
5. `EvidenceGradeTable`  
6. `ConfidenceMeter`  
7. `KnowledgeGraphCanvas` (start read-only)  
8. `PdfDocumentViewer` (or embed)  
9. `LibraryUploadZone`  
10. `ProcessingQueueDrawer`  
11. `ChatEvidenceDrawer`  
12. `ToolCallInspector` (when tools stream)  
13. `SessionExpiredModal`  
14. App-level `ErrorBoundary`  
15. `ProjectEvidenceSummary`  

---

# 15. Top 20 Improvements

| # | Improvement | Priority | Effort |
|---|-------------|----------|--------|
| 1 | Wire `/pipeline` + `/phases` + types; Paper **Understand** tab | Critical | L |
| 2 | Library **Upload** zone + move bulk progress to Library | Critical | M |
| 3 | Processing timeline (Phase 1 job states) | Critical | M |
| 4 | Evidence grading table UI | Critical | L |
| 5 | Classification + DU structure panels | Critical | L |
| 6 | Knowledge graph v1 (read-only) | High | L |
| 7 | PDF/document viewer with jump-to-section | High | L |
| 8 | Collapse sidebar IA (Chat · Library · Projects · Research · More) | High | M |
| 9 | Chat evidence drawer (RAG ↔ files) | High | M |
| 10 | Unify LLM overview as one tab, not the only analysis | High | M |
| 11 | Unify Soro branding end-to-end | High | S |
| 12 | Compare/gaps entry from Library multi-select + Projects | Medium | M |
| 13 | Memory explain + manual pin | Medium | M |
| 14 | Session expired friendly modal | Medium | S |
| 15 | Error boundary + empty/error catalog | Medium | S |
| 16 | Remove/repurpose dead components | Medium | S |
| 17 | a11y pass (labels, skip link, focus) | Medium | M |
| 18 | Tool-call inspector when tools enabled | Medium | M |
| 19 | Project-level synthesis dashboard | Low | L |
| 20 | Charts for confidence / grade distributions | Low | M |

Effort: **S** &lt; 2d · **M** ~1–2 wks · **L** multi-sprint  

---

# 16. Prioritized Roadmap

### Critical (next 1–2 sprints)
- Phase 1 paper workspace (tabs + API wiring)  
- Library upload + processing visibility  
- Evidence + classification visibility  

### High (following)
- Knowledge graph v1  
- Document viewer  
- IA sidebar redesign  
- Chat evidence drawer  

### Medium
- Memory explainability  
- Session/error UX  
- a11y + dead code cleanup  
- Compare/gaps entry points  

### Low
- Project synthesis dashboards  
- Advanced charting  
- Marketing landing in SPA  

---

# 17. Mock Screen Descriptions — Ideal Phase 1 Experience

> Descriptions only — not implementations.

### A. Library with Upload & Queue
Full-width drop zone at top of Knowledge Library. Cards show **pipeline badge** (`Queued → Understanding → Classified → Graded → Ready`). Right drawer: live batch/job list with phase names, not just “pending/done”.

### B. Paper Workspace (primary research surface)
Left: slim **PDF/structure** pane (pages + detected sections). Center tabs:  
**Overview** (biblio + LLM executive summary) · **Structure** (DU sections/quality) · **Classify** (type/domain/design/guideline + confidence) · **Entities** (PICO/medical) · **Evidence** (grade table, RoB, consistency) · **Graph** · **Chat**.  
Header actions: Re-run Phase 1, Export dossier, Save citation, Open in project.

### C. Evidence Matrix
Sortable table: outcome × grade × confidence × linked spans. Click row → highlight snippet in viewer + show grader rationale.

### D. Knowledge Graph
Force-directed or clustered graph: Population / Intervention / Comparator / Outcome / Study nodes. Filter by confidence; click node → side panel with provenance phase.

### E. Chat with Evidence Rail
While streaming, right rail shows **retrieved chunks**, **Phase 1 entities mentioned**, and **citation candidates**. User can pin an evidence card into Notes.

### F. Project Intelligence Home
Project dashboard: papers by evidence grade distribution, open contradictions (from compare), suggested gaps, shared graph across papers.

### G. Processing Clarity Toast/Banner
After upload: “Extracting structure… Classifying… Grading evidence…” with deep link to Paper Workspace when Ready.

---

# 18. Deliverable Checklist (this report)

| # | Section | Status |
|---|---------|--------|
| 1 | Executive Summary | ✓ |
| 2 | Current UX Score | ✓ 6.0 |
| 3 | Visual Design Score | ✓ 7.0 |
| 4 | IA Score | ✓ 5.5 |
| 5 | AI Explainability Score | ✓ 2.5 |
| 6 | Production Readiness Score | ✓ 5.5 |
| 7 | Complete Screen Inventory | ✓ |
| 8 | Missing Phase 1 Features | ✓ |
| 9 | Missing Components | ✓ |
| 10 | UX Problems | ✓ |
| 11 | Technical Frontend Debt | ✓ |
| 12 | Top 20 Improvements | ✓ |
| 13 | Mock screen descriptions | ✓ |

---

# 19. Sources (inspected)

- `frontend/src/routes/router.tsx`, `RootLayout.tsx`  
- `frontend/src/features/**` pages and APIs (chat, files, papers, analysis, search, citations, projects, writing, settings, dashboard)  
- `frontend/src/types/api.ts`, `features/files/api.ts`, `features/analysis/*`  
- `frontend/src/components/layout/*`, `components/ui/*`, `index.css`, `package.json`  

**Confirmed absent in SPA:** clients for `/api/documents/:id/analyze`, `/pipeline`, `/phases/:phase`; knowledge graph views; evidence-grading tables; classification panels; structured medical extractor UI.

---

# 20. D9 closure (2026-07-26) — a11y + M11/M12 hardening

Design-system ship step **D9** closed the following audit items in production SPA (routes/ViewModels unchanged):

| UI-State / M11–M12 item | Status |
|-------------------------|--------|
| App-level `ErrorBoundary` | Done — `components/common/ErrorBoundary.tsx` wraps App |
| Route `errorElement` | Done — `RouteErrorFallback` on root + legal routes |
| Session expired UX (no silent dump) | Done — `SessionExpiredModal` + `soro:session-expired` from apiClient 401 |
| Skip link | Done — AppShell → `#main-content` |
| Main landmark | Done — `<main id="main-content">` |
| Icon control labels | Done — ThemeToggle `aria-label`; loading `sr-only` |
| Shortcut scope (ignore while typing) | Done — `isTypingTarget` for ⌘B + paper `1`–`8` / `c`/`e`/`s` |
| ⌘K find + commands | Done — D8 |
| Library upload discoverability | Done earlier (D5) |
| Phase 1 paper tabs / pipeline / graph | Done in M4–M10 track (supersedes “absent” note above for those surfaces) |

**Still open (out of D9 scope):** resizable rails persistence; full UI-State Phase 1 “latent” items already shipped elsewhere; branding string sweep on login templates.

---

*UI-State.md — originally audit-only; §20 records D9 closure.*
