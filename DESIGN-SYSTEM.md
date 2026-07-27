# Soro Design System

**Product specification:** [Soro Product Spec **v1.0**](PRODUCT-SPEC.md) — Part 3 of 3  
**Document type:** Design system specification (visual + interaction language)  
**Product:** Soro  
**Spec version:** 1.0  
**Date:** 2026-07-26  
**Status:** **Locked in Product Spec v1.0** — feature-complete for first implementation phase (design only; no code in this document)  
**Companions:** [`UI-Architecture.md`](UI-Architecture.md) · [`UI-State.md`](UI-State.md)

**Intent:** Give Soro a visual identity that reads as a **research instrument**, not a generic AI chat product. Current product chrome (violet accent, dark-default assistant UI) is treated as **legacy** to migrate away from—not as the target system.

**UX / workstation redesign (pending approval):** [`docs/DESIGN-SYSTEM-v2.md`](docs/DESIGN-SYSTEM-v2.md) · [`docs/Interaction-Guidelines.md`](docs/Interaction-Guidelines.md). **Do not implement v2 UI until D0 + D0.5 (static prototype) are approved.**

---

# 0. Design Principles

1. **Instrument, not entertainment** — Density is allowed; spectacle is not. No glow, no gradient washes, no celebratory confetti for “AI done.”  
2. **Evidence has a color; chrome does not** — Neutrals carry the shell. Color is reserved for status, confidence, grades, and focus.  
3. **One accent, many semantics** — A single brand accent for interaction; a separate semantic palette for science (grade, risk, pipeline).  
4. **Typography carries authority** — Display for brand and titles; a calm reading face for paper content; mono for IDs, DOIs, scores.  
5. **Light is first-class** — Research happens in daylight and offices. Dark is a preference, not the brand default.  
6. **Cards are rare** — Prefer surfaces, rules, and spacing. Cards only when the object is selectable or actionable.  
7. **Motion explains state** — Pipeline progress, stream cursor, panel open/close. Never decoration for its own sake.  
8. **Brand test** — Remove the wordmark: the page should still feel like Soro (ink, structure, precision)—not ChatGPT-violet.  
9. **AI states are a product language** — Uploading → Queued → Understanding → Classifying → Evidence Ready → Graph Ready → Chat Ready must look and read the **same** in Library, Paper Workspace, Projects, and Dashboard. Users learn the system once.

---

# 1. Brand Character

| Attribute | Expression |
|-----------|------------|
| **Name** | Soro — always, in product chrome |
| **Personality** | Precise, calm, scholarly-modern, private |
| **Voice in UI** | Short, concrete (“Evidence ready,” not “Your AI magic is complete!”) |
| **Metaphor** | Lab bench + reading desk: tools within reach, paper at center |
| **Not** | Neon AI, purple gradients, startup candy, newspaper density |

---

# 2. Color System

## 2.1 Core neutrals (Ink)

Cool, slightly blue-gray ink—not warm cream, not pure Instagram black.

| Token | Light | Dark | Role |
|-------|-------|------|------|
| `ink.950` | `#0E1218` | — | Strongest text (light mode) |
| `ink.900` | `#161B22` | `#E8ECF1` | Primary text |
| `ink.700` | `#3A4452` | `#B7C0CC` | Secondary text |
| `ink.500` | `#6B7685` | `#8B95A5` | Tertiary / captions |
| `ink.300` | `#C5CDD8` | `#3D4654` | Borders / rules |
| `ink.200` | `#E2E7EE` | `#2A313C` | Dividers / tracks |
| `ink.100` | `#F1F3F7` | `#1C222B` | Subtle fill |
| `ink.50` | `#F7F8FA` | `#141920` | App background |
| `ink.0` | `#FFFFFF` | `#0E1218` | Elevated surface |

**Surfaces**

| Token | Light | Dark | Use |
|-------|-------|------|-----|
| `surface.app` | `ink.50` | `ink.0` | Shell background |
| `surface.panel` | `ink.0` | `ink.100` | Sidebar, rails |
| `surface.raised` | `ink.0` | `ink.100` | Modals, popovers |
| `surface.sunken` | `ink.100` | `ink.0` | Inputs, code wells, viewer gutter |

## 2.2 Brand accent (Signal)

Replace violet with a **deep teal-ink** accent: scientific, calm, uncommon in consumer AI UIs.

| Token | Value | Use |
|-------|-------|-----|
| `signal.600` | `#0F6E6A` | Primary actions, links, focus ring |
| `signal.500` | `#14807B` | Hover / active |
| `signal.100` | `#D8F0EE` | Soft selected (light) |
| `signal.900` | `#083B39` | Soft selected (dark) / text on soft |

**Do not** use signal for success/error/grade—those are semantic.

## 2.3 Semantic science palette

Used in Evidence, Classify, Pipeline, Graph—not in global chrome.

| Token | Hex | Meaning |
|-------|-----|---------|
| `sem.ready` | `#2F6F4E` | Completed / pass / ready bands |
| `sem.running` | `#1B6B8A` | Active AI work in progress |
| `sem.queued` | `#6B7685` | Waiting / not started |
| `sem.error` | `#B42318` | Failed / destructive |
| `sem.warn` | `#B54708` | Quality warnings, low confidence caution |
| `sem.info` | `#175CD3` | Neutral informational chips |

### 2.3.1 AI state colors (pipeline ladder)

Dedicated tokens for the **canonical AI journey**. These are the only colors used for pipeline status chrome (badges, steppers, dashboard widgets). Do not invent per-page variants.

| State ID | Label (UI copy) | Token | Dot / icon treatment |
|----------|-----------------|-------|----------------------|
| `ai.upload` | Uploading | `sem.info` | Soft pulse on icon |
| `ai.queued` | Queued | `sem.queued` | Static hollow/muted — waiting, not yet AI |
| `ai.understand` | Understanding | `sem.running` | Soft pulse |
| `ai.classify` | Classifying | `sem.running` | Soft pulse |
| `ai.evidence` | Evidence Ready | `sem.ready` | Static check |
| `ai.graph` | Graph Ready | `sem.ready` | Static check |
| `ai.chat` | Chat Ready | `signal.600` | Static; means “inquiry unlocked” |
| `ai.error` | Needs attention | `sem.error` | Static alert |
| `ai.idle` | Not started | `sem.queued` | Hollow / muted |

**Rule:** **Uploading** = transfer/validation in flight (`sem.info`). **Queued** = upload finished, waiting for a worker—must not look like AI has started. Mid-pipeline AI work (`Understanding`, `Classifying`) shares `sem.running`. Readiness bands share `sem.ready` until **Chat Ready**, which uses brand `signal` to mark the shift from *processing* to *conversation*.

**Evidence grades (map, don’t invent science)**

| Grade band | Color role |
|------------|------------|
| High / strong | `sem.ready` |
| Moderate | `signal.600` |
| Low | `sem.warn` |
| Very low / critical RoB | `sem.error` |
| Unrated | `ink.500` |

**Confidence meter**

- Track: `ink.200`  
- Fill: interpolate `sem.warn` → `signal.600` → `sem.ready` by threshold bands (not a rainbow gradient bar)

## 2.4 Chat-specific

| Token | Light | Dark | Notes |
|-------|-------|------|-------|
| `chat.user` | `signal.100` | `signal.900` | User bubble—quiet, not neon |
| `chat.assistant` | transparent / `surface.app` | same | Assistant is not a bubble wall |
| `chat.rail` | `surface.panel` | `surface.panel` | Evidence rail |

## 2.5 Forbidden (target system)

- Violet / indigo as primary (`#7c3aed`, `#8b5cf6` and kin)  
- Purple→indigo hero gradients  
- Glow / bloom on focus  
- Success = bright lime neon  
- Warm paper cream as default app background  

---

# 3. Typography

## 3.1 Families

| Role | Family | Rationale |
|------|--------|-----------|
| **Brand / UI display** | **Creato Display** (existing asset) | Keep as Soro’s signature; use for nav titles, page titles, empty-state headlines |
| **UI body** | **Creato Display** at regular/medium for controls; or system UI sans if Creato feels heavy at 13–14px | Prefer readability in dense tables |
| **Reading (paper narrative, long analysis)** | **Source Serif 4** or **Literata** | Scholarly reading; distinguishes “content” from “chrome” |
| **Data / IDs** | **IBM Plex Mono** or **JetBrains Mono** | DOIs, scores, phase keys, graph IDs |

## 3.2 Scale

| Token | Size / line | Weight | Use |
|-------|-------------|--------|-----|
| `display` | 32 / 40 | 500–700 | Rare: Home hero line, empty states |
| `title.lg` | 24 / 32 | 600 | Page title |
| `title.md` | 20 / 28 | 600 | Panel / tab section |
| `title.sm` | 16 / 24 | 600 | Card object titles |
| `body.md` | 15 / 24 | 400 | Default UI |
| `body.sm` | 13 / 20 | 400 | Secondary, tables |
| `caption` | 12 / 16 | 500 | Labels, steppers (not all-caps spaghetti) |
| `overline` | 11 / 14 | 600 | Optional section label; letter-spacing +0.04em max |
| `mono.sm` | 12 / 16 | 400 | Scores, DOIs |

**Rules**
- Avoid all-caps micro-labels as the default hierarchy (current UI overuses them). Prefer weight + size.  
- Paper narrative and LLM overview render in the **reading** family.  
- Chat messages: UI body; long assistant prose may use reading family at `body.md`.

---

# 4. Layout & Spacing

## 4.1 Space scale (4-based)

`4 · 8 · 12 · 16 · 24 · 32 · 48 · 64`

| Token | px | Use |
|-------|----|-----|
| `space.1` | 4 | Icon gaps |
| `space.2` | 8 | Compact stacks |
| `space.3` | 12 | Control padding |
| `space.4` | 16 | Default stack |
| `space.5` | 24 | Section gap |
| `space.6` | 32 | Panel padding |
| `space.7` | 48 | Page sections |
| `space.8` | 64 | Rare breathing room |

## 4.2 Grid

- App shell: sidebar **240px** (collapsed **64px**); main fluid.  
- Paper split: viewer **minmax(320px, 42%)** / panel flex.  
- Content max width for reading columns: **720px**; for data tables: full main width.  
- Page horizontal padding: `24` desktop, `16` mobile.

## 4.3 Density modes

| Mode | Where |
|------|-------|
| **Comfortable** | Home, Settings, empty states |
| **Compact** | Evidence tables, Library grid, Graph side lists |

---

# 5. Radius, Stroke, Elevation

## 5.1 Radius

| Token | px | Use |
|-------|----|-----|
| `radius.none` | 0 | Tables, graph canvas edge |
| `radius.sm` | 4 | Inputs, chips |
| `radius.md` | 8 | Buttons, menus |
| `radius.lg` | 12 | Panels, dialogs |
| `radius.xl` | 16 | Upload dropzone only |

**Avoid** pill (`9999`) as default for filters/actions. Chips use `radius.sm`.

## 5.2 Stroke

- Default rule: `1px` `ink.200`  
- Strong rule: `1px` `ink.300`  
- Focus: `2px` `signal.600` ring, offset 2px—**no glow**

## 5.3 Elevation

Prefer **border + background** over shadow stacks.

| Level | Treatment |
|-------|-----------|
| 0 | Flat on `surface.app` |
| 1 | `surface.panel` + hairline border |
| 2 | Modal: border + single soft shadow `0 8px 24px rgba(14,18,24,0.12)` (light) / `0 8px 24px rgba(0,0,0,0.45)` (dark) |

No multi-layer colored shadows.

---

# 6. Iconography

- **Family:** Lucide (already in product)—keep for consistency.  
- **Optical size:** 16 default; 20 for nav; 14 inline in tables.  
- **Stroke:** 1.75–2; match text weight, don’t go ultra-thin.  
- **Color:** inherit `ink.700`; active nav uses `signal.600`.  
- **Never** use emoji as status indicators in product chrome.

---

# 7. Components (design contracts)

Design language for building blocks—not React APIs.

## 7.1 Buttons

| Variant | Look | Use |
|---------|------|-----|
| **Primary** | Filled `signal.600`, white label | One primary per view |
| **Secondary** | Quiet fill `ink.100` / border | Secondary actions |
| **Ghost** | No fill | Tertiary, toolbars |
| **Destructive** | `sem.error` outline or soft fill | Deletes |
| **Size** | sm 32 · md 36 · lg 40 height | Compact tables use sm |

No gradient buttons. No shine.

## 7.2 Inputs

- Height 36; `radius.sm`; sunken surface.  
- Label above (not floating).  
- Error: text + border `sem.error`, not only color.

## 7.3 Chips / badges

| Kind | Style |
|------|-------|
| **Pipeline / AI state** | Always use **AI State Language** (§12): same label + dot + color everywhere |
| **Classification** | Neutral border chip; signal border when selected |
| **Confidence** | Mono score + thin meter |
| **Grade** | Semantic fill soft, not loud |

## 7.4 Tabs (Paper Workspace)

- Underline tabs, not pill tabs.  
- Active: `signal.600` underline 2px + `ink.900` label.  
- Overflow: scroll with fade edges on tablet/mobile.

## 7.5 Tables (Evidence)

- Hairline rows; compact density default.  
- Sticky header on `surface.panel`.  
- Row hover: `ink.100`.  
- Selected row: `signal.100` / `signal.900`.

## 7.6 Cards

Allowed when the object is **selectable or navigable** (Library paper, Project).  
Structure: title · meta line · pipeline badge.  
No card for static text blocks in Paper tabs—use sections + rules.

## 7.7 Navigation

- Sidebar: quiet; active item = left 2px signal bar + soft fill (not heavy pill).  
- Bottom mobile bar: 4 items; labels 10–11px; active = signal icon + label.

## 7.8 Chat

- User: soft signal bubble, max-width ~640px.  
- Assistant: full-bleed text column, no bubble.  
- Streaming: thin signal caret / pulse on last line—no skeleton fireworks.  
- Evidence rail: panel, not floating stickers on the transcript.

## 7.9 Empty states

- One display line + one sentence + one primary CTA.  
- Illustration optional: abstract line diagram (instrument), not mascots.

## 7.10 Overlays

- Dialogs: `radius.lg`, level-2 elevation, clear title + actions right-aligned.  
- Sheets (mobile): full-width, handle, same tokens.

---

# 8. Motion

| Motion | Duration | Easing | Use |
|--------|----------|--------|-----|
| Micro | 120–160ms | standard | Hover, press |
| Panel | 200–280ms | emphasized | Rail / sheet open |
| Status | 300ms | linear or soft | Pipeline step advance |
| Stream | continuous | — | Token reveal; respect `prefers-reduced-motion` |

**Ship 2–3 intentional motions in visually led surfaces:** (1) pipeline step advance, (2) evidence row → viewer focus, (3) evidence rail open.  
**Reduce motion:** instant panel swap; no step animation; keep stream text.

No parallax, no background blob animation.

---

# 9. Content & Voice

| Do | Don’t |
|----|-------|
| “Phase 1 ready — structure and evidence available” | “AI finished cooking ✨” |
| “Evidence grade: Low — inspect rationale” | “Trust score: 🔥” |
| “Upload to Library” | “Drop your vibes” |
| Error codes mapped to plain language | Raw `invalid_mime` in the headline |

**Number formatting:** confidence as `0.82` or `82%`—pick one product-wide (recommend **%** for UI, raw in advanced).

---

# 10. Accessibility

| Requirement | Spec |
|-------------|------|
| Contrast | Body text ≥ 4.5:1 on surfaces; UI chrome ≥ 3:1 |
| Focus | Visible signal ring; never remove outline without replacement |
| Hit targets | ≥ 40×40px interactive on touch |
| Status | Never color-only: pair with text/icon |
| Motion | Honor reduced motion |
| Labels | Icon-only controls require accessible names |
| Skip link | “Skip to main content” on app shell |

---

# 11. Theme modes

| Mode | Default? | Notes |
|------|----------|-------|
| **Light** | **Yes (target)** | Primary research look |
| **Dark** | Optional | Same tokens remapped; keep semantic hues slightly desaturated for eye comfort |
| System | Follow OS | Settings |

Migration: stop shipping dark as the unspoken brand; make light the marketing and default logged-in experience unless user chose dark.

---

# 12. AI State Language

The most important consistency layer in Soro. Users should recognize **where a paper is in the system’s understanding** without relearning status UI on each screen.

## 12.1 Canonical ladder

Always present in this order (skip visually only if a stage is N/A for that document type—never reorder):

```
Uploading
    ↓
Queued
    ↓
Understanding
    ↓
Classifying
    ↓
Evidence Ready
    ↓
Graph Ready
    ↓
Chat Ready
```

| Stage | User meaning | Backend mapping (conceptual) |
|-------|--------------|------------------------------|
| **Uploading** | File is transferring / validating | Client upload, MIME/AV checks, object storage write |
| **Queued** | Upload finished; waiting for a worker | Job enqueued (outbox / `upload_jobs` / Redis queue)—**AI has not started** |
| **Understanding** | Structure & quality extraction has started | Phase 1.1 document understanding running |
| **Classifying** | Type, domain, design, context | Phase 1.2 (+ 1.3 summary) |
| **Evidence Ready** | Grades / RoB / outcomes usable | Phase 1.4–1.5 usable for Evidence tab |
| **Graph Ready** | Relationships usable | Phase 1.7 knowledge graph ready |
| **Chat Ready** | Grounded inquiry unlocked | Pipeline ready enough for paper chat + rail |

**Why Queued exists:** Background workers introduce a real gap after upload completes. Without **Queued**, that silence looks like a hang. The label teaches: *your file is safe; the system is waiting its turn—not stuck transferring, and not yet “thinking.”*

**Composite “headline” state** (for compact badges): the **furthest completed** stage, or the **current running** stage if mid-flight, or **Needs attention** if any blocking error.

Examples:
- Running classify → badge: **Classifying**  
- DU+classify done, grading done, graph pending → badge: **Evidence Ready** (graph step still pending in stepper)  
- All green → badge: **Chat Ready**

## 12.2 One pattern, four surfaces

Same DNA everywhere—only **density** changes.

| Element | Spec |
|---------|------|
| **Dot** | 8px circle; color from §2.3.1; pulse only for **Uploading**, **Understanding**, **Classifying** — **Queued** is static muted |
| **Label** | Exact strings above; `caption` / `body.sm`; never synonyms (“Processing…”, “AI magic”, “Analyzing docs”) |
| **Optional meta** | Mono time estimate or phase detail on hover/expand—not instead of the label |
| **Error** | Label **Needs attention** + short reason on expand; same `sem.error` treatment |

### Library
- On each **FileCard**: compact **AI State Badge** (dot + label).  
- Multi-select / filters: filter by headline state (`Chat Ready`, `Classifying`, …).  
- Upload zone: live list rows use the same badge while files climb the ladder.

### Paper Workspace
- **Pipeline Stepper** under the title: all six stages as nodes; current = pulse + signal underline; done = ready check; future = muted hollow.  
- Tab availability mirrors state: Evidence tab enabled at **Evidence Ready**; Graph at **Graph Ready**; Chat CTA emphasized at **Chat Ready**.  
- Tabs not yet unlocked: visible but quiet, with tooltip “Available when [State].”

### Projects
- Project paper lists: same badge as Library.  
- Project Overview: **mix strip**—counts per headline state (e.g. 4 Chat Ready · 2 Classifying · 1 Needs attention). Same colors/dots as badges.  
- No separate “project progress” metaphor.

### Dashboard
- **Continue research** / attention widgets use the same badges.  
- “Needs attention” and “Almost ready” (e.g. Evidence Ready but not Chat Ready) use identical components—not custom dashboard chips.

## 12.3 Stepper anatomy (Paper + expanded Library drawer)

```
(•) Uploading — (•) Queued — (•) Understanding — (•) Classifying — (✓) Evidence Ready — ( ) Graph Ready — ( ) Chat Ready
```

| Node state | Visual |
|------------|--------|
| Pending | Hollow circle `ink.300`, label `ink.500` |
| Active (Uploading / Understanding / Classifying) | Filled stage color, soft pulse, label `ink.900` |
| Active (**Queued**) | Filled `sem.queued`, **no pulse**, label `ink.900` — waiting, not working |
| Complete | Filled `sem.ready` + check, or `signal.600` check for Chat Ready |
| Error | Filled `sem.error` + alert; ladder pauses here |

Connectors: 1px `ink.200`; completed segment `sem.ready`.

## 12.4 Motion for AI states

| State | Motion |
|-------|--------|
| Uploading / Understanding / Classifying | Dot pulse 1.2s loop; opacity 1.0 → 0.45; respect reduced motion → static |
| Queued | **No pulse** — static muted; optional subtle connector shimmer only if reduced-motion allows |
| Ready bands | No loop; optional 200ms check draw-in once |
| Transition between stages | Connector fill 300ms; one step at a time |

Never confetti, never full-card shimmer for stage changes.

## 12.5 Voice lock (copy)

Allowed labels (exact):

- Uploading  
- Queued  
- Understanding  
- Classifying  
- Evidence Ready  
- Graph Ready  
- Chat Ready  
- Needs attention  

Disallowed substitutes: Processing, Analyzing, Magicking, Working, Pending (as a user-facing substitute for Queued or any Ready stage), Done, Complete (use the specific Ready label).

Each allowed label maps to a real stage of the backend journey. Vague progress words are forbidden because they hide whether the file is still transferring, waiting on a worker, or already under AI analysis.

## 12.6 Accessibility

- Color never sole indicator: always visible text label.  
- Pulse omitted when `prefers-reduced-motion`.  
- Screen reader: “Status: Classifying” / “Status: Chat Ready”.  
- Focusable badges where they open the Processing drawer or Paper stepper.

## 12.7 Anti-patterns

- Different wording on Dashboard vs Library (“AI running” vs “Classifying”).  
- Skipping **Queued** so post-upload silence looks broken.  
- Pulsing **Queued** as if AI had started.  
- Green “Ready” that doesn’t say *what* is ready.  
- Hiding Graph Ready because the Graph tab is empty—show state honestly.  
- Using brand violet/legacy purple for pipeline dots.  
- Celebratory overlays when Chat Ready fires.

---

# 13. Domain patterns (science UI)

## 13.1 Pipeline stepper

Implements **AI State Language** (§12). Paper Workspace uses the full six-node stepper; Library/Dashboard use the compact badge derived from the same state machine.

## 13.2 Evidence matrix

Compact table; grade chip; confidence meter; click → opens provenance.  
Empty: “No graded outcomes yet — run analysis or wait for pipeline.”

## 13.3 Knowledge graph

Canvas background `ink.50` / dark `ink.0`.  
Nodes: quiet fills by type (Population / Intervention / Outcome / Study)—use a **muted categorical set** (blue-gray, teal, ochre, slate)—not neon categorical rainbow.  
Selection: signal ring.  
Minimap optional on desktop only.

## 13.4 Document viewer

Gutter `surface.sunken`; page canvas white even in dark mode (reading comfort) with dark chrome around it.  
Highlight: signal soft fill at 25% opacity.

---

# 14. Asset & brand applications

| Asset | Spec |
|-------|------|
| Wordmark | “Soro” in Creato Display Medium; ink.900 / ink.0 on dark |
| Mark (optional later) | Geometric “instrument” monoline—not a robot head |
| Favicon | Simplified mark or “S” in signal on ink |
| OG / marketing | Light surface, display type, one paper metaphor—no purple haze |

---

# 15. Anti-patterns (explicit)

1. Violet primary / purple gradients  
2. Default dark as brand identity  
3. Pill filter clusters and badge spam  
4. Card wrapping every paragraph  
5. Multi-shadow glassmorphism  
6. Emoji status  
7. All-caps label forests  
8. Glow focus rings  
9. Inter/Roboto as brand (Creato stays; don’t regress to generic SaaS sans-only)  
10. Warm cream + terracotta “editorial AI” cliché  

---

# 16. Adoption roadmap (design → product)

| Stage | Design work | Notes |
|-------|-------------|-------|
| **D1** | Token remap (neutrals + signal) in Figma / token sheet | Visual PR can follow later |
| **D2** | Sidebar + buttons + tabs restyle | Matches UI-Architecture M0 |
| **D3** | **AI State Language** — badge + stepper + copy lock across Library / Paper / Projects / Dashboard | With M3; non-negotiable consistency |
| **D4** | Evidence table + confidence | With M6 |
| **D5** | Graph categorical colors + viewer chrome | With M7–M9 |
| **D6** | Light-default + dark audit | Settings + onboarding |

---

# 17. Success criteria

The system succeeds when:

1. A screenshot with the logo cropped still reads as **Soro**, not a violet chat clone.  
2. Evidence and pipeline states are understandable in grayscale (shape + text).  
3. Paper reading (serifs) is visually distinct from app chrome (sans).  
4. Light mode feels intentional and premium—not an afterthought invert.  
5. Motion is limited to state-explaining moments.  
6. A user who learns **Queued** / **Classifying** / **Evidence Ready** / **Chat Ready** on Library recognizes the same states on Paper, Projects, and Dashboard without new vocabulary.  
7. After upload finishes, **Queued** is visible before **Understanding**—users never confuse “waiting for a worker” with “nothing happened.”

---

## Phase-1 completeness note

With the **Queued** stage and locked human terminology, this design system is considered **feature-complete for the first implementation phase** and is **locked as Product Specification v1.0** (see [`PRODUCT-SPEC.md`](PRODUCT-SPEC.md)). Later phases may extend grades/graph density—not the ladder vocabulary—via a version bump.

---

*End of Soro Design System — design specification only; no code or components shipped in this document.*
