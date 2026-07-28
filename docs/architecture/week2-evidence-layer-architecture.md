# Week 2 Evidence Layer Architecture Decision Document (ADD)

Status: Accepted (frozen Week 2 intent)  
Scope: Phase 2.2 Evidence Layer MVP  
Audience: Backend, frontend, platform, security, and QA leads  
Depends on: Writing Studio Shell `v0.1.0`, Phase 1.1 / 1.5 / 1.7, ADR-0003  
Related: `docs/phase-2-writing-roadmap.md` §2.2, `docs/00-constitution.md` Principle 11,
`docs/architecture/add-0005-research-intelligence-pipeline.md` (post-MVP intelligence — not Week 2),
`docs/architecture/week2-evidence-layer-platform-contracts.md` (ADR-0005 freeze),
`docs/architecture/week2-release-decision.md`

---

## 1) Principle 0 — Evidence First (binding)

> All knowledge shown to users must originate from stored evidence.
>
> LLMs may organise, summarise, compare, and explain.
>
> They may never invent evidence.
>
> Every generated statement must be reproducible from stored evidence.

**Constitution rule (permanent):** every new AI feature must consume the Evidence Layer rather than bypass it. See ADR-0003 and Principle 11 in `docs/00-constitution.md`.

Governing product rule (north star):

> The Evidence Layer never generates facts. It discovers, organises, scores, and reasons over evidence.

---

## 2) Verdict and scope cut

**Approve the six-engine north star as long-term architecture. Do not implement six engines as Week 2.**

Week 2 ships a thin, auditable **Evidence Layer** that unlocks Writing Studio’s differentiator (Evidence Inspector) and researcher invites after Phase 2.2.

```text
Evidence Layer (Week 2)
├── Evidence Objects (canonical)
├── Provenance
├── Sentence Bindings
├── Evidence Inspector
├── Candidate status on EvidenceObject
├── Human review (claim_reviews)
├── Versioned extraction
└── POST /api/evidence/explain
```

### Explicit non-goals (this milestone)

- Six independently deployed engines
- Cross-paper Reasoning Engine chat
- Research memory / personalization
- Hypothesis generation / peer-review assistant
- Guided writing (Phase 2.4)
- Citation Engine rebuild (Phase 2.3 — connect later)
- Neo4j / new graph database
- Replacing Phase 1.5 / 1.7
- New `papers` table (use Library `files` + Research Ready)

### Near-term after MVP (not Week 2 freeze)

**Evidence Timeline** (topic → chronological paper/evidence stream) — only after Inspector is proven against real objects.

---

## 3) Component topology

```text
Library (Research Ready files)
  -> Phase 1.1 Document Understanding (sections, page/quote anchors)
  -> Phase 1.5 Evidence Grading (quality / bias / consistency)
  -> Phase 1.7 Knowledge Graph (SUPPORTS / CONTRADICTS / EVIDENCE_CLAIM)
       -> Evidence Extractor job (worker)
            -> evidence_objects (candidate)
            -> claim_reviews (human accept/reject/edit)
       -> writing_sentence_bindings
            -> POST /api/evidence/explain
                 -> Writing Studio Evidence Inspector
```

### Service boundary

- Modular monolith under `backend/evidence/` (same pattern as `backend/writing/`).
- Factory/DI wiring from `server.py` — never `import server`.
- Async extraction via existing `worker.py` job queue; no new broker.

### Package layout (target)

```text
backend/evidence/
  __init__.py
  objects.py       # EvidenceObject domain + serializers
  extractor.py     # Research Ready → candidate objects
  scoring.py       # confidence_band from Phase 1.5 + heuristics
  bindings.py      # sentence/block ↔ evidence links
  provenance.py    # pipeline version / content hash helpers
  inspector.py     # explain assembly (no invented facts)
  reviews.py       # accept / reject / edit
  api/             # blueprint factory (optional seam)
  validation/
  services/
  events/
  jobs/
  tests/
```

Umbrella name in docs/API: **Evidence Layer**. Layer-2 binder module name: **Evidence Support** (not a second “Evidence Engine”). Long-term multi-engine platform remains aspirational naming only.

---

## 4) Canonical contract: EvidenceObject

`EvidenceObject` is Dhund’s universal research-knowledge unit. Names like Claim / Finding / Result are **views or fields**, not competing root entities.

### Required shape (Week 2)

```json
{
  "id": "…",
  "user_id": 1,
  "project_id": 2,
  "file_id": 10,
  "page": 12,
  "char_start": 100,
  "char_end": 240,
  "section": "Results",
  "quote": "…",
  "claim": "…",
  "study_type": "RCT",
  "study_quality": "High",
  "supports": ["…"],
  "contradicts": [],
  "limitations": [],
  "confidence_band": "high",
  "pipeline_version": "2.2.0",
  "created_by": "analysis-pipeline",
  "status": "candidate",
  "content_hash": "…",
  "supersedes_id": null,
  "provenance": {
    "document_understanding": "…",
    "evidence_grading": "…",
    "knowledge_graph": "…",
    "extraction_prompt_version": "…",
    "pipeline_version": "2.2.0"
  }
}
```

### Hard rules

| Rule | Rationale |
|------|-----------|
| Always page-anchored (`file_id` + `page` + `quote`; prefer `char_start`/`char_end`) | Ideas without spans are unverifiable |
| `confidence_band` ∈ `low\|moderate\|high` | Uncalibrated `0.92` is marketing, not science |
| Append-only versions; re-extraction supersedes | Never silent-mutate accepted objects |
| Project + user scoped | Same isolation model as Writing Shell |
| Reference `file_id`, not a new papers table | Library Research Ready is paper identity |
| Auto-extract starts as `candidate` | Human review required for trust |

---

## 5) Reuse of Phase 1 (non-negotiable)

| Existing | Week 2 use |
|----------|------------|
| Phase 1.1 Document Understanding | Sections, page/quote anchors |
| Phase 1.5 Evidence Grading | Inputs to `study_quality` / `confidence_band` |
| Phase 1.7 Knowledge Graph | SUPPORTS / CONTRADICTS / EVIDENCE_CLAIM → object fields |
| Library Research Ready | Extraction gate |
| Writing Shell `v0.1.0` | Binding surface + Inspector host |

Do **not** build a parallel GRADE stack or parallel graph store. Dual truth is a product bug.

---

## 6) Human review

Table: `claim_reviews` (keyed by `evidence_object_id`).

| Field | Purpose |
|-------|---------|
| evidence_object_id | Target |
| user_id | Reviewer |
| status | `accepted` \| `rejected` \| `edited` |
| reason | Optional free text |
| edited_claim / edited_quote | Optional when status=edited |
| reviewed_at | Audit |

Inspector prefers **accepted** evidence for “supported by” counts; candidates are visible and clearly labeled. Empty / weak evidence UX must say **insufficient evidence** — never pad with model prose.

---

## 7) Writing bindings and explain API

Stable anchors: prefer `block_id` / markdown range id over fragile string match alone. Store both range metadata and optional quote snippet for display.

Primary Inspector backend:

`POST /api/evidence/explain`

- **Input:** `document_id` + sentence/block anchor (+ optional selected text).
- **Output:** EvidenceObjects → claim fields → papers (`file_id`) → pages → short reasoning chain assembled **only** from stored links/provenance.
- **Authz:** Writing Shell ownership; server validates every `evidence_id`.
- Frontend stays thin: does not re-rank evidence client-side.

---

## 8) Security

| Threat | Control |
|--------|---------|
| Cross-tenant leak | `user_id` + `project_id` on every row; ownership checks; no IDOR via guessed UUIDs/ids |
| Prompt injection via PDF text | Treat paper text as untrusted; structured extraction schema; never execute instructions in papers |
| LLM inventing evidence IDs | Server validates every referenced id exists and is owned before attach/render |
| Sensitive clinical quotes | Same ACL as source file; purge on account delete; avoid full quotes in telemetry |
| Mutable “immutable” evidence | Append-only versions; audit log of supersede/accept/reject |
| Cost/DoS via mass re-extraction | Job queue + rate limits; Research Ready + project quotas |
| Public share of evidence chains | Authz on every Inspector/explain fetch; no public share in Week 2 |

---

## 9) Observability and ops

- Structured logs: `project_id`, `file_id`, `evidence_object_id`, `pipeline_version`, `job_id` — not full quotes by default.
- Metrics: extraction success/fail per paper, candidate→accepted conversion, explain latency, insufficient-evidence rate.
- Partial failure: per-paper extraction may fail without poisoning project aggregates.
- Idempotency: `(project_id, file_id, content_hash, pipeline_version)` uniqueness for active (non-superseded) objects / extraction runs.

---

## 10) Delivery process

Same staged process as Week 1 Writing Shell:

1. This ADD (frozen)
2. Backend technical design (schema, extractor, explain, reviews)
3. Frontend technical design (Evidence Inspector)
4. Verification & QA spec
5. Implementation board + slices
6. Implement → Stage 4 gates → release candidate (e.g. `v0.2.0-rc1`)

Downstream docs:

- `docs/architecture/week2-evidence-layer-backend-technical-design.md`
- `docs/architecture/week2-evidence-layer-frontend-technical-design.md`
- `docs/architecture/week2-evidence-layer-verification-and-qa-spec.md`
- `docs/architecture/week2-evidence-layer-implementation-board.md`
- Migration `0033_evidence_layer.sql`

**After Week 2 MVP:** do not jump to AI writing. Build Research Intelligence
capabilities on this platform per ADD-0005 (retrieval → ranking → consensus →
conflict → then Writing Intelligence / Reviewer / Assistant).
