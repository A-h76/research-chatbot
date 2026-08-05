# Engineering Evolution Tracker

**Status:** Living — update when an area moves Current → Target (or priority changes).  
**Date opened:** 2026-08-05  
**Type:** Evolution picture for engineers — **not** a tech-debt dump, **not** a product roadmap.  
**Companions:** [`ENGINEERING-CONSTITUTION-v1.md`](ENGINEERING-CONSTITUTION-v1.md) · [`ARCHITECTURE-HEALTH.md`](ARCHITECTURE-HEALTH.md) · [`audit/03-TECHNICAL-DEBT-REPORT.md`](audit/03-TECHNICAL-DEBT-REPORT.md) · [`adr/`](adr/)

**Purpose:** One shared answer to:

> Where are we today, and where are we going?

Debt lists *what hurts*. Roadmaps *what users get*. **Evolution** tracks *architecture trajectory*.

---

## How to use

1. Before architecture-shaped work, find the **Area** row.  
2. Prefer work that moves **Current → Target** (especially High priority) while shipping ~80% capability.  
3. When Current changes, update this table in the same PR (or immediately after).  
4. Do **not** add aesthetic-only rows (“rename folder X”).

---

## Evolution board

| Area | Current | Target | Priority | Notes |
|------|---------|--------|----------|-------|
| **AI Invocation** | Utility shims on ACR (Bite 8): compare/gaps, project research, embed, memory/titles/metadata. Remaining: writing assistant fallback, session `/api/search` embed in `search/routes.py` | **All LLM** → Capability Router → Gateway (shims retired or ADR) | **High** | Bites 1–8 done 2026-08-05 |
| **Cost Ledger** | Dual write: **CostLedger** ($) + **AI Ledger** (provenance) | AI Ledger owns attribution → CostLedger = billing adapter → **one write façade** | **High** | Unify after all paths record AI Ledger |
| **Upload** | Two HTTP stacks + two storage façades (ADR-0014) | **Shared upload service** — two APIs OK, **one business implementation** | **High** | Not one endpoint; one `apply_pdf_bytes` / policy |
| **Discovery** | Providers + shared scholarly ops; some custom attach/import bits | **Resolver pipeline** — provider supplies metadata only; shared import after acquisition | **High** | PubMed / Drive / OneDrive → same `enqueue_import` spine |
| **Writing** | WI composer + assistant on Gateway; deterministic reviewer/extract engines | Every writing AI rule: `resolve_execution` → Gateway (already true for hot paths) | **Medium** | Maintain; no second compose path |
| **Research Scope** | Gateway present (ADR-0017); chat gated | Scope enforced on all research AI entry points | **High** | ALLOW · CLARIFY · REDIRECT |
| **UFTR** | Platform service (ADR-0015) | Default full-text path — **no per-provider fulltext forks** | **Medium** | Feeds Dimension 3 |
| **server.py** | Monolith (models + many routes) | Thin composition root (`create_app` / register_*) | **Medium** | Peel by blueprint; models extract = separate ADR |
| **Library** | Mixed (files, connect, storage concerns interleaved) | **Library** product domain ownership | **Medium** | Separate from Discovery |
| **Evidence** | Strong + frozen contracts; extract/reviewer engines canonical | Keep growing; single research truth | **Low** (maintain) | ADR-0003 / 0005 / 0007 — don’t reopen casually |
| **Reviewer** | Backend persistence + ACR engine; FE incomplete | Clear Reviewer domain (or owned submodule of Writing) | **Medium** | Product-critical polish |
| **Research Intelligence / SUE** | Phase1 + paper_analysis engines on ACR | Isolated RI domain; one pipeline per rule | **Medium** | Don’t merge into Evidence |
| **Workspace** | Projects / notes / compare exist as surfaces | Explicit Workspace domain | **Low** (later) | After AI + Discovery/Library ownership clearer |
| **Trust** | Baseline + landing Trust Layer; `/trust` page gap | Trust platform layer (events, audit hooks, compliance surfaces) | **Medium** | Serves all domains |
| **Queue / Worker** | Postgres SKIP LOCKED + outbox + heartbeat | Same spine; evolve priority/cancel/observability **in place** | **Low** | ADR-0001 — no Celery rewrite |
| **Ecosystem catalog** | Live vs Soon honesty | Keep as platform honesty layer for integrations | **Low** (maintain) | `backend/ecosystem/` |
| **Shared utilities** | Some dumps / cross-cuts | `shared/<concern>/` only | **Medium** | No new mega-`utils.py` |
| **Legacy schema** | `SearchIndex` unused; `ImportSession` weak | Wire or deprecate deliberately | **Low** | Only when a milestone touches the area |

---

## Priority legend

| Priority | Meaning |
|----------|---------|
| **High** | Move on the next AI / research-AI milestones (80/20) |
| **Medium** | Move when building in that neighborhood |
| **Low** | Explicitly deferred or “maintain / don’t make worse” |

---

## Platform Layers vs Product Domains

Evolution work must name **which kind** of area it is:

### Platform Layers (serve everything)

AI Platform · Storage · Trust · Infrastructure · Worker · Queue · Observability · Auth · Shared

### Product Domains (what users experience)

Discovery · Library · Evidence · Writing · Reviewer · Workspace · (Ecosystem UX honesty)

See [`ENGINEERING-CONSTITUTION-v1.md`](ENGINEERING-CONSTITUTION-v1.md) §2.

---

## Canonical implementation (Dimension 3)

**Principle:** Every business rule has **one implementation**; callers delegate.

| ✅ Fine | ❌ Not fine |
|--------|------------|
| JWT + session upload APIs → `UploadService` | PubMed + OpenAlex each reimplement store → queue → analysis |
| React + CLI → Library API | Drive + OneDrive each custom attach logic |
| PubMed + arXiv as thin provider edges | Second `OpenAI()` in a feature package |

**PR checklist** (before merge):

1. Does this introduce a **second implementation** of an existing rule?
2. If yes: **Why?** · **Temporary?** · **ADR?** · **Retirement plan?**
3. If no plan → reject or redesign.

**Path to KPI 4** (see [`ARCHITECTURE-HEALTH.md`](ARCHITECTURE-HEALTH.md) §3): High rows below — especially **Cost Ledger**, **Upload**, **Discovery** — not folder merges. Rescore only when call sites converge (see **Architectural drift** in Architecture Health).

---

## Recently moved (changelog)

| Date | Area | Change |
|------|------|--------|
| 2026-08-05 | **AI Invocation** | Bite 8: utility_engine — compare/gaps, project research, embed, memory/titles/metadata on ACR + ledger |
| 2026-08-05 | **Search** | `invoke_rag_llm` + `resolve_search_execution`; `POST /api/rag` ACR + ledger + `ai_execution` |
| 2026-08-05 | **SUE / Analyze Paper** | `invoke_paper_analysis_llm` + `record_phase1_pipeline_execution`; worker + upload analyze route |
| 2026-08-05 | **Evidence** | `execute_evidence_extraction` + `resolve_evidence_extract_execution`; projector ledger + `ai_execution` on sync extract |
| 2026-08-05 | **Reviewer** | `execute_reviewer` + `resolve_reviewer_execution`; deterministic validation + AI Ledger; `parent_execution_id` → WI composer |
| 2026-08-05 | **AI Invocation** | Writing Assistant (`POST /api/writing`) via `resolve_writing_assistant_execution` + Gateway + AI Ledger |
| 2026-08-05 | **AI Invocation** | Gateway owns chat Responses transport (`stream_responses` / `create_responses`); `OpenAIResponsesAdapter`; AI Ledger `trace_id` + `status` |
| 2026-08-05 | **AI Invocation** | `/api/chat` model via `resolve_chat_execution`; `ai_execution` on SSE `done` + AI Ledger record |
| 2026-08-05 | **Cost Ledger** | Documented dual-write (CostLedger $ + AI Ledger provenance); chat now hits both |
| 2026-08-05 | — | Tracker opened; baseline from Engineering Constitution + debt audit |
| 2026-08-05 | Doctrines | Engineering Constitution v1 frozen; Architecture Health opened |

*(Append rows upward as Current advances.)*

---

## Out of scope for this file

- Feature ship lists → product / audit trackers  
- Competitive gates → `docs/audit/16-COMPETITIVE-REPLACEMENT-REVIEW.md`  
- UI doctrine → Design Language v1  
- Scoring KPIs → [`ARCHITECTURE-HEALTH.md`](ARCHITECTURE-HEALTH.md)  
