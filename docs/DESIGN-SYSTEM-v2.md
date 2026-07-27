# Soro Product Design System v2

**Status:** Draft — awaiting approval before implementation  
**Date:** 2026-07-26  
**Type:** Product UX + visual system (not code)  
**Supersedes in spirit:** Ad-hoc purple chatbot chrome still shipping in the SPA  
**Aligns with:** [`DESIGN-SYSTEM.md`](../DESIGN-SYSTEM.md) v1 tokens · [`UI-Architecture.md`](../UI-Architecture.md) routes/ViewModels · [`docs/soro-vs-jenni-roadmap.md`](soro-vs-jenni-roadmap.md) · [`docs/Interaction-Guidelines.md`](Interaction-Guidelines.md)

**Guiding principle:** Soro is the **operating system for scientific research.**

**Hard constraints**

- Do **not** change backend architecture, routes, ViewModels, or mappers.  
- Do **not** implement UI in this pass — approve this doc first, then ship page-by-page.  
- Goal is **not prettier**. Goal is: **operating system for scientific research**.

---

## 0. Feeling targets (borrow, don’t clone)

| Borrow from | What we take | What we leave |
|-------------|--------------|---------------|
| **Linear** | Minimal nav, tight spacing, quiet type | Issue-tracker metaphors |
| **Notion** | Content-first pages, calm side panels | Endless block playground |
| **Perplexity** | Answer + sources as first-class UI | Web-search as the whole product |
| **NotebookLM** | Workspace organisation (sources → studio) | Playful / consumer visual language |
| **Raycast** | Dense elegant rows, command-feel density | Overlay-only interaction |
| **Vercel Dashboard** | Professional dashboard restraint | Deploy/ops chrome |
| **GitHub** | Hierarchy for technical data (lists, meta, diffs) | Repo/code primacy |
| **Figma** | Sidebar + inspector pattern | Infinite canvas as home |

**Soro =** VS Code (tool surfaces) × Notion (content calm) × Figma (inspect) × Linear (restraint).

**Soro ≠** ChatGPT · Claude chat shell · colourful SaaS landing · “AI dashboard.”

---

## 1. UX audit (current product)

### 1.1 What’s working (keep)

| Strength | Why it matters for researchers |
|----------|--------------------------------|
| Paper Workspace tabs (Structure → … → Graph) | Matches how scientists *dissect* a paper |
| Phase pipeline + AI state language | Honest progress; learn once, reuse everywhere |
| ViewModel + mapper boundary | UI can densify without inventing science |
| Explainable Chat + `WorkspaceReference` | Inquiry points back into evidence |
| Library → Paper → Chat loop | Correct primary object: the paper |

### 1.2 Critical hierarchy bugs

Observed Paper Overview stack (pre/post partial fixes):

```
Header → Pipeline (dominant) → Buttons → Notes card → Chat card → Tabs
```

**Target:**

```
Header → Tabs → Current content → Pipeline (collapsed) → Secondary widgets
```

| Problem | Researcher cost | Severity |
|---------|-----------------|----------|
| Pipeline dominates after Ready | Progress feedback treated as content; tabs feel secondary | ★★★★★ |
| Tabs below chrome/cards | Workspace is the product but reads as footer | ★★★★★ |
| Duplicate Chat CTAs | Decision fatigue; looks unfinished | ★★★★ |
| Empty Notes / chat feature cards | Vertical waste; “dashboard tiles” not workstation | ★★★★ |
| Many equal-weight cards | No scan path; everything shouts | ★★★★ |
| Excess vertical spacing | Researchers scroll past empty air | ★★★ |
| Accent purple on too much chrome | Feels chatbot / consumer AI | ★★★ |
| Dev panel in main flow (dev builds) | Breaks professional workstation illusion | ★★ |

### 1.3 Product identity mismatch

| Current vibe | Needed vibe |
|--------------|-------------|
| AI chatbot with paper attachments | Scientific workstation |
| Dashboard of cards | Document-centered workspace |
| Pipeline as hero | Evidence as hero |
| Marketing density (sparse) | Reading density (compact) |

**Why:** Researchers open Soro to *inspect and work*. If chrome wins, they bounce to PDF + ChatGPT.

---

## 2. Design philosophy (v2)

1. **Evidence-first** — Content always dominates chrome.  
2. **Dense** — Researchers read; don’t gift-wrap emptiness.  
3. **Minimal** — No unnecessary borders, shadows, or stacked cards.  
4. **Calm** — One accent; neutrals carry the shell.  
5. **Professional** — No playful gradients, glass, or celebration motion.  
6. **Workspace-oriented** — Paper (and Project) are centres; Chat is a mode.  
7. **Fast** — Fewer clicks to Structure / Evidence / Chat.  
8. **Scientific** — Hierarchy like GitHub/Linear: meta → body → inspect.

---

## 3. Information hierarchy

### 3.1 Application zones

```
┌──────────┬─────────────────────────────────────────────┐
│ Shell    │ Context header (paper / project / chat)     │
│ Sidebar  ├─────────────────────────────────────────────┤
│          │ Primary navigation of THIS object (tabs)    │
│          ├─────────────────────────────────────────────┤
│          │ Main stage (tab content — evidence-first)   │
│          ├─────────────────────────────────────────────┤
│          │ Status / pipeline (collapsed when Ready)    │
│          ├─────────────────────────────────────────────┤
│          │ Secondary (notes, actions, inspector)       │
└──────────┴─────────────────────────────────────────────┘
```

**Rule:** Tabs sit immediately under the object header. Never below feature cards.

### 3.2 Object hierarchy (mental model)

| Level | Object | UI centre |
|-------|--------|-----------|
| L0 | App shell | Sidebar |
| L1 | Library / Project / Chat list | Collection |
| L2 | **Paper** / Project studio / Thread | **Workspace** |
| L3 | Tab (Structure, Evidence, …) | Main stage |
| L4 | Selected entity / grade / node | Inspector (optional rail) |

NotebookLM organisation without NotebookLM look: **sources live in Library; understanding lives in Paper Workspace.**

### 3.3 Paper Workspace hierarchy (canonical)

```
[ ← Library ]  Title · Authors · Journal meta · status chip
──────────────────────────────────────────────────────────
Overview | Structure | Classification | Entities | Evidence | Graph | Narrative | Chat
──────────────────────────────────────────────────────────
▌ MAIN STAGE (active tab — dense, content-led)
──────────────────────────────────────────────────────────
✓ Chat Ready · Processed 2m ago · View pipeline details   ← collapsed
──────────────────────────────────────────────────────────
Notes (compact) · Cite · Export                           ← secondary
```

### 3.4 Overview tab content model (not a card dump)

Prefer **one summary surface** + **stat strip** + **section jumps**:

| Block | Content | Interaction |
|-------|---------|-------------|
| Summary | Abstract / narrative blurb (short) | Expand |
| Quick stats | Study type · Domain · Grade · Entity count · Graph size | Click → tab |
| Jump row | Structure · Evidence · Graph · Chat | Tab select |
| Recent inquiry | Last paper-chat snippet (if any) | Open chat |
| Notes | Compact empty or count | Notes route |

**Avoid:** Separate large Chat card + Notes card + action card all competing.

---

## 4. Navigation redesign

### 4.1 Philosophy

- **Linear:** Five primary destinations max — sidebar must not grow forever.  
- **Researching ≠ chatting:** Users are in a workstation; Chat is a *mode*, not the product centre.  
- **Figma:** Object-local tools (paper tabs, library toolbar) outrank global nav peers.  
- **Raycast / VS Code:** Universal find via **⌘K / Ctrl+K**, not another sidebar item.

### 4.2 Sidebar (desktop) — simplified

```
Soro
[+ New]                 ← Upload · New project · New chat (menu)

Home
Library                 ← corpus (near-term centre)
Projects                ← long-term centre (see §4.6)
Writing                 ← evidence-backed drafts (M15+)
Chat                    ← inquiry mode (demote over time; see §4.5)

────────
Recent papers (3–5)
Recent projects (3)

Settings · Account
```

**Removed from sidebar** (become **toolbar / command palette** actions):

| Former nav item | New home |
|-----------------|----------|
| Search | **⌘K** command palette (+ Library toolbar) |
| Compare & gaps | Library toolbar · Project Insights · ⌘K |
| Citations | Library / Writing toolbar · ⌘K |
| Notes | Paper secondary · Project · ⌘K |
| Memory | Settings / Account · ⌘K |

| Why |
|-----|
| Sidebars that list every feature become product tours, not workstations |
| Researchers already expect Search / Compare *in context of the corpus* |
| Writing earns a primary slot because it is a durable artifact surface (vs Jenni) |

**Routes stay** (`/search`, `/research/compare`, etc.) — deep-linkable; just not primary nav.

### 4.3 In-paper navigation

- **Tabs are the product.** Sticky under header on scroll (desktop).  
- Chat tab → existing `/papers/:id/chat` (route unchanged).  
- URL `?tab=` unchanged.

### 4.4 Mobile

- Bottom: Home · Library · Projects · More  
- More: Writing, Chat, Settings  
- Paper: sticky tab strip (horizontal scroll)  
- Rails → sheets  
- ⌘K → mobile search sheet  

### 4.5 Chat: primary now → secondary later

| Horizon | Chat placement | Why |
|---------|----------------|-----|
| **Near-term** | Sidebar item + Paper tab + Project chats | Discovery; existing habit |
| **Mid-term** | Demote global Chat under More / ⌘K; keep Paper + Project chat | Users research; they don’t “open ChatGPT” |
| **Long-term** | Chat lives **inside** Paper and Project only; global thread list is secondary | Aligns with “OS for research,” not “AI chatbot” |

Do **not** delete global chat routes — demote chrome only.

### 4.6 Centre of gravity: Library now → Projects later

| Horizon | Centre | Analogy |
|---------|--------|---------|
| **Now** | **Library** (papers) | Files |
| **Later** | **Projects** (workstreams containing papers) | Figma: Project → Files |

### 4.6.1 Home = Continue working (not a dashboard)

VS Code-style start page — **no analytics, no welcome hero, no giant cards.**

Show: Continue working · Recent projects · Recent papers · Today’s notes · Recent chats.  
Dense rows only.

### 4.6.2 Writing = grounded environment (not Google Docs)

```
Projects → Drafts → Paper references → Claim blocks → Evidence links
```

Compete on defensibility, not WYSIWYG. Claim blocks are first-class.

### 4.7 Progressive disclosure (View levels)

Same routes / ViewModels / mappers — chrome density only.

| View | Emphasize |
|------|-----------|
| **Simple** | Overview, Summary, Chat |
| **Standard** (default) | Structure, Entities, Evidence |
| **Research** | Full tabs + rails |
| **Expert** | Graph, Inspector, ⌘K hints, advanced filters |

### 4.8 Workspace Modes (layout emphasis, not routes)

| Mode | Emphasis |
|------|----------|
| **Reading** | Paper, Summary, Structure — minimal chrome |
| **Analysis** | Entities, Evidence, Classification, Graph + Inspector |
| **Writing** | Draft, Claims, Evidence, References, Chat |

Optional `?mode=`; does not change backend.

### 4.9 Command palette (differentiator)

**⌘K / Ctrl+K** — universal entry for papers, entities, evidence, commands, navigation, View/Mode.

See [`Interaction-Guidelines.md`](Interaction-Guidelines.md).

**Docs freeze:** After this amendment, stop expanding design docs. Next artifact is **D0.5 static prototype**.

---

## 5. Layout system

### 5.1 Shell widths

| Region | Width | Notes |
|--------|-------|-------|
| Sidebar | 240px (collapsed icon 52px) | Notion/Linear calm |
| Main | `max-w-3xl` reading · `max-w-5xl` workspace data · `max-w-6xl` compare | Don’t force chat width on Evidence tables |
| Inspector rail | 280–320px | Figma-like; optional |

### 5.2 Page templates

**T1 — Collection** (Library; Citations/Notes when opened from toolbar)  
Header + **contextual toolbar** (Search, Compare, Citations, Filters) + dense list. GitHub-like rows.

**T2 — Workspace** (Paper, Project)  
Header + tabs + stage + collapsed status. *Primary template.*

**T3 — Inquiry** (Paper Chat, Project Chat, demoted global Chat)  
Message column + evidence rail (Perplexity source pattern, private `WorkspaceReference`s).

**T4 — Tool** (Compare, Writing; Search only if opened as full page)  
Toolbar + split/stacked work area; no dashboard widgets.

### 5.3 Paper layout wireframe (desktop)

```
┌────────┬──────────────────────────────────────────────┐
│ Nav    │ Title                                         │
│        │ Authors · Journal · Year · DOI · [Ready]      │
│        │ ───────────────────────────────────────────── │
│        │ [Overview][Structure]…[Chat]     ← sticky     │
│        │ ───────────────────────────────────────────── │
│        │                                               │
│        │            MAIN STAGE                          │
│        │                                               │
│        │ ───────────────────────────────────────────── │
│        │ ✓ Ready · 2m ago · details                    │
└────────┴──────────────────────────────────────────────┘
```

While **processing only**, insert a **full Pipeline stepper** between header and tabs (progress feedback). Never after Ready as hero.

**Library toolbar wireframe**

```
Library                          [Upload] [Compare] [Citations] [Filter]   ⌘K
────────────────────────────────────────────────────────────────────────────
row · row · row …
```

## 6. Spacing system

Inspired by Linear / Vercel: **tight, consistent, not sparse.**

| Token | Value | Use |
|-------|-------|-----|
| `space.1` | 4px | Icon gaps, chip padding |
| `space.2` | 8px | Inline clusters |
| `space.3` | 12px | Row padding, compact cards |
| `space.4` | 16px | Section padding |
| `space.5` | 20px | Header block gaps |
| `space.6` | 24px | Between major sections |
| `space.8` | 32px | Page top/bottom only |

**Rules**

- Default section gap: `space.6` (not 48–64px).  
- List rows: `space.3` vertical padding.  
- Ban “hero empty” stacks of cards with `py-8` between each.  
- Overview: prefer one bordered region over three floating cards.

**Why:** Dense pages let researchers compare Structure vs Evidence without losing context to scrolling.

---

## 7. Typography system

Linear / Vercel: **small, compact, readable, professional.**

| Role | Spec | Use |
|------|------|-----|
| `type.display` | 20–22px / semibold / tight | Paper title only |
| `type.title` | 16px / semibold | Section titles (rare) |
| `type.body` | 14px / regular / 1.5 | Prose, abstracts |
| `type.ui` | 13px / medium | Tabs, buttons, rows |
| `type.meta` | 12px / regular | Authors, timestamps, captions |
| `type.micro` | 11px / medium / tracking-wide | Section labels (uppercase sparingly) |
| `type.mono` | 12px tabular | DOIs, scores, IDs |

**Rules**

- Prefer `type.ui` over large marketing headings inside workspaces.  
- One display size per page (the paper/project title).  
- Tab labels: `type.ui`, not oversized.  

**Why:** Scientific UIs encode authority in restraint, not size.

---

## 8. Color & accent usage (v2)

Keep DESIGN-SYSTEM ink neutrals + semantic science palette.

**Accent policy (critical):** reduce accent usage ~**60%** vs current SPA.

| Accent allowed | Accent forbidden |
|----------------|------------------|
| Active tab underline/text | Large soft purple panels |
| Primary button fill | Sidebar selected wash on every item |
| Focus rings | Decorative gradients / glow |
| Selected graph node | Card borders in accent |
| Text links in body | Empty-state illustrations in brand wash |

**Current purple:** Acceptable as interim `signal` **if** usage-capped as above. Long-term: migrate to DESIGN-SYSTEM teal (`signal.600` `#0F6E6A`) for distinctiveness vs consumer AI violet.

**Surfaces:** `surface.app` / `panel` / `sunken` — borders `ink.200`, not accent.

---

## 9. Card & surface system

### 9.1 Principle

Cards are **rare** (DESIGN-SYSTEM §0.6). Prefer:

1. **Information surface** — single bordered region / definition list  
2. **Expandable sections** — Structure-like disclosure  
3. **Inline panels** — inspector, rails  
4. **Dense rows** — Library, citations  

### 9.2 Component inventory (v2)

| Component | Role | Card? |
|-----------|------|-------|
| `AppSidebar` | Shell nav | No |
| `ObjectHeader` | Title + meta + status | No |
| `WorkspaceTabs` | Sticky tab list | No |
| `PipelineStatus` | Expanded (processing) / Collapsed (ready) | Soft surface |
| `StatStrip` | Quick stats → tab jumps | No (strip) |
| `SummaryBlock` | Abstract / overview prose | Optional light border |
| `DataTable` | Evidence / entities | No |
| `InspectorRail` | Selected node/entity | Panel |
| `SourceChip` / `WorkspaceReferenceChip` | Navigable refs | Chip |
| `MessageList` | Chat | Bubbles only where needed |
| `CommandRow` | Raycast-like dense action row | No |
| `EmptyInline` | One-line empty + action | Dashed, compact |
| `CommandPalette` | ⌘K universal find + actions | Modal overlay |
| `CollectionToolbar` | Search / Compare / Citations / Filters on Library | No |
| `DevDock` | Dev-only inspector | Hidden in production |

**Deprecated patterns**

- Marketing “feature cards” duplicating a primary button  
- Triple stacked empty states  
- Full-width purple soft panels for non-actions  

---

## 10. Component redesign notes (by pattern)

### PipelineStatus

| State | UI |
|-------|-----|
| Processing / error | Full stepper between header and tabs |
| Ready | Collapsed: `✓ {label} · Processed {relative} · View details` |
| Details open | Stepper inside disclosure — never permanent hero |

**Why:** Progress is feedback; evidence is content.

### WorkspaceTabs

- Sticky; clear active (accent text + 2px underline).  
- Inactive: `ink.500`.  
- No pill backgrounds on every tab.

### Chat (global + paper)

- Perplexity pattern: **answer** then **sources/refs** — but refs are `WorkspaceReference` into tabs, not web cards.  
- Paper Chat: evidence rail = inspect workspace, not second chatbot.

### Library

- GitHub-like rows: title, meta, AI state badge, actions on hover/focus.  
- Upload is a toolbar action, not a hero marketing block.  
- **CollectionToolbar:** Compare, Citations, Filters — not sidebar peers.  
- Search opens ⌘K scoped to Library by default.

### Compare / Citations / Notes / Writing

- Opened from toolbar, project, or ⌘K (routes unchanged).  
- Tool template (T4): dense, tabular, export-first.  
- Writing (M15+) inherits claim blocks — not a pastel editor.

### CommandPalette

- Always available; respects current workspace scope (paper / project / library).  
- See Interaction Guidelines for focus trap, ranking, and keyboard.

---

## 11. Desktop responsive strategy

| Breakpoint | Behaviour |
|------------|-----------|
| ≥1280 | Sidebar + optional inspector |
| 1024–1279 | Sidebar collapsible; no inspector (use sheets) |
| &lt;1024 | Bottom nav; paper tabs scroll; rails → sheets |

**Why:** Workstation density on desktop; don’t fake a phone dashboard.

---

## 12. Motion

Keep DESIGN-SYSTEM: motion explains state only.

| Allowed | Forbidden |
|---------|-----------|
| Pipeline pulse while running | Gradient shimmer on Ready |
| Tab content fade 120–160ms | Bounce / confetti |
| Stream cursor | Parallax / glass |

---

## 13. Deliverable map

| # | Deliverable | Location |
|---|-------------|----------|
| 1 | UX audit | §1 |
| 2 | Information hierarchy | §3 |
| 3 | Navigation redesign | §4 |
| 4 | Component redesign | §9–10 |
| 5 | Spacing system | §6 |
| 6 | Typography system | §7 |
| 7 | Card system | §9 |
| 8 | Layout system | §5 |
| 9 | Desktop responsive | §11 |
| 10 | Implementation roadmap | §14 |
| 11 | Interaction system | [`Interaction-Guidelines.md`](Interaction-Guidelines.md) |
| 12 | Command palette | §4.7 + Interaction Guidelines |

---

## 14. Implementation roadmap (after approval)

**Do not big-bang rewrite.** Prototype feel first, then tokens, then pages.

```
D0 Approve design
    ↓
D0.5 Static prototype (Header · Sidebar · Workspace · Paper · Library)
    ↓  “Yes — this feels like Soro.”
D1 → D8 Implementation
```

| Step | Scope | Exit |
|------|-------|------|
| **D0** | Approve Design System v2 + Interaction Guidelines | Signed decisions (§15) |
| **D0.5** | **Static prototype** — no backend, no React business logic; HTML/CSS or Storybook mockups of shell + Paper + Library | Stakeholders: “This feels like Soro” |
| **D1** | Tokens: spacing, type, accent usage audit | Accent only on allowed targets |
| **D2** | Shell: slim sidebar + `ObjectHeader` + sticky tabs + ⌘K shell | Matches §4.2 / §5.3 |
| **D3** | `PipelineStatus` everywhere | Ready collapsed; processing expanded above tabs |
| **D4** | Paper Overview → Summary + StatStrip | Hierarchy fix |
| **D5** | Library densification + CollectionToolbar | T1 |
| **D6** | Paper/Project Chat chrome; demote global Chat affordance | T3 |
| **D7** | Writing, Compare, Citations (toolbar-opened) | T4 ☑ |
| **D8** | Command palette v1 (find + navigate + core commands) | Keyboard-first ☑ |
| **D9** | a11y + UI-State audit | M11–M12 ☑ |

**Non-goals during D1–D9**

- No route deletions (demote chrome only)  
- No mapper/ViewModel changes  
- No Jenni editor clone  
- No production deploy gated on full D9 (prototype D0.5 is the feel gate)

---

## 15. Decision checklist (approve / amend)

| Decision | Proposal | Your call |
|----------|----------|-----------|
| Hierarchy | Tabs under header; pipeline collapsed when Ready | ☐ |
| Accent | Cap 60%; purple interim **or** teal `signal` | ☐ Purple / ☐ Teal |
| Overview | Summary + StatStrip; no duplicate Chat card | ☐ |
| Cards | Rare; surfaces/sections/rows | ☐ |
| Density | Linear spacing (§6) | ☐ |
| Sidebar | Home · Library · Projects · Writing · Chat only | ☐ |
| Chat | Demote global under More / ⌘K; Paper/Project-first (D6) | ☑ |
| Search | ⌘K primary; `/search` route secondary | ☑ |
| View / Mode | Progressive disclosure + Reading/Analysis/Writing modes | ☐ |
| Docs freeze | No more design docs; D0.5 prototype next | ☐ |
| Prototype | **D0.5 frozen** — Home approved; Paper Workspace is next in production | ☑ |
| Ship order | D0 → D0.5 → D1–D9 in app · design track complete | ☑ |

---

## 16. Success criteria (UX)

A researcher opening a **Chat Ready** paper should:

1. See **tabs within one glance** of the title.  
2. Reach Evidence or Structure in **one click**.  
3. Not see a full pipeline stepper unless they open details.  
4. Feel they are in a **workstation**, not a chatbot.  
5. Scan Overview stats without scrolling past empty cards.  
6. Reach Search / Compare / Cite without hunting a growing sidebar — via toolbar or **⌘K**.

---

*End of Product Design System v2 — design only; no implementation until D0 + D0.5 approval.*
