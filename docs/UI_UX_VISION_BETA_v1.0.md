# UI_UX_VISION_BETA_v1.0

**Date:** 2026-07-29  
**Status:** Frozen  
**Scope:** Dhund Beta UI/UX — Evidence-backed Literature Review path only  
**Aligned with:** [`BETA_EXECUTION_PLAN_v0.2.1.md`](./BETA_EXECUTION_PLAN_v0.2.1.md) · [`PLATFORM_FREEZE_v1.0.md`](../Dhund-Flow/PLATFORM_FREEZE_v1.0.md) · [`SECURITY_BASELINE_v1.0.md`](./SECURITY_BASELINE_v1.0.md)

---

## Product identity

> **Dhund is a Research Operating System, not an AI chat application.**

Wrong first impression:

> “This looks like another ChatGPT-style writing tool.”

Desired first impression:

> “This is a professional workspace for conducting evidence-backed research.”

Every UI decision must reinforce that identity.

---

## UI Principles

Every screen must satisfy these filters. Use them to reject scope and decoration.

1. **Evidence before AI.**  
2. **Workflow before tools.**  
3. **Progress before waiting.**  
4. **Verification before export.**  
5. **Calm, professional, academic.**  

Examples:

| Question | Principle | Answer |
|----------|-----------|--------|
| Promote Chat in the sidebar? | 2 | No |
| Add bouncing / glowing AI animation? | 5 | No |
| Show Generate before Accept evidence? | 1 | No — guide to evidence first |
| Export without Verify affordance? | 4 | No |
| Static “Loading…” spinner only? | 3 | No — show research stage |

---

## Signature interaction

Every great product has one interaction people remember.

**Dhund’s signature:**

> **Click any citation marker → instantly inspect the supporting evidence without leaving the manuscript.**

```text
Previous studies suggest…

[#12]   ← click
```

Inspector (Evidence rail — stays on the Writing desk):

```text
Evidence #12
Paper / authors / year (when known)
Quote
Page
Confidence
Open paper
```

This is the interaction that sells trust. Verify / Accept / Revise build on it; they do not replace it.

---

## Design principles (product structure)

### 1. Workflow over pages

Researchers think in workflows, not feature menus.

```text
Import Research → Evidence → Writing → Review → Verify → Export
```

The app should feel like **one workspace**, not isolated tools.

### 2. Research, not chat

Never present Dhund as a conversational black box. Expose operations researchers recognise (see **UI language glossary**).

---

## Colour philosophy

Colour communicates **research status**, never decoration.

| Colour | Meaning |
|--------|---------|
| **White** | Manuscript (the paper) |
| **Grey** | Workspace chrome / rails |
| **Teal** (`#0f6e6a`) | Evidence and trust (primary accent) |
| **Green** | Verified / accepted / ready |
| **Amber** | Review needed / contested / weak evidence |
| **Red** | Unsupported claim / blocker / fail |

Do not introduce purple AI aesthetics, neon glow, or decorative gradients as brand.

Typography: **Creato Display** for UI; manuscript body uses academic spacing and research headings (see Writing desk).

Brand mark: Dhund wordmark + simple evidence glyph (not a bare “S” tile). Identity must hold if nav labels are ignored.

---

## Motion philosophy

> Motion communicates progress. Never decorate.

Every animation must explain:

- what just happened, or  
- what is happening, or  
- what happens next  

| Allowed | Forbidden |
|---------|-----------|
| Stage complete → check → next stage | Bouncing AI icons |
| Citation link pulse once | Glowing buttons |
| Soft fade of Research Confidence update | Particle effects |
| Calm Linear/Notion-like transitions | Flashy generative spectacle |

Sequential loading (one stage visible at a time):

```text
Fade in → soft pulse while active → completion check
  → slide upward → next stage appears
```

Example grounded-generate sequence:

1. Planning literature review…  
2. Organising evidence…  
3. Writing literature review…  
4. Linking citations…  
5. Verifying evidence…  
6. Literature Review Ready  

---

## UI language glossary

**Never say:** Thinking… · Processing… · Generating… · Loading…  

**Say instead (research operations):**

| Prefer | Context |
|--------|---------|
| Planning review | Planner stage |
| Organising evidence | Context / RI assembly |
| Writing literature review | Section synthesis |
| Linking citations | Binder |
| Verifying evidence | Research Reviewer / Verify |
| Preparing export | Export path |
| Extracting evidence | Extract pipeline |
| Accepting evidence | Inspector accept |

---

## Information architecture (beta)

```text
Home
Projects
Library
Research
Writing
──────────────
Integrations
Settings
```

- **Integrations:** visible Zotero / Mendeley connection status (and import pathways). Familiar tools build trust.  
- **Ask Dhund / Chat:** reachable but never primary (workflow before tools).  
- Legal / marketing copy must not say “ChatGPT-style.”

---

## Library

Empty Library must answer: *How do I get my research into Dhund?*

```text
Start your research
  Upload PDF
  Import from Zotero
  Import from Mendeley
  Import DOI
  Import PMID
  Browse recent projects
```

Never ship a bare “No papers.”

---

## Writing workspace (flagship)

Three columns:

```text
Outline          Editor (manuscript)          Evidence
```

Supporting modes (tabs or drawers — not competing columns): Reviewer · Export · Verification focus.

### Manuscript centre

The centre is **not** a web textbox aesthetic.

| Side rails | Centre |
|------------|--------|
| Software (chrome, inspectors) | **Paper** |
| Grey workspace | White page, margins |
| Tools | Research headings, academic spacing, `[#id]` markers |

The researcher should feel they are reading and editing a manuscript while the OS assists from the rails.

### Workflow the desk narrates

```text
Outline → Select section → Review evidence → Write Lit Review
  → Verify → Accept → Export
```

Every generated paragraph remains visibly connected to EvidenceObjects (signature interaction + Verify).

### Research Confidence (header strip)

Near the top of Writing — **not** an AI confidence score:

```text
Research Confidence
  Evidence coverage    __%
  Research Reviewer    Pass | Fail
  Unsupported claims   N
```

Only show metrics that help a decision *now*. During generation, live counts (e.g. Evidence Objects organised) are useful. After generation, hide vanity metrics (e.g. “Themes identified”) unless they drive Accept / Revise / Export.

**Filter for every metric:** *What decision does this help the researcher make?* If none — hide it.

---

## AI transparency

AI is never a black box. Generated content always exposes:

```text
Evidence → Research Reviewer → Research Confidence → Accept / Revise
```

Trust comes from transparency, not hidden intelligence.

---

## Empty states & progressive loading

Every empty surface guides the next workflow action (not “No items”).

Pages become usable immediately: Project and manuscript first; Evidence / Reviewer rails may continue loading with research-stage copy — never a full-page “Loading…”.

---

## Branding cues (always visible where relevant)

Papers · EvidenceObjects · Citations · Authors · Years · Journals · Reviewer status  

Avoid generic SaaS dashboards and chat-first layouts.

---

## Beta UI priorities (execution order)

No new workflows. No new AI capabilities. No architecture rewrites. Visual/UX on the existing Lit Review path only.

1. Redesign Writing Workspace (Outline | Manuscript | Evidence) + Research Confidence.  
2. Research-stage sequential loading (Generate / Extract).  
3. Surface Zotero / Mendeley in Library + Integrations.  
4. Workflow-driven empty states.  
5. Sidebar IA + brand mark + glossary copy pass (kill Thinking / ChatGPT-style).  
6. Progressive loading polish (usable rails before background work finishes).  

---

## Explicit non-goals (beta UI)

- Promoting Chat as a primary product surface  
- Fake Knowledge Graph chrome  
- Purple / dark “AI aesthetic” restyle  
- New product workflows beyond Import → Evidence → Lit Review → Verify → Export  

---

## Product Promise

Every major interaction in Dhund should answer four questions for the researcher:

1. **Where am I in the workflow?**  
2. **What is Dhund doing right now?**  
3. **Why should I trust this result?**  
4. **What should I do next?**  

If any screen fails to answer one of these, the design is incomplete.

---

## Success test

A first-time researcher opens Dhund and thinks:

> “This feels like software built specifically for research.”

—not—

> “This feels like another AI writing app.”

---

## Change control

Amend only for demonstrated beta friction or a failed Product Promise check. Prefer fixing the Lit Review desk over expanding surfaces.
