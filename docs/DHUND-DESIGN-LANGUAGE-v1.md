# Dhund Design Language v1

**Status:** **Frozen doctrine** — Phases 1–3 complete; no more inspiration sources. Ready for execution on approval.  
**Date:** 2026-08-05  
**Type:** Brand + product visual **governance** (not code)  
**Sources (Phase 1):** Apple · Linear · Vercel · Notion · Together AI · Airtable  
**Sources (Phase 2):** Stripe · Framer · Superhuman · Cursor  
**Sources (Phase 3):** Tesla · SpaceX · Replicate · Mintlify · Figma  
**Companions:** [`PRODUCT-CONSTITUTION-v1.md`](PRODUCT-CONSTITUTION-v1.md) · [`DESIGN-SYSTEM.md`](../DESIGN-SYSTEM.md) · [`docs/DESIGN-SYSTEM-v2.md`](DESIGN-SYSTEM-v2.md) · [`docs/Interaction-Guidelines.md`](Interaction-Guidelines.md)

**Product filter:** Before adding UI chrome, apply [`PRODUCT-CONSTITUTION-v1.md`](PRODUCT-CONSTITUTION-v1.md) — especially Invisible Intelligence, One Purpose Per Screen, and **Home Invisible · Intelligence Magical**. Visual language never overrides those.

**Surface emotional ownership (frozen)**

| Surface | Feel |
|---------|------|
| Home | Invisible orientation — calm desk, one milestone. **Frozen** for polish (2026-08-08). |
| Projects | Continuity — continue-first bookshelf; empty state starts the research journey (Publish vocabulary). **Frozen** (2026-08-08). |
| Sidebar | Quiet infrastructure — soft active pill, no teal rail. **Frozen** (2026-08-08). Discover via ⌘K. |
| Library | Effortless control — which paper to read next (Continue \| Recommended), not a paper database. |
| Research Intelligence | Magical insight — Dhund’s signature. |
| Writing | Flow from evidence. |
| Review | Publication confidence. |

Do **not** put brand spectacle on Home. Signature craft (Evidence Inspector, provenance, RI lenses) belongs in the workflow screens.

### Typography color tokens (hierarchy, not decoration)

| Token | CSS | Use |
|-------|-----|-----|
| `text.primary` | `--text-primary` / `text-text-primary` | Headlines, titles, project name |
| `text.secondary` | `--text-secondary` / `text-text-secondary` | Body, supporting context |
| `text.tertiary` | `--text-tertiary` / `text-text-tertiary` | Labels, metadata (`NEXT MILESTONE`) |
| `text.accent` | `--text-accent` / `text-text-accent` | Links, active nav, actionable concepts only |
| `text.success` / `warning` / `danger` / `info` | semantic | Evidence / RI / Review — never Home chrome |

**Ratio:** ~90% neutral · ~8% teal accent · ~2% semantic. Color carries meaning, never decoration.

**Intent:** A maintainable **design governance document** — ownership by surface, density, borders, confidence, and cognitive load — so Dhund stays visually consistent for years.

**Hard rules**
- **Inspiration closed.** Do not add new reference brands. Execute this language.
- Do **not** implement UI until Muhammad confirms the freeze (or explicitly says “implement”).
- Prefer extending existing Dhund tokens (`signal` teal, ink ladder, AI state language) over inventing a second palette.

---

## 0. One-sentence brand

> Dhund is a **light-first research instrument**: Linear density in tooling, Notion calm in writing, Mintlify clarity in docs, Figma inspection for evidence — marketed with Apple/Tesla product confidence and SpaceX-grade **Trust Layer** austerity when institutional credibility must be absolute. Teal is the only brand voltage; evidence and pipeline stages are the only places color gets loud. Nothing feels magical — everything feels inspectable.

---

## 1. What each brand contributes (and what we refuse)

| Brand | Borrow for Dhund | Leave behind | Where it lands |
|-------|------------------|--------------|----------------|
| **Apple** | Product-first hero; chrome recedes; one interactive color; hairline dividers; generous section air on **marketing only**; photography/product as museum object | SF Pro lock-in; Action Blue; consumer retail configurators; edge-to-edge alternating light/dark as app default | Landing hero, brand moments, empty states that feel “finished” |
| **Linear** | Workstation density; hairline panels; quiet type; single accent used sparingly; screenshots of real product as proof; 4–8–12–16 radius ladder; focus rings | Near-black marketing as **app** default; lavender `#5e6ad2`; issue-tracker metaphors | Evidence panel, Library rows, Pipeline chrome, Settings density, AI Execution inspector |
| **Vercel** | Ink-on-near-white subtraction; Geist-like tight tracking for display; mono eyebrows for technical labels; 1px borders; square 6px app chrome vs pill marketing CTAs | Mesh hero gradients; violet/magenta brand candy; deploy/ops metaphors | App shell, Search, Citations table, Developer/API honesty, Capability Router labels |
| **Notion** | Content-first pages; calm side panels; reading line length; soft off-white canvas; quiet chrome so the document wins | Sticker rainbow personality; block playground as identity; playful consumer warmth in science chrome | Writing workspace, Paper narrative/overview reading, Notes |
| **Together AI** | Alternating research/docs bands; uppercase **mono eyebrows** for technical sections; AI infra seriousness without chat bubbles | Orange–magenta–periwinkle gradient as brand chrome; black-primary everywhere; hype infrastructure vibe | AI Execution / Prompt Engine surfaces, model routing labels, research-band sections on landing |
| **Airtable** | Editorial workflow clarity; sober ink; full-bleed **signature panels** used sparingly to punctuate long explainers; modest type weights | Coral/forest signature cards as app wallpaper; multi-color “voltage” cards inside the OS | Landing “How it works” / Ecosystem explainers; rare marketing callout panels only |

### Phase 2 — Premium polish

| Brand | Borrow for Dhund | Leave behind | Where it lands |
|-------|------------------|--------------|----------------|
| **Stripe** | Thin editorial display (weight ~300–400) on marketing; **tabular numerals** for counts/scores; composited **real product mockups** as proof; soft blue-tinted shadow only on floating panels; one filled CTA per band | Atmospheric **gradient mesh** as brand identity; electric indigo `#533afd`; navy-as-app-default; money-SaaS metaphor | Landing hero type air; Citations/quotas numerics; pricing; trust via product screenshots |
| **Framer** | Poster-grade negative tracking on **landing H1 only**; gradient/atmosphere as **isolated showcase cards** (max 1–2 per viewport), never full-section washes; white/dark polarity for rare marketing bands | Dark canvas as brand identity; extreme −5px tracking in-app; magenta/violet/orange spotlight grid as recurring motif; perpetual motion as personality | Landing section openers; optional one “atmosphere” card in Ecosystem/How-it-works — not the OS |
| **Superhuman** | **Three-band marketing rhythm**: dark/indigo hero → white body → **deep teal closing CTA**; **one CTA per band**; mid-weights (460–540 feel) for warmth; tight display leading | Required portrait photography; violet-sky atmosphere; pale-violet hero pills; indigo navy as primary fill | Landing structure (esp. final CTA band = Dhund `signal` dark teal); marketing CTA discipline |
| **Cursor** | Warm-editorial restraint; **scarce single accent**; display weight 400 magazine voice; **AI timeline pastels scoped only to agent/pipeline stages**; hairline-only depth; generous mono on technical surfaces; 80px marketing section rhythm | Cursor Orange `#f54e00`; warm cream canvas replacing cool paper; pastel pills as system action colors | Research Progress / Capability Router / AI Execution stage chips; loading & streaming honesty; command density |

### Phase 3 — Signature details

| Brand | Borrow for Dhund | Leave behind | Where it lands |
|-------|------------------|--------------|----------------|
| **Tesla** | Radical subtraction; **product imagery does the talking**; near-zero chrome decoration; weight 400/500 only; ~0.33s ease on state changes; frosted/transparent nav over hero | Electric Blue `#3E6AE1`; persistent chatbot bar; car-showroom metaphor; zero borders as app law | Landing hero; empty states; “finished” product moments |
| **SpaceX** | Mission austerity; full-bleed proof imagery; **ghost outline** secondary CTAs; uppercase micro for mission/trust eyebrows; one action per band | Pure black as identity; all-caps display everywhere; aerospace DIN as UI face; no-accent absolutism (Dhund keeps teal) | **Trust Layer** (security, compliance, privacy, reproducibility, audit); rare “mission” marketing bands |
| **Replicate** | Dark **code-story** bands as pull-quotes; three-family discipline (display / UI / mono); scarce hot accent pattern → map to teal; notebook/diagram energy for architecture | Hot orange `#ea2804`; cream canvas takeover; fully-rounded every control; 128px display in-app | API / AI how-it-works; Capability Router explainers; code wells |
| **Mintlify** | **3-column docs** (sidebar / prose / TOC); Inter+mono pairing for docs; dense 14–16px long-form; black/teal CTAs scarce; flat docs cards | Mintlify mint `#00d4a4` as brand (Dhund teal wins); sky-gradient heroes as default; testimonial orange | Contracts, ADR viewers, API reference, in-product docs, Settings help |
| **Figma** | **Canvas + inspector** split; monochrome chrome with intentional story panels; fine variable weights; mono uppercase taxonomy labels | Pastel sticky-note full-bleed blocks in the OS; black as only CTA (teal stays); FigJam joy-as-identity | Evidence inspector; Paper workspace; collaboration panels; optional one marketing story block |

---

## 1c. Phase 3 decisions (the important ones)

### Tesla subtraction vs SpaceX Trust Layer
**Tesla wins for default landing calm** (white canvas, product first — *premium product*). **SpaceX wins for the Trust Layer** only — pure black + ghost CTAs when institutional credibility must feel absolute (*engineering credibility*). Never make SpaceX black the Research OS shell.

Security, compliance, privacy, reproducibility, audit, and enterprise controls are all **manifestations of the Trust Layer** — not separate “website section” aesthetics.

### Mintlify docs layout — adopt?
**Yes — strongest Phase 3 gift.** Dhund contracts, ADRs, API, and in-app help should follow **sidebar / prose / TOC**. Keep Dhund `signal` teal for accents — do not switch to Mintlify mint.

### Figma inspector — where?
**Evidence + Paper workspace.** Main canvas = content; right (or side) inspector = claims, spans, metadata, AI execution. Matches DESIGN-SYSTEM-v2 workstation intent. Reject Figma’s pastel story blocks **inside** the OS.

### Replicate code-story bands
**Yes for API / Router / “how AI runs” marketing and docs.** Dark mono wells as pull-quotes on light pages. Reject orange and cream identity.

### Collaboration UI
Figma’s calm inspector + Mintlify’s dense prose + Linear’s rows — not FigJam stickies. Shared evidence stays **instrument**, not whiteboard carnival.

---

### Stripe mesh — where / where not?
**Not** as Dhund’s brand sky. Stripe’s mesh *is* Stripe. Dhund’s trust argument is **evidence + product screenshots**, not atmospheric candy.  
**Yes** to: thin marketing display, tabular numerals on counts/scores/quotas, soft shadow on floating command palette / modals only, one filled CTA per band.

### Framer motion & posters — landing only?
**Yes.** Extreme tracking and dark artboard energy stay on **marketing**. In-app Framer energy would fight Linear density and Notion reading calm.  
Atmosphere gradients: allowed as **at most one showcase card** on landing (Framer rule: cards, not section grounds). Never in Evidence, Writing, or Library.

### Superhuman three-band — adopt?
**Yes for landing.** Hero (dark or product) → light explanatory body → **closing band in deep teal** (`signal.900` / `#083B39`–`#0e3030` range). This is the strongest Phase 2 gift — Superhuman’s teal close band maps cleanly onto Dhund’s existing signal.  
**One CTA per band** becomes marketing law. Reject violet hero pills and mandatory portraits.

### Cursor AI timeline — map to Dhund pipeline?
**Yes, pattern only.** Cursor scopes pastels to agent stages — Dhund scopes **pipeline / Router / progress** chips the same way: color only inside the stage strip, never as global chrome.  
Use **existing** `sem.*` / AI state tokens — do **not** import Cursor’s peach/mint/lavender palette or orange CTA.

### Loading & micro-interactions
| State | Feeling | Borrow |
|-------|---------|--------|
| Streaming answer | Quiet cursor / progressive reveal | Cursor honesty + Linear restraint |
| Pipeline running | Stage chips + calm progress | Cursor timeline pattern + Dhund `sem.running` |
| Command palette / Ask | Instant, dense, hairline | Cursor + Linear |
| Landing hover | Icon Cloud spin; beam explain | Existing Dhund rules |
| “AI done” | Status text + ready chip — never confetti | All Phase 1–2 seriousness |

---

## 2. Brand philosophy (Dhund-specific)

1. **Instrument, not entertainment** — Density is allowed; spectacle is not. (Keep from existing DESIGN-SYSTEM; reinforced by Linear + Vercel + Cursor.)
2. **Evidence has a color; chrome does not** — Neutrals carry the shell. Semantic color is for pipeline, confidence, grades — never rainbow decoration (reject Notion stickers, Together/Stripe meshes, Airtable signature cards **inside the app**, Framer spotlight grids).
3. **One accent** — Deep teal `signal` (`#0F6E6A`). Not Linear lavender, Apple blue, Stripe indigo, Cursor orange, or Vercel mesh.
4. **Light is first-class** — Research happens in offices and daylight. Linear/Framer dark is optional for **landing contrast bands**, never the default Research OS shell.
5. **Cards are rare** — Surfaces + hairlines (Vercel/Linear/Cursor). Cards only when the object is selectable or actionable.
6. **Motion explains state** — Pipeline, stream, beam, panel open/close. Hover-only Icon Cloud. No perpetual decorative spin (Framer motion ≠ app default).
7. **Reading ≠ tooling** — Writing/Paper follow Notion’s calm; Evidence/Library follow Linear’s density. Mixing them in one surface is a bug.
8. **One CTA per marketing band** — Superhuman discipline; Stripe sparseness.
9. **Brand test** — Remove the word “Dhund”: it should still feel like a research OS, not ChatGPT-violet or generic SaaS.
10. **Nothing magical** — Every AI decision is inspectable; every evidence object exposes provenance; confidence is visible. (Confidence Doctrine — §2b.)

---

## 2b. Frozen doctrines (Dhund-native)

These are **governance rules**, not brand borrows. They keep the language maintainable for years.

### Visual Density Doctrine

| Surface | Density | Notes |
|---------|---------|-------|
| Landing | **Low** | Tesla/Apple air; one job per band |
| Writing | **Low** | Notion measure; chrome recedes |
| Reading (Paper narrative/overview) | **Medium** | Calm but structured |
| Evidence | **High** | Linear inspector density |
| Library | **High** | Rows, status, scan |
| Search / Discover | **High** | Hits + filters, no waste |
| Docs (API / ADR / contracts) | **Medium** | Mintlify prose + nav |
| Settings | **Medium** | Clear, not sparse |
| Trust Layer | **Low–Medium** | SpaceX austerity; proof over chrome |
| AI Execution / Router | **High** | Technical, inspectable |

**Rule:** If a High-density surface feels airy, it is wrong. If a Low-density surface feels like a dashboard, it is wrong.

### Border Doctrine

```text
Structure = 1px borders (hairlines).
Elevation = shadows (modals, popovers, command palette only).

Borders → structure
shadows → floating above the surface

Never use shadow to invent hierarchy between peer panels.
```

Aligned with Linear + Apple + Cursor hairline discipline.

### Confidence Doctrine

```text
Every AI decision should feel inspectable.
Every evidence object should expose provenance.
Confidence should be visible.
Nothing should feel magical.
```

This is **only Dhund** — not Apple, not Linear. It binds Evidence inspector, AI Execution, Capability Router, grounded writing, and reviewer flows.

### Cognitive Load Doctrine

```text
Every screen answers only one primary question.
```

| Surface | Primary question |
|---------|------------------|
| Library | What do I have? |
| Search / Discover | What exists? |
| Evidence | What is true? |
| Writing | What should I say? |
| Reviewer | Can I defend this? |
| Paper workspace | What does this paper say / contain? |
| Projects | What am I working on? |
| Docs | How does this work? |
| Settings | How does Dhund behave? |
| Trust Layer | Can I trust Dhund with this work? |
| Dashboard | What should I do next? |

**Rule:** If a screen answers two primary questions equally, split it or demote one to secondary chrome.

---

## 3. Color philosophy

### 3.1 Keep (locked DNA)

| Role | Token direction | Hex (light) | Rationale |
|------|-----------------|-------------|-----------|
| Accent | `signal.600` | `#0F6E6A` | Distinct from consumer AI violet; scientific; already shipping |
| App canvas | `ink.50` | `#F7F8FA` | Cool paper (Vercel `#fafafa` + Notion soft, but cooler than Notion `#f6f5f4`) |
| Elevated | `ink.0` | `#FFFFFF` | Raised panels |
| Primary text | `ink.900` | `#161B22` | Near Vercel/Airtable ink, not pure Notion black |
| Muted | `ink.500` | `#6B7685` | Captions, meta |
| Hairline | `ink.200` / border | `#E2E7EE` | Linear/Vercel 1px language |

Semantic science palette (**Evidence / Pipeline only**): keep `sem.ready`, `sem.running`, `sem.queued`, `sem.error`, `sem.warn`, `sem.info` from DESIGN-SYSTEM.md.

### 3.2 Explicitly forbidden in product chrome

| Pattern | Source temptation | Why Dhund rejects it |
|---------|-------------------|----------------------|
| Mesh / multi-stop hero gradients in app | Vercel, Together, Stripe | Makes Research OS feel like a marketplace / fintech sky |
| Lavender / purple accent | Linear, legacy SPA, Superhuman violet pills | Chatbot / lifestyle association |
| Sticker / multi-pastel personality | Notion | Undermines scholarly trust |
| Coral / forest full-bleed cards in OS | Airtable | Marketing voltage ≠ workstation |
| Action Blue / Stripe indigo / Cursor orange as brand | Apple, Stripe, Cursor | Wrong category; teal is locked |
| Framer spotlight grid as identity | Framer | Spectacle over instrument |
| AI pastels as global buttons | Cursor misuse | Timeline/pipeline scope only |
| Tesla Electric Blue / Replicate orange / Mintlify mint as brand | Tesla, Replicate, Mintlify | Teal `signal` is locked |
| SpaceX all-caps UI / pure black app | SpaceX | Aerospace cosplay in a research OS |
| Figma pastel sticky sections in product | Figma | Collaboration ≠ moodboard |

### 3.3 Where limited “voltage” is allowed

- **Landing only:** Superhuman-style deep teal closing band; optional single dark hero band; at most one Framer-like atmosphere card — never Stripe/Vercel mesh sky.
- **Evidence grades / confidence:** semantic colors only.
- **Pipeline / AI Execution / Research Progress:** Cursor-style **scoped stage chips** using Dhund `sem.*` / AI state tokens — never as page chrome.
- **Ecosystem Icon Cloud:** brand logos keep their own colors; Dhund chrome stays neutral around them.
- **Numerics:** Stripe-style tabular figures for citation counts, quotas, scores, DOI-adjacent tables.

---

## 4. Typography system

### 4.1 Families

| Role | Choice | Borrowed spirit |
|------|--------|-----------------|
| UI / marketing sans | **Plus Jakarta Sans** (already shipping) | Vercel Geist restraint + Linear tracking discipline — without licensing Geist/Linear Display |
| Reading / paper body | Same sans at body sizes, or optional serif later for long extracts | Notion reading rhythm (line-height ~1.5, calm measure) |
| Mono | System mono / existing mono stack | Vercel Geist Mono eyebrows; Together uppercase mono for **technical** labels only |

### 4.2 Scale (product)

Align with DESIGN-SYSTEM denser workstation; marketing may go larger.

| Token | Size | Weight | Tracking | Use |
|-------|------|--------|----------|-----|
| `display` | 28–40px (app) / 48–64px (landing) | 400–600 (Stripe/Cursor thin–magazine on landing; avoid heavy 700 on heroes) | −0.02 ~ −0.04em (Framer extremes landing-only) | Landing H1, rare in-app |
| `title` | 16–20px | 600 | −0.01em | Panel titles, page H1 in app |
| `body` | 14px | 400 | 0 | Default UI |
| `ui` | 13px | 500 | 0 | Controls, tabs |
| `meta` | 12px | 400–500 | 0 | Captions, timestamps |
| `micro` | 11px | 500 | +0.04em uppercase optional | Mono-style eyebrows (Together/Vercel) for Router, pipeline, DOI |

**Writing / Paper:** prefer 15–16px body, line-height 1.5–1.6, max-width ~65ch (Notion).  
**Evidence / Library:** 13–14px dense rows (Linear).

---

## 5. Spacing & layout

### 5.1 Spacing scale (4-based, Linear/Vercel)

`4 · 8 · 12 · 16 · 24 · 32 · 48`  
Section marketing: `80–128` (Apple/Vercel section air).  
App shell: prefer `8–16` gaps; kill empty “dashboard air” (DESIGN-SYSTEM-v2 audit).

### 5.2 Grid

- **App:** fluid content column + optional inspector rail (Figma Evidence pattern; Linear density).
- **Landing:** single composition per section; one job per band (existing Dhund rule + Apple museum rhythm).
- **Writing:** content column primary; outline rail secondary (Notion).

### 5.3 Radius

| Token | px | Use |
|-------|-----|-----|
| `xs` | 4–6 | Inputs, dense chips (Vercel app chrome) |
| `sm` | 8 | Buttons in app, small cards |
| `md` | 12 | Panels, dialogs |
| `lg` | 16 | Marketing cards, screenshot frames |
| `pill` | 9999 | Marketing CTAs only (Apple/Vercel) — **not** every chip in the OS |

---

## 6. Elevation & borders

**Default:** hairline border on flat surface (Vercel/Linear) — no multi-layer shadows.  
**Allowed shadow:** one soft elevation for modals / popovers / floating command palette (Apple product-shadow discipline: shadow on the floating object, not on all chrome).  
**Forbidden:** glow, neon rings, glassmorphism stacks.

---

## 7. Motion philosophy

| Pattern | Rule |
|---------|------|
| Pipeline / AI states | Status color + short progress — same language everywhere (Cursor timeline *pattern*) |
| Animated Beam | Only Research OS hero, pipeline progress, AI Execution inspector |
| Icon Cloud | Hover-to-spin only; no play/pause chrome; no center logo |
| Landing CTAs | One primary per band (Superhuman/Stripe); closing teal band |
| Panels | 150–220ms ease-out open/close |
| Hover | Opacity/border shift; no bounce |
| Framer energy | Landing section transitions only — never perpetual loops in app |
| Reduced motion | Freeze decorative motion; keep functional state changes |

**Reject:** Framer-style perpetual hero loops in the app; Stripe mesh as motion backdrop; confetti on “AI done.”

---

## 8. Core components (language)

### Buttons
- **App primary:** `signal` fill, `sm` radius, 13–14px — Linear-sized, not Apple retail pills.
- **Marketing primary:** near-black or teal pill (Airtable/Vercel) — reserved for landing CTAs.
- **Secondary:** hairline border, white/elevated fill.
- **Ghost / tertiary:** text + hover wash.

### Inputs
- Hairline border, `xs`–`sm` radius, quiet focus ring in `signal` (Linear focus discipline).
- Sunken fill (`ink.100`) for code / DOI / mono fields (Vercel code block energy without flash).

### Cards
- Default: **no card**.
- Use when: selectable Library item, pricing tier, marketing feature that is interactive.
- Prefer list rows with hairlines for Evidence / Citations / Search hits.

### Sidebar & navigation
- Calm, narrow, low chroma (Linear).
- Active: soft `signal.100` wash or left hairline — not thick colored bars.
- Account / settings demoted visually from research objects (paper, project, evidence).

### Research canvas / workspaces
| Surface | Feeling target | Primary borrow |
|---------|----------------|----------------|
| **Evidence** | Dense inspector, scannable claims | Linear |
| **Writing** | Long-form calm, cite-as-you-go | Notion |
| **Library** | Rows + status, not tile carnival | Linear + Vercel |
| **Search / Discover** | Technical clarity, provider honesty | Vercel |
| **Dashboard** | Next action, not widget soup | Linear + Airtable editorial clarity |
| **Landing** | Section-owned brands (see §8b); product museum + teal close | Tesla · Apple · Linear · SpaceX · Replicate · … |
| **Docs / API / ADR** | Sidebar · prose · TOC | Mintlify |
| **Trust Layer** | Austere proof (security → compliance → privacy → reproducibility → audit) | SpaceX (layer only) |
| **Evidence inspector** | Canvas + side inspector | Figma pattern + Linear density |
| **AI / API explainers** | Dark code-story wells | Replicate pattern + Dhund teal |

### 8b. Landing section ownership (frozen formula)

Do **not** paint the whole landing as one brand. Assign each band; keep Dhund tokens (signal teal, cool paper, Newsreader + Plus Jakarta).

| Landing section | Primary | Secondary | Mix |
| --------------- | ------- | --------- | --- |
| Hero | Tesla | Apple | 70 / 30 |
| Product story | Apple | Vercel | 80 / 20 |
| Research pipeline | Linear | Together AI | 80 / 20 |
| Ecosystem | SpaceX | Together AI | 60 / 40 |
| AI Capability Router | Replicate | Together AI | dark code-story |
| Research OS showcase | Linear | Figma | 60 / 40 |
| Evidence inspector | Figma | Linear | canvas + rail |
| Writing | Notion | Apple | 80 / 20 |
| API / Docs tease | Mintlify | Replicate | 80 / 20 |
| Enterprise / Trust | SpaceX | IBM austerity | 70 / 30 |
| Pricing | Stripe | Apple | 70 / 30 |
| FAQ | Mintlify | Notion | dense accordion |
| Finale CTA | Superhuman | — | deep `signal-900` |
| Footer | Vercel | Apple | 70 / 30 |

**Motion (landing only):** hero fade · pipeline beam · ecosystem connections · AI router cascade · product-frame enter-viewport. Forbidden: floating icons, constant rotations, neon particles, infinite background loops.

**Implementation:** `templates/login.html` + `static/landing-v2.css` + `static/landing.js`.

---

## 9. Surface mapping — answered questions

### Why should Evidence feel like Linear instead of Notion?
Evidence is an **inspection surface**: claims, spans, confidence, conflicts. Linear’s density and hairlines support scan + decide. Notion’s block playground would bury verification under soft whitespace.

### Why should Writing borrow Notion’s reading rhythm but not its UI?
Researchers need **measure, quiet chrome, side notes**. They do not need sticker personality or infinite block toys. Cite chips and evidence bindings stay Dhund/Linear-tight inside a Notion-calm page.

### Why should landing use Apple instead of Framer (updated Phase 2)?
Apple’s **chrome recedes** still wins for Research OS marketing. Framer contributes **poster tracking** and optional **one** atmosphere card — not dark-as-identity or spotlight grids. Superhuman contributes the **closing teal CTA band** and single-CTA discipline.

### Where should Stripe-like gradients be used — and avoided? (updated)
**Avoid everywhere as brand sky.** Stripe mesh is non-negotiable *for Stripe*; for Dhund it would erase teal instrument identity. Soft blue-tinted **shadows** on floating panels are the only Stripe depth borrow.

### Cursor timeline vs Dhund pipeline
Same *scoping rule*: stage colors live inside the progress/execution strip. Dhund keeps its own `sem.*` / AI state tokens — we borrow the discipline, not the peach/mint/lavender set or orange CTAs.

### Which animations reinforce seriousness vs gimmick?
Serious: pipeline state, beam that explains Import → Dhund → Evidence, hover Icon Cloud, stream cursor, Superhuman single-CTA bands.  
Gimmick: auto-spinning logos, confetti, glow on “AI done,” rainbow beams, Stripe mesh sky, Framer spotlight grids.

---

## 10. Design tokens (v1 summary)

```text
accent:        #0F6E6A  (signal.600)
accent-hover:  #14807B
accent-soft:   #D8F0EE
canvas:        #F7F8FA
surface:       #FFFFFF
ink:           #161B22
ink-muted:     #6B7685
hairline:      #E2E7EE
radius-app:    6–8px controls, 12px panels
radius-mkt:    pill CTAs only
space:         4/8/12/16/24/32/48
type-ui:       Plus Jakarta Sans
type-mono:     ui-monospace (eyebrows, DOI, router)
shadow:        modal/popover only (optional Stripe-blue tint)
numerics:      tabular figures for counts/scores/quotas
```

Dark mode: invert the ink ladder; keep `signal` hue; never make dark the brand story (Linear/Framer marketing dark is optional band, not identity).

---

## 11. Relationship to existing docs

| Doc | Role after this |
|-----|-----------------|
| `DESIGN-SYSTEM.md` | Remains token + component law for shipping; Phase 1–2 **reinforce** teal/light/instrument |
| `docs/DESIGN-SYSTEM-v2.md` | Workstation UX hierarchy still pending approval; this Language supplies the **visual DNA** for that UX |
| This file | Synthesis + philosophy + borrow/leave matrix from Phase 1–2 inspirations |

---

## 12. Acceptance checklist

### Phase 1
- [ ] Approve teal-as-only-brand-voltage (no lavender/blue/orange/indigo takeover)
- [ ] Approve light-first app shell (dark only as preference / landing band)
- [ ] Approve Evidence=Linear density vs Writing=Notion calm split
- [ ] Approve marketing subtraction (Apple/Vercel) vs app density (Linear)
- [ ] Approve forbidden list (mesh gradients, sticker palette, signature coral in OS)

### Phase 2
- [ ] Approve Superhuman three-band landing (esp. deep teal close)
- [ ] Approve one CTA per marketing band
- [ ] Approve Stripe tabular nums + product-mockup proof — **no** mesh sky
- [ ] Approve Framer tracking/atmosphere **landing-only**, max one spotlight card
- [ ] Approve Cursor AI-stage chip pattern mapped to Dhund pipeline tokens

### Phase 3
- [x] Approve Mintlify 3-column docs for contracts/API/ADR (accent stays Dhund teal)
- [x] Approve Figma canvas+inspector for Evidence/Paper (no pastel blocks in OS)
- [x] Approve Tesla subtraction for product heroes; SpaceX austerity for **Trust Layer** only
- [x] Approve Replicate dark code-story wells for AI/API explainers (no orange/cream identity)
- [x] Freeze Visual Density, Border, Confidence, and Cognitive Load doctrines
- [x] Rename Enterprise band → **Trust Layer**

### Freeze
- [x] **No more inspiration sources** — execute the language

---

## 13. Next — execute (do not expand references)

**One-sentence identity (canonical):**

> Apple's restraint, Linear's precision, Notion's readability, Mintlify's documentation, Figma's inspection model, Tesla's product confidence, and SpaceX's engineering credibility — held together by Dhund's own doctrine of evidence-first, inspectable research.

**Implementation order (after “implement”):**

1. Tokens + landing three-band (Superhuman close) + Icon Cloud
2. Evidence inspector rail (Figma pattern) + Confidence Doctrine UI
3. Docs/API layout (Mintlify 3-col)
4. Pipeline stage chips (Cursor pattern)
5. Trust Layer (SpaceX austerity — security/compliance/privacy/reproducibility/audit)
