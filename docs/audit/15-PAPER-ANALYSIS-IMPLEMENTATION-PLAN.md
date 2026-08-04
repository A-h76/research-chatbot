# 15 — Scientific Understanding Engine — Implementation Plan

**Document:** `15-PAPER-ANALYSIS-IMPLEMENTATION-PLAN.md`  
**UI:** Paper Analysis 2.0 · **Engine:** Scientific Understanding Engine  
**Revision:** **v3 locked** (reality-checked) — 2026-08-03  
**Status:** **2.7 / #21 Production Ready** · next **#22 PubMed**  
**Tracker:** [12](12-PHASE2-COMPLETION-TRACKER.md) (locked)

---

## North Star

Every imported paper → structured scientific object → writing-ready intelligence.

## Feature gate (every change)

1. Real researcher problem?  
2. Extend existing architecture (not rewrite)?  
3. Improves Import → Analysis → Evidence → Writing → Review → Export without leaking into KG / Memory / Agents / Publication Intelligence?

**One-paper test:** richer **one paper** → in scope. Cross-corpus / over-time reasoning → defer.

---

## 0. Principles

1. One milestone → Production Ready before next.  
2. Extend `phase1_analysis` / `paper_analysis` / `phase_projector` / paper FE only.  
3. EvidenceObjects = Writing/Reviewer bridge.  
4. Prefer author-stated + locators; **never invent** stats significance or quality theater.  
5. Cost note each milestone: tokens · latency · artifact reuse.

---

## 1. Locked milestones (2.1–2.7)

| MS | Name | Scope (reality) |
|----|------|-----------------|
| **2.1** | Scientific Structure | Sections + objectives / RQ / hypotheses / problem statement **when reliably extractable**; Overview bridge from structured data |
| **2.2** | Methodology Intelligence | Consistently extractable methods fields (design, population, N, variables, dataset, metrics, setup, …); optional light author-stated code/data availability — **not** full repro product |
| **2.3** | Statistical Intelligence | Explicit tests / p / CI / effects only; interpretation only if author-stated; no fabricated “significant” |
| **2.4** | Evidence Intelligence | Richer grounded projector; auto `evidence_extract` happy path; additive facets (method/quote/confidence/limitations) |
| **2.5** | Limitations & Novelty | Author-stated first; no AI hype judgments |
| **2.6** | Scientific Entities | Paper-scoped entities + local edges; **not** global graph |
| **2.7** | Quality Assessment | **Inspectable checklist** (methodology / evidence / limitations / availability signals) — **not** opaque `8.9/10` |

```text
2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6 → 2.7 → #21 🟢 → PubMed
```

### Explicitly deferred (not milestones under #21 now)

| Item | When |
|------|------|
| Figure & Table intelligence (vision/OCR/tables) | Later — significant project |
| Full reproducibility assessment | Later — needs richer extraction |
| Cross-paper intelligence | Later in Phase 2 — after single-paper mature |
| Full citation network | Not now — KG-adjacent |

---

## 2. Milestone notes

### 2.1 Scientific Structure ✅
Strengthen Phase 1.1 via additive `scientific_structure` on serialize; FE Structure + Overview. Reuse import/Phase text — no extra LLM.

**Shipped:** `backend/document_understanding/scientific_structure.py` · Structure “Scientific framing” · Overview framing cards.

### 2.2 Methodology
Generalize beyond medical-only depth; FE Methodology section. Consistent fields > exhaustive wishlist.

**Shipped:** `backend/document_understanding/methodology_profile.py` · Structure “Methodology” · Overview methodology hint · classification/PICO enrich when present.

### 2.3 Statistics
Extract what is written. Interpretation field only with `author_stated` (or omit).

**Shipped:** `backend/document_understanding/statistics_profile.py` · Structure “Statistical findings” · Overview hint · medical measures enrich when present.

### 2.4 Evidence
Projector enrichment + enqueue `evidence_extract` when research_ready + project. Caps for noise. No new job family.

**Shipped:** `phase_projector.v1.2` facets · `MAX_CANDIDATES_PER_FILE=30` · `maybe_enqueue_evidence_extract` after phase1 · Overview auto-run copy.

### 2.5 Limitations & Novelty
Author-stated lists/profiles; invent-nothing tests.

**Shipped:** `backend/document_understanding/limitations_novelty_profile.py` · Structure “Limitations & novelty” · Overview hint · projector EO limitations enrich.

### 2.6 Entities
Non-medical entities; paper Graph stays file-scoped JSON.

**Shipped:** `scientific_entities_profile` · Entities tab scientific + local relations · Overview chips · no Neo4j.

### 2.7 Quality (inspectable)

**Ship this shape:**

```text
Methodology: Strong
✓ Randomized controlled trial

Evidence:
✓ Large sample
✓ Statistical analysis reported

Limitations:
• Single-center study
• Short follow-up

Availability:
• Code unavailable
• Dataset unavailable
```

**Do not ship:** `Quality Score: 8.9/10` without explainable checklist underneath.

Deterministic aggregator over stored profiles preferred (near-zero tokens). PDF deep-link if locators exist (nice-to-have in 2.7, not a rewrite).

**Shipped:** `quality_assessment_profile` · Structure “Quality assessment” · Overview hint · reasons on every item · no opaque score.

---

## 3. Production Ready (per milestone)

```text
✓ Backend · Frontend · Workers additive only · Tests · Docs
✓ Feature gate + one-paper test passed
✓ Evidence compatibility · Cost note · No pillar leak
```

---

## 4. Next action

**#21 done (2.1–2.7).** Next: **#22 PubMed** (acquisition).  
**Do not expand this plan** unless a deferred item is explicitly promoted.

---

## 5. Change log

| Date | Note |
|------|------|
| 2026-08-03 | v1: 2.1–2.7 |
| 2026-08-03 | v2: Figures/Cross-Paper/reorder (superseded) |
| 2026-08-03 | **v3 locked:** restore 2.1–2.7; feature gate; defer Figures/Repro/Cross-Paper; inspectable quality |
| 2026-08-03 | **2.1 shipped** (scientific_structure + FE framing) |
| 2026-08-03 | **2.2 shipped** (methodology_profile + FE) |
| 2026-08-03 | **2.3 shipped** (statistics_profile + FE; author_stated interpretations only) |
| 2026-08-03 | **2.4 shipped** (projector v1.2 + auto evidence_extract + caps) |
| 2026-08-03 | **2.5 shipped** (limitations_novelty_profile + FE; author_stated only) |
| 2026-08-03 | **2.6 shipped** (scientific_entities_profile + Entities tab bridge) |
| 2026-08-03 | **2.7 shipped** (inspectable quality checklist); **#21 🟢** |
