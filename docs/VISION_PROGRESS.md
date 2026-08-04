# VISION_PROGRESS — Dhund Research OS

**Companion to:** Permanent Vision 1.0 (*Building the World's Research Operating System*)  
**Also:** [`docs/audit/05-RESEARCH-OS-VISION.md`](./audit/05-RESEARCH-OS-VISION.md) · [`docs/audit/11-VERSION1-COMPLETION-TRACKER.md`](./audit/11-VERSION1-COMPLETION-TRACKER.md)  
**Last updated:** 2026-08-03  
**Rule:** Update after major milestones. Progress is against the **vision**, not only the feature list.

---

## Snapshot

| Lens | Status |
|------|--------|
| **V1 engineering scoreboard** (#1–20) | **100% 🟢** — personal closed-beta OS core Production Ready (**archived** → [11](./audit/11-VERSION1-COMPLETION-TRACKER.md)) |
| **Phase 2 scoreboard** (#21–28) | **2A 🟢 / 2B 🟢** — [12](./audit/12-PHASE2-COMPLETION-TRACKER.md); #21–28 Production Ready |
| **Permanent Vision (5 pillars, avg)** | **~56%** — Research OS far from finished |
| **Freeze** | Graph/Agents/Memory/Enterprise frozen until [Primary Workspace Review](./audit/16-COMPETITIVE-REPLACEMENT-REVIEW.md) |
| **Sequencing** | After #28 → Product Readiness Review ([16](./audit/16-COMPETITIVE-REPLACEMENT-REVIEW.md)), **not** auto Phase 3 · Doctrine: reduce context switching |
| **Motto fit today** | Papers → evidence → (partial) insight → publishable **MD/Bib** trail works for lit-review |

```text
Knowledge Acquisition     █████████░  ~90%
Research Intelligence     ██████░░░░  ~58%
Writing Intelligence      ███████░░░  ~74%
Research Workspace        █████░░░░░  ~48%
Publication Intelligence  ██░░░░░░░░  ~22%
```

---

## Pillar detail

### 1 — Knowledge Acquisition (~90%)

**Goal:** Collect every piece of knowledge a researcher needs → clean library. Sources are entrances into one pipeline, not silos.

| Capability | Status |
|------------|--------|
| PDF / document import | ✅ |
| DOI / metadata / dedupe | ✅ (strengthen as sources land) |
| Zotero + Mendeley (sync + PDF pull) | ✅ V1 |
| OpenAlex Discover + Crossref | ✅ |
| Semantic Scholar | ✅ related / enrichment |
| PubMed | ✅ #22 — Discover + OA → Analysis |
| Google Drive | ✅ #23 — OAuth + PDF import → Analysis (watch deferred) |
| BibTeX / RIS | ✅ |
| arXiv | 🟢 Phase 2B (#24) |
| Europe PMC | 🟢 Phase 2B (#25) |
| ORCID | 🟢 Phase 2B (#26) |
| Dropbox | 🟢 Phase 2B (#27) |
| OneDrive | 🟢 Phase 2B (#28) |
| Automatic metadata + worker pipeline | ✅ |

**Moves the needle next:** Fill [16 Competitive Replacement Review](./audit/16-COMPETITIVE-REPLACEMENT-REVIEW.md) — primary workspace gate before Graph/Agents.

---

### 2 — Research Intelligence (~58%) — “Dhund’s heart”

| Capability | Status |
|------------|--------|
| Paper analysis (structure, methods, claims…) | ✅ pipeline |
| Evidence Objects (provenance, confidence, spans) | ✅ Platform V1 |
| Consensus / conflict / themes / gaps / matrix / timeline | ✅ RI APIs + Compare UX |
| Knowledge Graph as product | ⚪ / thin RI graph views — flagship P5 |
| Corpus-scale literature questions without LLM invention | Partial — project-scoped, not OS-scale |

**Moves the needle next:** Feed SUE via Phase 2B acquisition; after #28, [16 Competitive Replacement Review](./audit/16-COMPETITIVE-REPLACEMENT-REVIEW.md) may prioritize Workspace before Graph.

---

### 3 — Writing Intelligence (~74%)

| Capability | Status |
|------------|--------|
| Grounded Writer (evidence-linked) | ✅ |
| Citation insert + bibliography path | ✅ |
| Reviewer Engine + persistent checks | ✅ |
| Export with evidence trail (MD/BibTeX) | ✅ |
| Outline Builder (full lit-review / methods / discussion) | Partial |
| Explainability (why / evidence / confidence) | Partial → strong in Inspector |

**Moves the needle next:** richer outlines & section types; keep style-only transforms labeled honestly.

---

### 4 — Research Workspace (~48%)

| Capability | Status |
|------------|--------|
| Personal projects (library, notes, drafts, hub) | ✅ |
| Writing + reviewer history in project | ✅ |
| Project memory promotion | Partial |
| Timelines / experiments / tasks as first-class | Thin |
| Team collaboration on shared evidence | ⚪ out of V1 |
| Research Memory flagship (months later) | Partial → P6 |

**Moves the needle next:** Memory depth for personal OS; collaboration only when Enterprise/P4 intentional.

---

### 5 — Publication Intelligence (~22%)

| Capability | Status |
|------------|--------|
| Grounded export + provenance | ✅ MD/Bib |
| Journal selection / formatting packs | ⚪ |
| Submission readiness / checklists | ⚪ |
| Reviewer-response drafting / revision compare | ⚪ |
| DOCX / journal packs | ⚪ out of V1 |

---

## Vision success criteria (1–10)

| # | Criterion | Today |
|---|-----------|-------|
| 1 | Discover & import multi-source | **Partial** — Bridge + Discover; PubMed/Drive later |
| 2 | Structured searchable library | **Strong** |
| 3 | Papers → evidence / claims / methods | **Strong** (KG product still ahead) |
| 4 | Themes / consensus / gaps at scale | **Partial** |
| 5 | Plan research with methodology support | **Thin** |
| 6 | Draft with claim→evidence traceability | **Strong** |
| 7 | Continuous review + reviewer history | **Strong** |
| 8 | Collaborate via shared evidence/memory | **Not yet** |
| 9 | Publication-ready with provenance | **Partial** (export yes; packs no) |
| 10 | Return months later; project remembers | **Partial** |

**Strong:** 2, 3, 6, 7 (+ parts of 1/4/9/10). **Not OS-complete.**

---

## Research loop

```text
Search ········ Partial
Import ········· Ready
Analyze ········ Ready
Extract Evidence  Ready
Knowledge Graph · Thin (views ≠ flagship)
Research Intel ·· Partial
Write ·········· Ready
Review ········· Ready
Revise ········· Partial (human)
Publish ········ Thin (MD/Bib)
Learn / Memory ·· Partial
```

---

## AI philosophy

**Target:** Question → Evidence → RI → Reasoning → LLM → Reviewer → Answer.

**Today:** Writing Intelligence path largely respects this. Chat is a **tool**, not the product spine — aligned with vision.

---

## What Dhund must not become (still binding)

No generic chatbot skin, prompt marketplace, social network, or disconnected AI tools. V1 completion does **not** license scope sprawl.

---

## How to update this file

1. After a pillar-moving milestone, adjust % and capability rows.  
2. Keep V1 tracker for **engineering Production Ready**; keep **this** file for **vision distance**.  
3. Quarterly (or after freeze lift), refresh the ASCII bars and success table.  
4. Every feature still answers the North Star test in Vision 1.0.

**Canvas twin:** open `Dhund-Vision-Progress.canvas.tsx` beside chat for the interactive view.
