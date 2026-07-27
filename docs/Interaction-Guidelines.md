# Soro Interaction Guidelines

**Status:** Draft — approve with Design System v2  
**Date:** 2026-07-26  
**Type:** Interaction / behaviour system (visual design is only half of UX)  
**Companion:** [`DESIGN-SYSTEM-v2.md`](DESIGN-SYSTEM-v2.md) · [`DESIGN-SYSTEM.md`](../DESIGN-SYSTEM.md) · [`UI-State.md`](../UI-State.md)

**Principle:** Soro is an **operating system for scientific research**. Interactions should feel like VS Code + Linear + Figma — precise, keyboard-friendly, undoable where possible — never like a playful chatbot.

**Constraints:** Do not invent backend contracts. Loading/streaming/error copy stays aligned with UI-State + M3 AI status language.

---

## 1. Input model

| Channel | Priority | Notes |
|---------|----------|-------|
| Keyboard | First-class | Researchers live on keyboards |
| Pointer | First-class | Hover reveals density; click commits |
| Touch | Supported | Sheets instead of rails; larger hit targets |

**Rule:** Every primary action reachable by keyboard. Every focusable control has a visible focus ring (`signal` / accent — usage-capped per DS v2).

---

## 2. Focus

| Rule | Detail |
|------|--------|
| Visible focus | 2px ring; never remove `outline` without replacement |
| Tab order | Logical: sidebar → header → tabs → main → inspector |
| Modal / palette | Focus trap; restore focus to trigger on close |
| Skip link | “Skip to main content” on app shell |
| Roving tabindex | Tabs, graph node list, command results |

**Why:** Dense UIs without focus are unusable for power users and a11y.

---

## 3. Hover

| Surface | Hover behaviour |
|---------|-----------------|
| Library / citation rows | Reveal secondary actions (cite, open, compare checkbox) |
| Graph nodes | Highlight node + connected edges; tooltip with label |
| Reference chips | Underline / slight lift; show target tab in `title` |
| Buttons | Background shift only — no scale bounce |
| Sidebar items | Neutral wash (`ink.100`), not accent fill |

**Rule:** Hover never changes layout height (no jump).

---

## 4. Selection

| Context | Selection model |
|---------|-----------------|
| Library | Multi-select for Compare (checkbox + Shift range) |
| Entities / Evidence rows | Single select → optional inspector |
| Graph | Single node or edge; Esc clears |
| Chat messages | Text/block select for copy; no multi-message bulk unless needed |
| Command palette | Single highlighted result; Enter runs |

**Selected chrome:** `signal.100` / border — not heavy purple panels.

---

## 5. Keyboard shortcuts (global)

| Shortcut | Action |
|----------|--------|
| `⌘K` / `Ctrl+K` | Command palette |
| `⌘B` / `Ctrl+B` | Toggle sidebar |
| `Esc` | Close palette / clear selection / collapse inspector |
| `g then l` | Go Library *(optional chord — v2)* |
| `g then p` | Go Projects |
| `g then w` | Go Writing |
| `/` | Focus in-page filter when on Collection (Library) |

**Paper workspace**

| Shortcut | Action |
|----------|--------|
| `1`…`8` | Jump tabs (Overview…Chat) when not typing in input |
| `c` | Open paper chat |
| `e` | Evidence tab |
| `s` | Structure tab |

Disable letter shortcuts while focus is in `input`, `textarea`, `contenteditable`.

---

## 6. Command palette

**Open:** `⌘K` / `Ctrl+K` · click search affordance in shell.  
**Close:** `Esc` · click overlay · successful navigate.

### Behaviour

1. Opens with focus in query field.  
2. Default scope = current context (Library / Paper / Project).  
3. Results grouped: **Commands** · **Papers** · **Entities** · **Chats** · **Projects**.  
4. Arrow keys move; Enter executes; `⌘Enter` may open in background where relevant.  
5. Empty query shows frequent commands + recents.  
6. Ranking: exact prefix > fuzzy > recency within scope.

### Commands (v1 set)

Upload paper · Search papers · Open Evidence/Graph/Structure · Compare papers · Start chat · New project · Export citation · Open notes · Jump to entity/section · Find author · Switch project · Settings.

### Non-goals (v1)

- Natural-language agent inside the palette  
- Web-wide academic search (private library first)

**Why:** Differentiator vs NotebookLM / Jenni / Perplexity — a true research workstation shortcut layer.

---

## 7. Loading

| Pattern | When | UI |
|---------|------|-----|
| Skeleton | First paint of known layout | Match final structure; no spinner-only pages |
| Inline busy | Button / row action | Disable control + `aria-busy` |
| Pipeline | Phase work | `PipelineStatus` expanded; AI state badge |
| Soft refresh | Background poll | No full-page flash |

**Forbidden:** Blocking the whole app for a single paper phase.  
**Copy:** Use existing AI state labels (Queued, Understanding, …) — never “magic.”

---

## 8. Streaming (chat)

| Rule | Detail |
|------|--------|
| Historical messages | Do not re-render/remount while stream updates (memoize) |
| Live turn | Separate live region; `aria-live="polite"` |
| Stop | Always available while streaming |
| Failure | Inline error on live turn; keep prior messages |
| Sources / refs | Appear after stream completes (or progressive if backend sends) |
| Reasoning | Separate from answer; collapsed by default |

Align with M10 Explainable Chat: no invented refs during stream.

---

## 9. Optimistic UI

| Allowed | Guard |
|---------|-------|
| Reading status toggle | Rollback + toast on failure |
| Note title edits | Debounced save; show “Saving…” meta |
| Project rename | Optimistic list update |
| Chat user bubble | Show immediately; reconcile ids from server |

**Not optimistic:** Evidence grades, pipeline phase results, citation metadata from DOI — wait for truth.

---

## 10. Undo & destructive actions

| Action | Pattern |
|--------|---------|
| Delete note / citation | Confirm or toast with Undo (5–10s) |
| Delete conversation | Confirm dialog |
| Remove paper from project | Undo toast |
| Clear graph selection | Esc (instant) |

**Why:** Researchers fear silent data loss more than extra clicks.

---

## 11. Context menus

Right-click / long-press on:

- Paper row → Open, Chat, Cite, Compare, Move to project  
- Entity / evidence row → Open tab, Copy name, Insert claim *(M14+)*  
- Graph node → Focus, Open entity, Hide type  

Menus: compact, `type.ui`, keyboard-navigable. No decorative icons soup.

---

## 12. Split panes & resizable panels

| Panel | Default | Resize |
|-------|---------|--------|
| Sidebar | 240px | 200–320px; persist |
| Paper Chat evidence rail | 264px | 220–360px; collapse to icon |
| Graph inspector | 300px | 260–400px |
| Compare split | 50/50 | Drag gutter |

**Rules:** Minimum widths enforced; double-click gutter resets; no overlapping modals with panes.

---

## 13. Inspector behaviour (Figma-like)

1. Selecting an object opens inspector (right).  
2. Inspector shows **only** ViewModel fields — no raw JSON in prod.  
3. Deep links (`?ref=`) select + scroll + focus target.  
4. Closing inspector does not leave stale highlight without selection state.  
5. Mobile: inspector = bottom sheet (40–70% height).

---

## 14. Graph interactions

| Input | Result |
|-------|--------|
| Click node | Select + inspector + fit soft pan |
| Click edge | Select edge detail |
| Drag background | Pan |
| Wheel / pinch | Zoom toward cursor |
| Fit control | Frame all filtered nodes |
| Esc | Clear selection |
| Filter / search | Dim non-matches; don’t destroy layout unless needed |

**Stable IDs:** Navigation uses mapper keys / `sourceEntityId`, not transient UUIDs alone (M9/M10).

**Forbidden:** Edit/delete graph in v1 UI (read-only instrument).

---

## 15. Chat interactions

| Action | Behaviour |
|--------|-----------|
| Send | Enter; newline Shift+Enter |
| Stop | Halts stream; partial answer kept |
| Copy | Per-message; copies answer text (not chrome) |
| Regenerate | Last assistant only |
| Reference chip click | Navigate workspace tab + `ref` |
| Starter prompts | Fill composer or send — one pattern, consistent |
| Paper scope | Web search off; disclose “grounded in this paper” |

**Global vs paper chat:** Same message chrome; different rails and empty states.

---

## 16. Collection interactions (Library)

| Action | Behaviour |
|--------|-----------|
| Upload | Toolbar; progress via AI state on rows |
| Multi-select | Enables Compare |
| Row primary click | Open Paper Overview |
| Filters | Persist in URL query when cheap |
| Empty library | Inline empty + Upload — not a marketing page |

---

## 17. Motion (interaction)

| Duration | Use |
|----------|-----|
| 80–120ms | Hover / focus assists |
| 120–160ms | Tab panel swap |
| 160–220ms | Palette / sheet open |
| Pulse only | Active pipeline / streaming cursor |

No springy overshoot. Prefer opacity + 4px translate.

---

## 18. Error & empty

| State | Pattern |
|-------|---------|
| Empty | `EmptyInline` — one line + one action |
| Error | Banner or row alert; retry when safe |
| Session expired | Modal (M11) — not silent bounce |
| Pipeline error | Badge + expanded pipeline details |

Copy: concrete, short, non-blaming (“Evidence not available yet”).

---

## 19. Implementation hooks (when coding)

| Guideline | Likely surface |
|-----------|----------------|
| ⌘K | Shell-level provider |
| Focus trap | Palette, modal, sheet |
| Memoized history | MessageList (M10) |
| `?ref=` focus | `useWorkspaceFocus` |
| Shortcut scopes | Ignore when typing |

No backend changes required for interaction chrome.

---

## 20. Approval checklist

| Item | Approve |
|------|---------|
| Keyboard-first + visible focus | ☑ |
| ⌘K as primary search/command | ☑ |
| Optimistic only for safe prefs/edits | ☑ |
| Resizable rails with persisted widths | ☐ |
| Graph read-only + stable-id focus | ☑ |
| Streaming without remounting history | ☑ |

---

*End of Interaction Guidelines — pair with Design System v2; prototype in D0.5 before building.*
