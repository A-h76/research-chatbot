# Phase 2 Completion Tracker

**Document:** `12-PHASE2-COMPLETION-TRACKER.md`  
**Role:** Layer 4 — **Phase 2 execution tracking** (not strategy)  
**Created:** 2026-08-03  
**Last updated:** 2026-08-03 (**locked** reality-checked scope)  
**Predecessor:** [11-VERSION1-COMPLETION-TRACKER.md](11-VERSION1-COMPLETION-TRACKER.md) — V1 archived (#1–20 🟢)

---

## Phase 2 North Star

```text
Every imported paper should become a structured scientific object,
not merely a PDF with metadata.

Paper → Scientific Structure
      → Methodology
      → Statistics
      → Evidence
      → Scientific Entities
      → Relationships (paper-scoped)
      → Quality (inspectable)
      → Writing-ready Intelligence
```

**Mission:** Deep scientific understanding first, then research acquisition.

**Naming:** UI = **Paper Analysis** · Engine = **Scientific Understanding Engine** (extends existing pipeline).

**Pipeline:** Sources → Import → Library → SUE → Evidence → Writing Intelligence → Reviewer → Export  
No source is special after bytes are accepted (see **Golden Rule of Acquisition**).

### Phase 2 state (accurate framing)

```text
✅ V1 Complete          — Import → Evidence → Writing → Reviewer → Citations → Export (trust)
✅ Phase 2A Complete    — #21 Paper Analysis 2.0 / SUE (paper intelligence)
▶  Phase 2B Complete    — #22–28 Knowledge Acquisition 🟢
```

**Not** “Phase 2 finished.” Phase 2B still owns PubMed → Drive → arXiv → Europe PMC → ORCID → Dropbox → OneDrive.

Differentiator: not “another provider,” but **every imported paper automatically becomes structured research**.

---

## Golden Rule of Acquisition (binding — every source, forever)

> **Every document entering Dhund—regardless of source—must become the same canonical Paper object and traverse the same Research Intelligence pipeline. Acquisition providers may differ only in authentication, metadata retrieval, and document acquisition. From the moment document bytes are accepted into the import pipeline, every downstream stage (analysis, evidence extraction, writing, review, export, and future capabilities) must be provider-agnostic.**

**Production Ready test (per provider):** a paper discovered from that provider can reach Writing Intelligence through the exact same pipeline as every other source.

```text
No provider-specific analysis.
No provider-specific evidence extraction.
No provider-specific writer.
No shortcuts.
```

Forbidden shortcuts (how debt accumulates):

* “Skip SUE for Provider X”
* “Europe PMC has its own extractor”
* “Drive imports bypass Evidence”
* “PubMed has a special writer”

### Canonical Research OS path (providers are not special)

```text
Upload · OpenAlex · PubMed · arXiv · Google Drive · Zotero · Mendeley
Europe PMC · Dropbox · OneDrive · (future sources…)
        │
        ▼
apply_pdf_bytes_to_stub
        │
enqueue_import
        │
phase1_analysis (SUE)
        │
evidence_extract
        │
Evidence Platform
        │
Writing Intelligence
        │
Research Reviewer
        │
Export
```

Acquisition providers are **entry points** into one Paper object — not parallel products.

### Connector product test (binding — #23–28 and beyond)

A connector is only complete when a researcher can **start there** and **end at Writing Intelligence** (then Review / Export) through the **shared** pipeline — not when OAuth/search “works.”

```text
Start at source → bytes accepted → shared pipeline → Writing Intelligence → Reviewer → Export
```

### Identity & dedupe (monitor as sources grow)

Target as acquisition expands:

```text
Same paper (Upload | Zotero | Mendeley | PubMed | OpenAlex | Drive | …)
      ↓
One Library item · multiple source links
      ↓
One Analysis · one Evidence set
```

Today: DOI / PMID / title-year keys + metadata merge on import. Strengthen canonical resolution as #23–28 land — do not invent per-source paper copies.

---

## Feature gate (binding — every proposal)

```text
1. Does it solve a real researcher problem?
2. Can it extend the existing architecture (not rewrite it)?
3. Does it improve Import → Analysis → Evidence → Writing → Review → Export
   without leaking into KG / Memory / Agents / Publication Intelligence?
4. Does it obey the **Golden Rule of Acquisition** (provider-agnostic after bytes accepted)?
```

If any answer is **no** → defer.

**One-paper test:** If it makes **one paper** richer → #21 (done). If it brings papers into that richer pipeline → #22–28. If it reasons across many papers/projects/time → future pillar.

---

## 0. Engineering rules

Same Production Ready / DoD as V1 ([11 §0.1](11-VERSION1-COMPLETION-TRACKER.md)).  
One milestone → 🟢 before the next. Cost note (tokens / latency / reuse) on each attestation.  
**Golden Rule of Acquisition** above is mandatory for every #22–28 attestation and every future source.

### Still frozen (pillars / productization)

```text
❌ Knowledge Graph Product · Research Memory · Agents
❌ Enterprise / Teams / Billing · DOCX packs · Publication Intelligence
❌ Full citation network product
❌ Figure & Table vision/OCR project (defer)
❌ Cross-paper intelligence productization (defer until single-paper mature)
❌ Heavy reproducibility scoring (defer)
❌ Jumping to “Phase 3” / flagship pillars before Product Readiness Review
```

### Unblocked by #21 🟢

```text
✅ Phase 2B #22–28 Knowledge Acquisition — Golden Rule applies; no analysis bypass
```

### After #28 — Competitive Replacement Review (not Phase 3 / not Graph)

When all seven acquisition rows (#22–28) are 🟢, **do not** immediately build Knowledge Graph, Research Memory, or Agents.

1. Hold a **Product Readiness / Competitive Replacement Review**.
2. Fill [16-COMPETITIVE-REPLACEMENT-REVIEW.md](16-COMPETITIVE-REPLACEMENT-REVIEW.md) — researcher-driven gate, not a feature checklist.
3. Ask:
   * Can a PhD student complete a literature review entirely inside Dhund?
   * Where do they still leave the platform?
   * Is the biggest remaining gap PDF reading, annotation, synthesis, publication, or collaboration?
4. Critical daily workflows (Discover → Export) must be strong; Graph / Memory / Agents may stay ❌ without blocking a compelling product.
5. **Answers determine the next milestone** — shift from engineering-driven sequencing to researcher-driven product development. Prediction: Research Workspace & Publication before flagship pillars. Product Doctrine: improve research quality / velocity / confidence / continuity — not accumulate AI features.

Sequencing so far (preserve):

```text
V1        Trust + writing foundation
Phase 2A  Deep paper understanding (Paper Analysis 2.0)
Phase 2B  Expand acquisition without changing the pipeline
Next      Validate primary-workspace fitness before flagship pillars
```


---

## 1. Scoreboard

| # | Subsystem | Status | Current | Target | Production Ready |
|---|-----------|--------|---------|--------|------------------|
| 21 | Paper Analysis 2.0 (SUE) | 🟢 Production Ready | 100% | 100% | Yes |
| 22 | PubMed | 🟢 Production Ready | 100% | 100% | Yes |
| 23 | Google Drive | 🟢 Production Ready | 100% | 100% | Yes |
| 24 | arXiv | 🟢 Production Ready | 100% | 100% | Yes |
| 25 | Europe PMC | 🟢 Production Ready | 100% | 100% | Yes |
| 26 | ORCID | 🟢 Production Ready | 100% | 100% | Yes |
| 27 | Dropbox | 🟢 Production Ready | 100% | 100% | Yes |
| 28 | OneDrive | 🟢 Production Ready | 100% | 100% | Yes |

---

## 2. #21 — Locked milestones (2.1–2.7 only)

**Status:** 🟢 **#21 Production Ready** — milestones **2.1–2.7** complete (2026-08-03)  
**Next milestone:** Fill [16 Competitive Replacement Review](16-COMPETITIVE-REPLACEMENT-REVIEW.md) — **not** Graph / Agents / Memory.

Plan: [15](15-PAPER-ANALYSIS-IMPLEMENTATION-PLAN.md) · Gap: [14](14-PAPER-ANALYSIS-GAP-REPORT.md) · Audit: [13](13-PAPER-ANALYSIS-AUDIT.md)

```text
2.1 Scientific Structure          ✅ Production Ready
2.2 Methodology Intelligence      ✅ Production Ready
2.3 Statistical Intelligence      ✅ Production Ready
2.4 Evidence Intelligence         ✅ Production Ready
2.5 Limitations & Novelty         ✅ Production Ready
2.6 Scientific Entities (paper-scoped)  ✅ Production Ready
2.7 Quality Assessment (inspectable checklist)  ✅ Production Ready
        ↓
#21 🟢 → … → #26 ORCID 🟢 → #27 Dropbox 🟢 → #28 OneDrive 🟢
        ↓
After #28 → Competitive Replacement Review ([16](16-COMPETITIVE-REPLACEMENT-REVIEW.md))
```

### 2.1 attestation (2026-08-03)

```text
✓ Backend: scientific_structure on document_understanding serialize
✓ Frontend: Structure “Scientific framing” + Overview bridge
✓ Workers: unchanged (phase1_analysis path)
✓ Tests: backend/document_understanding/test_scientific_structure.py + FE mapper tests
✓ Invent-nothing: empty when no signals
✓ Cost: 0 extra LLM tokens; regex over existing abstract/sections; no PDF re-parse
✓ Feature gate + one-paper test: yes
```

Code: `backend/document_understanding/scientific_structure.py`, `_serialize_document` hook, `PaperStructureTab` / `PaperOverviewTab`.

### 2.2 attestation (2026-08-03)

```text
✓ Backend: methodology_profile on document_understanding (after classification + medical enrich)
✓ Frontend: Structure “Methodology” + Overview methodology hint
✓ Workers: unchanged (phase1_analysis path; additive attach only)
✓ Tests: backend/document_understanding/test_methodology_profile.py + FE mapper tests
✓ Invent-nothing: null/empty when signals weak; non-medical papers get design/dataset/metrics when present
✓ Cost: 0 extra LLM tokens; regex over methods/abstract; optional classification/PICO reuse
✓ Feature gate + one-paper test: yes
```

Code: `backend/document_understanding/methodology_profile.py`, `_attach_methodology_profile`, `PaperStructureTab` / `PaperOverviewTab`.

### 2.3 attestation (2026-08-03)

```text
✓ Backend: statistics_profile on document_understanding (after methodology; medical enrich)
✓ Frontend: Structure “Statistical findings” + Overview hint (distinct from doc counts)
✓ Workers: unchanged (phase1_analysis path; additive attach only)
✓ Tests: backend/document_understanding/test_statistics_profile.py + FE mapper tests
✓ Invent-nothing: no significance from p alone; interpretations require author_stated
✓ Cost: 0 extra LLM tokens; regex over results/abstract/discussion; optional medical measures reuse
✓ Feature gate + one-paper test: yes
```

Code: `backend/document_understanding/statistics_profile.py`, `_attach_statistics_profile`, `PaperStructureTab` / `PaperOverviewTab`.

### 2.4 attestation (2026-08-03)

```text
✓ Backend: phase_projector.v1.2 facets (method/quote/confidence/limitations + methodology/stats enrich)
✓ Backend: MAX_CANDIDATES_PER_FILE=30 noise cap; prompt version aligned in extract hash
✓ Backend: maybe_enqueue_evidence_extract after phase1 when project + research_ready
✓ Frontend: Overview copy — auto-run happy path; manual Extract remains override
✓ Workers: additive chain only — existing evidence_extract job family
✓ Tests: test_phase_projector + test_auto_extract + extract contract
✓ Invent-nothing: still skip ungrounded; limitations only from Phase 1 / EG props
✓ Cost: 0 extra LLM; reuses Phase 1 projection
✓ Feature gate + one-paper test: yes
```

Code: `backend/evidence/phase_projector.py`, `backend/evidence/services/auto_extract.py`, `worker._handle_phase1_analysis`.

### 2.5 attestation (2026-08-03)

```text
✓ Backend: limitations_novelty_profile on document_understanding (author_stated only)
✓ Backend: phase_projector reads profile limitations into EO candidates
✓ Frontend: Structure “Limitations & novelty” + Overview hint
✓ Workers: unchanged (phase1 attach only)
✓ Tests: test_limitations_novelty_profile.py + FE mapper tests
✓ Invent-nothing: no AI hype / breakthrough scoring; empty when no author signals
✓ Cost: 0 extra LLM tokens; regex over discussion/limitations/abstract
✓ Feature gate + one-paper test: yes
```

Code: `backend/document_understanding/limitations_novelty_profile.py`, `_attach_limitations_novelty_profile`, `PaperStructureTab` / `PaperOverviewTab`.

### 2.6 attestation (2026-08-03)

```text
✓ Backend: scientific_entities_profile on document_understanding (project methodology/stats)
✓ Backend: local relations only when both ends exist; optional medical enrich
✓ Frontend: Entities tab shows scientific entities when medical skipped; local relations list
✓ Frontend: Overview chips include scientific entities
✓ Workers: unchanged (phase1 attach only)
✓ Tests: test_scientific_entities_profile.py + FE entities enrich tests
✓ Invent-nothing: empty when profiles empty; no Neo4j / global graph
✓ Cost: 0 extra LLM; reuse 2.2/2.3 profiles
✓ Feature gate + one-paper test: yes
```

Code: `backend/document_understanding/scientific_entities_profile.py`, `_attach_scientific_entities_profile`, `PaperEntitiesTab` / `PaperOverviewTab`.

### 2.7 attestation (2026-08-03)

```text
✓ Backend: quality_assessment_profile — Methodology / Evidence / Limitations / Availability checklist
✓ Backend: categorical bands + per-item reason; no overall_score / 8.9/10
✓ Frontend: Structure “Quality assessment” + Overview hint
✓ Workers: unchanged (phase1 attach only)
✓ Tests: test_quality_assessment_profile.py + FE mapper tests
✓ Invent-nothing: missing notes when signals absent; reasons always present
✓ Cost: 0 extra LLM; deterministic aggregate of 2.2–2.6 profiles
✓ Feature gate + one-paper test: yes
```

Code: `backend/document_understanding/quality_assessment_profile.py`, `_attach_quality_assessment_profile`, `PaperStructureTab` / `PaperOverviewTab`.

| Milestone | Reality scope |
|-----------|----------------|
| 2.1 ✅ | Structure + objectives/RQ/hypotheses/problem **when reliably extractable** |
| 2.2 ✅ | Methods fields you can **consistently** extract; light author-stated repro signals OK |
| 2.3 ✅ | Stats **explicitly present** only — no invented significance |
| 2.4 ✅ | Better projector + auto evidence happy path; additive EO facets |
| 2.5 ✅ | Prefer **author-stated** limitations/novelty |
| 2.6 ✅ | Paper-scoped entities/relations — not global graph |
| 2.7 ✅ | Inspectable quality panel (why), not `8.9/10` |

**Deferred (still valuable — not in 2.1–2.7):** Figures & Tables · full reproducibility assessment · Cross-Paper Intelligence · citation network.

**Next:** Fill [16 Competitive Replacement Review](16-COMPETITIVE-REPLACEMENT-REVIEW.md) — do not expand #21–28 unless a deferred item is explicitly promoted.

**Stop revising this tracker** except to mark milestone attestations.

---

## 3. Change log

| Date | Note |
|------|------|
| 2026-08-03 | Tracker + audit pack created. |
| 2026-08-03 | Plan v2 explored (Figures/Cross-Paper/reorder). |
| 2026-08-03 | **Locked:** restore 2.1–2.7; feature gate; defer Figures/Repro/Cross-Paper/citation network; inspectable quality. |
| 2026-08-03 | **2.1 Scientific Structure → Production Ready.** Next: 2.2 Methodology. |
| 2026-08-03 | **2.2 Methodology Intelligence → Production Ready.** Next: 2.3 Statistics. |
| 2026-08-03 | **2.3 Statistical Intelligence → Production Ready.** Next: 2.4 Evidence. |
| 2026-08-03 | **2.4 Evidence Intelligence → Production Ready.** Next: 2.5 Limitations & Novelty. |
| 2026-08-03 | **2.5 Limitations & Novelty → Production Ready.** Next: 2.6 Entities. |
| 2026-08-03 | **2.6 Scientific Entities → Production Ready.** Next: 2.7 Quality. |
| 2026-08-03 | **2.7 Quality Assessment → Production Ready. #21 🟢.** Next: #22 PubMed. |
| 2026-08-03 | Framing: **Paper Intelligence complete; Knowledge Acquisition beginning** (Phase 2 ≠ finished). #22 bar: not “another search” — PubMed → Library → SUE → Evidence → Writing. Post-#28 note: consider Research Workspace & Publication before KG/Memory/Agents. |
| 2026-08-03 | **Phase 2A / 2B** naming; **Golden Rule** (identical downstream per source); post-#28 = Product Readiness Review + stub [16](16-COMPETITIVE-REPLACEMENT-REVIEW.md); no auto Phase 3. |
| 2026-08-03 | [16](16-COMPETITIVE-REPLACEMENT-REVIEW.md) strengthened: Context Switching Audit · competitive advantage · real-user marketing gate · critical daily vs future pillars. |
| 2026-08-03 | **#16 template complete:** Research Week Diary · Session Completion KPI · Primary Research Workspace framing · Product Doctrine (reduce context switching). |
| 2026-08-03 | **#22 PubMed → Production Ready.** NCBI search + PMID import + OA PDF → shared `import` pipeline (Golden Rule). Next: #23 Google Drive. |
| 2026-08-03 | Post-#22 doctrine: connector product test for #23–28; identity/dedupe watch (one library item · many source links). |
| 2026-08-03 | **#23 Google Drive → Production Ready.** OAuth connect · browse PDFs · import → shared `import` job (Golden Rule). Folder watch deferred. Next: #24 arXiv. |
| 2026-08-03 | **#24 arXiv → Production Ready.** Atom search + arXiv id import + PDF → shared `import` pipeline (Golden Rule). Next: #25 Europe PMC. |
| 2026-08-03 | Golden Rule restated: Production Ready only when paper reaches **Writing Intelligence** via shared pipeline — no provider-specific analysis/evidence/shortcuts. #24 re-verified under that bar. |
| 2026-08-03 | **Golden Rule of Acquisition** locked (general form): providers differ only in auth / metadata / document acquisition; after bytes accepted, all stages provider-agnostic. After #28 → Competitive Replacement Review, not Graph/Agents. |
| 2026-08-03 | **#25 Europe PMC → Production Ready.** REST search + PMCID/PMID import + OA PDF → shared `import` pipeline (Golden Rule). Next: #26 ORCID. |
| 2026-08-03 | **#26 ORCID → Production Ready.** Paste ORCID iD → public works list → import (+ OA via DOI/OpenAlex when available) → shared pipeline. OAuth deferred. Next: #27 Dropbox. |
| 2026-08-03 | **#27 Dropbox → Production Ready.** OAuth connect · browse PDFs · import → shared `import` job (Golden Rule). Folder watch deferred. Next: #28 OneDrive. |
| 2026-08-04 | **#16 governance upgrade:** Research Progress KPI · Cognitive Load Audit · healthy primary-workspace definition (leave only for genuine external need) · Product Doctrine v2 (quality / velocity / confidence / continuity). |

---

## 4. Knowledge Acquisition (#22–28) — Phase 2B

Unblocked by #21 🟢. **Golden Rule of Acquisition** applies to every row: same canonical Paper → same pipeline; connectors are entry points, not special cases.

| # | Subsystem | Status |
|---|-----------|--------|
| 22 | PubMed | 🟢 |
| 23 | Google Drive | 🟢 |
| 24 | arXiv | 🟢 |
| 25 | Europe PMC | 🟢 |
| 26 | ORCID | 🟢 |
| 27 | Dropbox | 🟢 |
| 28 | OneDrive | 🟢 |

### #22 PubMed — product bar (binding)

**Status:** 🟢 **Production Ready** (2026-08-03)

Not “just another search provider.” Success looks like:

```text
PubMed Search → Import → Library → Paper Analysis 2.0 → Evidence → Writing → Reviewer → Export
```

Every PubMed paper must automatically get methodology / statistics / evidence / novelty / quality from SUE when an OA PDF is attached (or after manual attach).  
User reaction to avoid: “Cool, they added PubMed.”  
User reaction to aim for: “Every PubMed paper becomes structured research.”  
Attestation requires Golden Rule proof — no skipped stage vs other sources / vs upload path.

#### #22 attestation

| Check | Evidence |
|-------|----------|
| Search | `GET /api/discover?provider=pubmed` → NCBI E-utilities (`backend/scholarly/pubmed.py`) |
| Import + PMID identity | `POST /api/discover/import` with `provider=pubmed`; `external_provider=pubmed`, `external_item_id=pmid`, tags `pmid:` |
| Dedupe | DOI match · PMID external id match |
| Golden Rule OA path | OA/PMC PDF → `apply_pdf_bytes_to_stub` → `enqueue_import` → same worker chain as upload |
| No OA | Metadata stub + FE note to attach PDF (same attach path as library) |
| UI | Discover source tabs OpenAlex / PubMed; Integrations catalog **Live**; deep link `/search?mode=discover&provider=pubmed` |
| Cost | 0 extra LLM on import; SUE cost identical to native upload once PDF lands |
| Tests | `backend/scholarly/test_pubmed.py`, `backend/library/test_discover_pubmed.py`, catalog + discoverApi FE |

**Next:** **#23 Google Drive**

### #23 Google Drive — product bar (binding)

**Status:** 🟢 **Production Ready** (2026-08-03)

Drive is a **connector**, not intelligence. Complete only if:

```text
Drive connect/browse → Import PDF → Library → Paper Analysis 2.0 → Evidence → Writing → Reviewer
```

#### #23 attestation

| Check | Evidence |
|-------|----------|
| OAuth | `GET /api/library/google_drive/connect` → callback → `LibraryConnection(provider=google_drive)` |
| Browse | `GET /api/library/google_drive/files` (PDF list in folder) |
| Import + Golden Rule | `POST /api/library/google_drive/import` → download → `apply_pdf_bytes_to_stub` → `enqueue_import` |
| Identity | `external_provider=google_drive`, `external_item_id=Drive file id`, tags `from-google-drive` |
| Catalog | Live + connectable; deep link `/library?provider=google_drive#import` |
| FE | Integrations Connect · Library Import menu · Sources strip · PDF picker dialog |
| Deferred | Folder watch / Changes API (honest: `folder_watch=false`) |
| Cost | 0 extra LLM on import; SUE identical to upload once PDF lands |
| Tests | `backend/library/test_google_drive.py`, `test_google_drive_import.py`, catalog |

**Next:** **#24 arXiv**

### #24 arXiv — product bar (binding)

**Status:** 🟢 **Production Ready** (2026-08-03)

Not “just another search provider.” Success looks like:

```text
arXiv Search → Import → Library → PDF → shared `import` job
  → Paper Analysis 2.0 → Evidence → Writing Intelligence → Reviewer → Export
```

Every arXiv paper must use the **same** SUE / evidence / writing path as upload — no arXiv-specific analysis or evidence extract.

#### #24 attestation

| Check | Evidence |
|-------|----------|
| Search | `GET /api/discover?provider=arxiv` → Atom API (`backend/scholarly/arxiv.py`) |
| Import + Golden Rule | `POST /api/discover/import` → `download_pdf` → `apply_pdf_bytes_to_stub` → `enqueue_import` → same worker chain as upload (`import` → `phase1_analysis` → auto `evidence_extract` → Writing Intelligence) |
| No shortcuts | Entry point only differs at PDF fetch; analysis/evidence/writing are shared modules |
| Identity | `external_provider=arxiv`, `external_item_id=arxiv_id`, tags `from-arxiv` / `arxiv:{id}` |
| Catalog | Live; deep link `/search?mode=discover&provider=arxiv` |
| FE | Discover tabs · Library Import menu · Command palette · HomeHeroUpload |
| Flag | `ENABLE_ARXIV` (default true); circuit + bulkhead |
| Cost | 0 extra LLM on import; SUE/evidence/writing identical to upload once PDF lands |
| Tests | `backend/scholarly/test_arxiv.py`, `backend/library/test_discover_arxiv.py`, catalog + discoverApi FE |

**Next:** **#25 Europe PMC**

### #25 Europe PMC — product bar (binding)

**Status:** 🟢 **Production Ready** (2026-08-03)

Not “another PubMed.” Success looks like:

```text
Europe PMC Search → Import → Library → OA PDF → shared `import` job
  → Paper Analysis 2.0 → Evidence → Writing Intelligence → Reviewer → Export
```

Europe PMC is an entry point only — same SUE / evidence / writing path as upload. No Europe-PMC-specific extractor or writer.

#### #25 attestation

| Check | Evidence |
|-------|----------|
| Search | `GET /api/discover?provider=europe_pmc` → Europe PMC REST (`backend/scholarly/europe_pmc.py`) |
| Import + Golden Rule | `POST /api/discover/import` → `download_open_access_pdf` → `apply_pdf_bytes_to_stub` → `enqueue_import` → same worker chain as upload |
| No shortcuts | Provider-specific code ends at PDF bytes |
| Identity | `external_provider=europe_pmc`, `external_item_id=PMCID` (or `MED:{pmid}`), tags `from-europe-pmc` |
| Catalog | Live; deep link `/search?mode=discover&provider=europe_pmc` |
| FE | Discover tabs · Library Import · Command palette · HomeHeroUpload |
| Flag | `ENABLE_EUROPE_PMC` (default true); circuit + bulkhead independent of PubMed |
| Cost | 0 extra LLM on import; SUE/evidence/writing identical once PDF lands |
| Tests | `backend/scholarly/test_europe_pmc.py`, `backend/library/test_discover_europe_pmc.py`, catalog + discoverApi FE |

**Next:** **#26 ORCID**

### #26 ORCID — product bar (binding)

**Status:** 🟢 **Production Ready** (2026-08-03)

Not OAuth identity. Success looks like:

```text
Paste ORCID iD → list public works → Import selected
  → Library stub (+ OA PDF when DOI/PMID/arXiv resolvable)
  → shared import → Analysis 2.0 → Evidence → Writing Intelligence
```

Honesty: many ORCID works have no PDF → metadata stub + attach note (same as PubMed No OA). OAuth / private works deferred.

#### #26 attestation

| Check | Evidence |
|-------|----------|
| List | `GET /api/discover?provider=orcid&q={orcid}` → Public API (`backend/scholarly/orcid.py`) |
| Import + Golden Rule | `POST /api/discover/import` → OA resolve → `apply_pdf_bytes_to_stub` → `enqueue_import` when PDF exists |
| No shortcuts | Provider-specific code ends at PDF bytes / metadata stub |
| Identity | `external_provider=orcid`, `external_item_id={orcid}:{put-code}`, tags `from-orcid` |
| Catalog | Live (`auth=none`); deep link `/search?mode=discover&provider=orcid` |
| FE | Discover tab · Library Import · Command palette · HomeHeroUpload |
| Deferred | ORCID OAuth, private works, LibraryConnection, author graph |
| Flag | `ENABLE_ORCID` (default true) |
| Tests | `backend/scholarly/test_orcid.py`, `backend/library/test_discover_orcid.py`, catalog + discoverApi FE |

**Next:** **#27 Dropbox**

### #27 Dropbox — product bar (binding)

**Status:** 🟢 **Production Ready** (2026-08-03)

Dropbox is a **connector**, not intelligence. Complete only if:

```text
Dropbox connect/browse → Import PDF → Library → Paper Analysis 2.0 → Evidence → Writing Intelligence → Reviewer
```

#### #27 attestation

| Check | Evidence |
|-------|----------|
| OAuth | `GET /api/library/dropbox/connect` → callback → `LibraryConnection(provider=dropbox)` |
| Browse | `GET /api/library/dropbox/files` (PDF list in folder) |
| Import + Golden Rule | `POST /api/library/dropbox/import` → download → `apply_pdf_bytes_to_stub` → `enqueue_import` |
| Identity | `external_provider=dropbox`, `external_item_id=Dropbox file id`, tags `from-dropbox` |
| Catalog | Live + connectable; deep link `/library?provider=dropbox#import` |
| FE | Integrations Connect · Library Import menu · Sources strip · PDF picker dialog |
| Deferred | Folder watch / webhooks (honest: `folder_watch=false`) |
| Cost | 0 extra LLM on import; SUE identical to upload once PDF lands |
| Tests | `backend/library/test_dropbox.py`, `test_dropbox_import.py`, catalog |

**Next:** Fill [16 Competitive Replacement Review](16-COMPETITIVE-REPLACEMENT-REVIEW.md)

### #28 OneDrive — product bar (binding)

**Status:** 🟢 **Production Ready** (2026-08-03)

OneDrive is a **connector**, not intelligence. Complete only if:

```text
OneDrive connect/browse → Import PDF → Library → Paper Analysis 2.0 → Evidence → Writing Intelligence → Reviewer
```

#### #28 attestation

| Check | Evidence |
|-------|----------|
| OAuth | `GET /api/library/onedrive/connect` → callback → `LibraryConnection(provider=onedrive)` |
| Browse | `GET /api/library/onedrive/files` (PDF list in folder) |
| Import + Golden Rule | `POST /api/library/onedrive/import` → download → `apply_pdf_bytes_to_stub` → `enqueue_import` |
| Identity | `external_provider=onedrive`, `external_item_id=Graph item id`, tags `from-onedrive` |
| Catalog | Live + connectable; deep link `/library?provider=onedrive#import` |
| FE | Integrations Connect · Library Import menu · Sources strip · PDF picker dialog |
| Deferred | Folder watch / delta (honest: `folder_watch=false`) |
| Cost | 0 extra LLM on import; SUE identical to upload once PDF lands |
| Tests | `backend/library/test_onedrive.py`, `test_onedrive_import.py`, catalog |

**Next:** Fill [16 Competitive Replacement Review](16-COMPETITIVE-REPLACEMENT-REVIEW.md) — **do not** start Graph / Research Memory / Agents.
