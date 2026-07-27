# Soro vs Jenni — Competitive Roadmap

**Status:** Planning (competitive detail)  
**Date:** 2026-07-26  
**Canonical Phase 2 sequence:** [`phase-2-writing-roadmap.md`](./phase-2-writing-roadmap.md) **(frozen)** — validation gate → shell → evidence → citations → guided AI → reviewer.  
**Companions:** [`UI-Architecture.md`](../UI-Architecture.md) · [`PRODUCT-SPEC.md`](../PRODUCT-SPEC.md)  
**Audience:** Product + engineering

---

## 1. Competitive thesis

| | **Jenni AI** | **Soro** |
|---|---|---|
| Category | Academic **writing** workspace | **Evidence-first** research OS |
| Wedge | Autocomplete + citations in the editor | Paper Workspace (M5–M10) → defensible drafts |
| Promise | Faster to a cited manuscript | Harder for a reviewer to kill your draft |

**Do not** pause the analysis pipeline to clone Jenni’s editor first.  
**Do** turn M5–M9 ViewModels into writing primitives, then match table-stakes writing UX.

**One-line positioning:**  
*The research OS that makes your writing defensible.*

---

## 2. Reuse contract (non-negotiable)

Writing features **consume** existing normalized ViewModels. They must **not** re-parse phase JSON or invent citations.

| Source | Mapper / model | Writing may use |
|--------|----------------|-----------------|
| M5 Structure | `mapStructure` → `DocumentUnderstandingView` | Section outlines, heading targets |
| M6 Classification | `mapClassification` → `ClassificationViewModel` | Document type / design / domain chips |
| M7 Entities | `mapEntities` → `EntitiesViewModel` / `EntityItemView.key` | Claim subjects, PICO slots |
| M8 Evidence | `mapEvidence` → `EvidenceViewModel` (`framework:*`, `outcome:*`) | Claim strength, grade badges |
| M9 Graph | `mapKnowledgeGraph` → stable `sourceEntityId` / `graphNodeRefId` | Related-concept scaffolding |
| M10 Chat | `WorkspaceReference` + `mapExplainableChat` | “Insert into draft” from chat refs |

Shared link type for writing ↔ workspace:

```ts
// Reuse M10 — do not invent a parallel citation type
WorkspaceReference {
  id, kind, refId, label?, tab, href?, metadata?
}
```

Every AI-written claim block must carry `references: WorkspaceReference[]` (may be empty only when the user explicitly chose “ungrounded”).

---

## 3. Milestone map (extends UI-Architecture §10)

Keep **M11–M12** as hardening. Competitive track starts at **M13**.

| ID | Phase | Milestone | Jenni pressure | Depends on | Exit criteria |
|----|-------|-----------|----------------|------------|---------------|
| **M11** | Hardening | Session + errors | Trust | Security PR4 | Expired session modal; ErrorBoundary |
| **M12** | Hardening | Polish / a11y | Parity basics | M0+ | UI-State audit closed |
| **M13** | **A — Wedge** | Compare & gaps → writing seed | Multi-paper synthesis | M8, M10 | Select 2–5 papers → compare/gaps UI → **Export outline** (markdown) with `WorkspaceReference[]` |
| **M14** | **A — Wedge** | Evidence-linked claims | Claim Confidence (deeper) | M7–M10 | “Insert claim” from Evidence/Entities/Chat → `ClaimBlockViewModel` with grade + refs; no invented refs |
| **M15** | **B — Draft** | Writing Studio MVP | Document home | M13–M14 | `/writing` (+ paper/project scoped); compose from claim blocks + outlines; save/export `.md` |
| **M16** | **C — Cite** | Citations CSL + Zotero | Citation styles / library sync | M15, existing Citations | CSL styles (APA/MLA/Chicago/Vancouver min); BibTeX + Zotero import; cite from paper library |
| **M17** | **D — Habit** | Grounded autocomplete | Autocomplete | M15–M16 | Inline suggestions **only** from selected library evidence; each suggestion has refs |
| **M18** | **D — Habit** | Manuscript review | Peer review / Claim Confidence | M8, M15–M16 | Review pass: unsupported / overstated / low-grade claims flagged vs Evidence VMs |
| **M19** | Stretch | Collab + rich export | Real-time collab, docx/LaTeX | M15–M16 | Optional: `.docx` / LaTeX export; collab only if SaaS-ready |

### Sequencing

```
M5–M10 (Paper Workspace + Explainable Chat) ──┐
M11 → M12 (hardening)                          ├── M13 → M14 → M15 → M16 → M17 → M18
Compare API (existing) ────────────────────────┘                         └── M19 (stretch)
```

---

## 4. Milestone specs

### M13 — Compare & gaps → writing seed

**Goal:** Multi-paper synthesis that Jenni’s single-doc chat can’t match.

**UI**
- Polish `/research/compare` (or current compare routes) with Ready-only papers
- Actions: **Copy outline** · **Send to Writing** (creates draft stub)

**ViewModels (new, thin)**
```ts
CompareOutlineViewModel {
  id
  paperIds: number[]
  sections: { title: string; bullets: string[]; references: WorkspaceReference[] }[]
  gaps: { text: string; references: WorkspaceReference[] }[]
  warnings: string[]
}
```

**Rules**
- Mapper `mapCompareOutline()` over existing compare/gaps API payloads only
- Bullets link to paper Evidence/Entities via `WorkspaceReference` when IDs exist
- No new backend endpoints unless compare payload already insufficient (prefer reuse)

**Acceptance**
- [ ] Outline export contains only grounded bullets or explicit “insufficient evidence” warnings  
- [ ] Clicking a ref opens `?tab=&ref=` on the source paper  
- [ ] TypeScript / tests / lint pass  

---

### M14 — Evidence-linked claims

**Goal:** Atomic writing unit that beats “cite anything” autocomplete.

**UI**
- On Evidence / Entities / Chat rails: **Insert claim**
- Claim preview: text + confidence/grade + reference chips

**ViewModels**
```ts
ClaimBlockViewModel {
  id
  text            // user-editable
  stance?: "supports" | "refutes" | "neutral" | "gap"
  confidence?: number   // from backend / evidence only — never invent
  grade?: string        // e.g. framework display grade
  references: WorkspaceReference[]
  source: "evidence" | "entity" | "chat" | "compare" | "user"
  warnings: string[]
}
```

**Mapper:** `mapClaimBlock()` — thin; accepts user text + existing refs; does not call `mapEvidence()` internally beyond reading a passed-in VM.

**Acceptance**
- [ ] Claim without refs shows persistent warning  
- [ ] Grade/confidence only when present on source VM  
- [ ] Chat “insert” reuses `WorkspaceReference`, does not invent kinds  

---

### M15 — Writing Studio MVP

**Goal:** A home for drafts that is not a fake Google Docs clone.

**Route:** `/writing` · `/writing/:draftId` · deep link `?from=compare&…` / paper-scoped

**UI**
- List drafts · editor (markdown-first is OK) · claim blocks as first-class nodes  
- Side rail: library papers / claim picker / workspace refs (reuse M10 chips)

**Persistence**
- Prefer existing notes/projects storage if it fits; else minimal `writing_drafts` table (only if required)  
- Avoid parallel prompt stacks — use PromptBuilder when generating section text

**Acceptance**
- [ ] User can build a Related Work / Summary section from M13–M14 artifacts  
- [ ] Export `.md` with footnote or link-style refs preserving `refId`s  
- [ ] Empty / loading / error via M3 patterns  

---

### M16 — Citations CSL + Zotero

**Goal:** Remove the #1 switcher objection vs Jenni.

**Scope**
- CSL styles: APA, MLA, Chicago, Vancouver (extend later)  
- BibTeX import/export (strengthen existing Citations)  
- Zotero import (RDF/BibTeX file first; API sync later)  
- “Cite in draft” inserts formatted citation + links `WorkspaceReference` to library paper when mapped

**Non-goals**
- Full Mendeley live sync (file import OK)  
- 10,000 styles on day one  

**Acceptance**
- [ ] Format switch updates bibliography in Writing Studio  
- [ ] Paper from Library can be cited without re-upload  
- [ ] No invented DOI/metadata — missing fields warn  

---

### M17 — Grounded autocomplete

**Goal:** Match Jenni’s habit loop without matching their ungrounded fluency.

**Behavior**
- Suggest next sentence **only** when a paper/project evidence context is selected  
- Each suggestion includes `references: WorkspaceReference[]`  
- User setting: `library_only` (default) vs `allow_ungrounded` (off by default, warning on)

**Acceptance**
- [ ] With empty library context → no autocomplete (or explicit disabled state)  
- [ ] Accepting a suggestion inserts claim block or annotated span with refs  
- [ ] Streaming UX does not invent confidence %  

---

### M18 — Manuscript review (vs Evidence)

**Goal:** Out-depth Jenni Claim Confidence using your grades.

**Checks (deterministic first, LLM second)**
1. Claim has zero refs → **unsupported**  
2. Claim refs an outcome/framework with low grade / high RoB → **weak evidence**  
3. Contradictory stances across claim blocks on same entity → **conflict**  
4. Optional LLM: overstatement language vs cited abstract/section  

**ViewModel**
```ts
ManuscriptReviewViewModel {
  findings: {
    id
    severity: "error" | "warning" | "info"
    message: string
    claimId?: string
    references: WorkspaceReference[]
  }[]
  summary: { unsupported: number; weak: number; conflicts: number }
}
```

**Acceptance**
- [ ] Findings deep-link to claim + Evidence tab  
- [ ] No finding invents a grade not present on Evidence VM  

---

### M19 — Stretch (only after M16)

- `.docx` / LaTeX export  
- Real-time collab  
- Live Zotero API sync  
- Public academic search index (compete with Jenni’s 200M) — **last**; private library remains default

---

## 5. Explicit non-goals (until M16+)

| Non-goal | Why |
|----------|-----|
| Generic ChatGPT essay mode | Undercuts defensibility brand |
| Invented chat citations | Violates M10 contract |
| Full Notion-like editor before claims | Wrong wedge order |
| Clone Jenni peer-review theater without grades | Shallow parity |
| Pause M11–M12 hardening | Trust regressions kill conversion |

---

## 6. Success metrics (product)

| Metric | Target after M15 | Target after M18 |
|--------|------------------|------------------|
| Time-to-first grounded outline (3 papers) | &lt; 10 min | &lt; 5 min |
| % exported bullets with ≥1 `WorkspaceReference` | ≥ 70% | ≥ 85% |
| Drafts that open Evidence/Entities from editor | Measurable CTR | Rising |
| Switcher survey: “more defensible than Jenni” | Soft signal | Primary win theme |

Vanity to ignore early: raw word count generated, autocomplete accept rate without refs.

---

## 7. Engineering principles

1. **Thin mappers only** — `mapCompareOutline`, `mapClaimBlock`, `mapManuscriptReview`; never fork `mapEvidence` / `mapEntities`.  
2. **Chat orchestrates, Writing renders** — same as M10 vs tabs.  
3. **Stable IDs** — entity keys, `framework:grade`, `outcome:*`, `source:type:id` for graph.  
4. **Warnings always visible** — low evidence, skipped phases, ungrounded mode.  
5. **No new backends** until a milestone’s exit criteria prove existing APIs insufficient.

---

## 8. Immediate next build (recommended)

After M11–M12 (or in parallel if staffed):

1. **M13** — Compare → outline with `WorkspaceReference[]`  
2. **M14** — Insert claim from Evidence + Chat rail  
3. **M15** — `/writing` studio MVP  

That triad is enough to **demo** “Soro vs Jenni” without an autocomplete clone.

---

*End of Soro vs Jenni competitive roadmap.*
