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

## Strategic pivot (post Bite 11)

**Stop active AI Platform migration work.** Canonical path is:

```text
Research Job → Capability Router → Gateway → AI Ledger → Artifact
```

Highest-leverage work is now **research workflow convergence** — especially acquisition, import, upload, UFTR, and evidence generation — so every provider is a thin entry into the same spine.

**Do not start:** CQRS · Kafka · microservices · event sourcing · Kubernetes · graph DBs.

See [`ARCHITECTURE-HEALTH.md`](ARCHITECTURE-HEALTH.md) § Strategic pivot + Dimension 8 (Workflow Completeness).

---

## Evolution board

| Area | Current | Target | Priority | Notes |
|------|---------|--------|----------|-------|
| **Discovery / Library spine** | ImportService spine (Bite 12) — Discover, Drive, OneDrive, Upload enqueue, attach, UFTR | Thin acquire edges → ImportService → UFTR/attach → enqueue → Worker → Evidence | **High** | Phase A landed 2026-08-05; Zotero/BibTeX still on LibraryImportService |
| **Upload** | UploadService (Bite 13) — session/JWT/bulk/presign register via one impl; dual storage façades kept | Maintain; storage folder merge deferred (ADR-0014) | **Medium** | Phase C done 2026-08-05 |
| **UFTR** | Platform service (ADR-0015) | Default full-text path — **no per-provider fulltext forks** | **High** | Feeds Dim 2 / 8 |
| **Domain events** | In-process bus (Bite 14) — `PaperImported`, `EvidenceAccepted`, `WritingGenerated`, `ResearchDecisionRecorded`, `AIExecutionCompleted` | Maintain; add names only for new business facts | **Medium** | Phase B done 2026-08-05 — **not** Kafka |
| **Workflow contracts** | WF v1.0 freeze (Bite 16) — Import / Evidence / Writing / Review / Publication | Maintain; additive fields only | **Low** (freeze) | Phase E done 2026-08-05 |
| **Workflow engine** | Research Workflow Engine (Bite 15) — Import→UFTR→SUE→Evidence→Writing→Review | Maintain; WF contracts frozen | **Low** (maintain) | Phase D done 2026-08-05 — not agents |
| **AI Invocation** | Bites 1–10 on ACR + Gateway | Maintain; shim list only | **Low** (freeze) | Do not chase purity |
| **Cost Ledger** | `record_platform_execution` façade (Bite 11) | Maintain projection path | **Low** (freeze) | Legacy `responses_text` OK |
| **Writing** | WI composer + assistant on Gateway | Maintain; no second compose path | **Low** (maintain) | |
| **Research Scope** | Gateway present (ADR-0017); chat gated | Scope on all research AI entry points | **Medium** | When touching research AI |
| **server.py** | Monolith (models + many routes) | Thin composition root | **Medium** | Peel by blueprint when in neighborhood |
| **Library** | Mixed with Discovery / storage | Clear Library product domain ownership | **High** | Separate from Discovery edges |
| **Evidence** | Strong + frozen contracts | Keep growing; single research truth | **Low** (maintain) | ADR-0003 / 0005 / 0007 |
| **Reviewer** | Backend + ACR engine; FE incomplete | Clear Reviewer domain | **Medium** | Product polish |
| **Research Intelligence / SUE** | Phase1 + paper_analysis on ACR | Isolated RI domain | **Medium** | Don’t merge into Evidence |
| **Workspace** | Projects / notes / compare | Explicit Workspace domain | **Low** | After spine clearer |
| **Trust** | Baseline + landing Trust Layer | Trust platform layer | **Medium** | Serves all domains |
| **Queue / Worker** | Postgres SKIP LOCKED + outbox | Same spine; evolve in place | **Low** | ADR-0001 — no Celery |
| **Ecosystem catalog** | Live vs Soon honesty | Maintain | **Low** | `backend/ecosystem/` |
| **Shared utilities** | Some dumps | `shared/<concern>/` only | **Medium** | |
| **Legacy schema** | `SearchIndex` unused; `ImportSession` weak | Wire or deprecate deliberately | **Low** | When milestone touches area |

---

## Priority legend

| Priority | Meaning |
|----------|---------|
| **High** | Next architecture cycle (Library spine / upload / events) |
| **Medium** | Move when building in that neighborhood |
| **Low** | Explicitly deferred, maintain, or **frozen** (AI Platform) |

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

**Path to KPI ≥ 4:** High rows — **Discovery/Library spine**, **Upload**, **UFTR**, **Domain events** — not folder merges, not AI polish. Rescore only when call sites converge.

---

### Next platform bites (Library spine)

| Phase | Bite | Scope | Moves |
|-------|------|-------|-------|
| — | **9–11** | AI invocation + ledger façade | ✅ Done 2026-08-05 — **AI freeze** |
| **A** | **12** | Canonical Library / Import spine — thin acquire edges → shared Import → enqueue | ✅ Done 2026-08-05 — Dim **2** + **8** |
| **C** | **13** | **UploadService** — JWT + session APIs delegate; keep both storage façades | ✅ Done 2026-08-05 — Dim **3** |
| **B** | **14** | In-process domain events (`PaperImported`, …) — handlers, not Kafka | ✅ Done 2026-08-05 — Dim **7** + **8** |
| **D** | **15** | Lightweight workflow engine (Job → Steps → Events) on existing worker | ✅ Done 2026-08-05 — Dim **2** + **8** |
| **E** | **16** | Research workflow contracts (Import / Evidence / Writing / Review / Publish) | ✅ Done 2026-08-05 — Dim **2** + **8** → Research OS |

Phase order is intentional: **spine first (A)**, then **UploadService (C)** can land in parallel or immediately after A starts; **events (B)** once call sites have a single place to emit from; **workflow engine / contracts (D–E)** after events exist.

### Closed AI bites (do not reopen for purity)

| Bite | Scope | Moves |
|------|-------|-------|
| **9** | Writing assistant → `invoke_prompt_llm` only | ✅ Done |
| **10** | JWT search/RAG embed → `invoke_query_embedding` | ✅ Done |
| **11** | Cost Ledger ← projection of AI Ledger | ✅ Done |

---

## Recently moved (changelog)

| Date | Area | Change |
|------|------|--------|
| 2026-08-05 | **Workflow contracts** | Bite 16: WF-v1.0 freeze — Import/Evidence/Writing/Review/Publication; Constitution §0.5 One Journey / One Rule |
| 2026-08-05 | **Workflow** | Bite 15: Research Workflow Engine — named steps + inspectable state; domain-event bridges + worker job notes; GET `/api/workflows/*` |
| 2026-08-05 | **Domain events** | Bite 14: sync in-process `DomainEventBus` — catalog + idempotent handlers; emit from ImportService, Evidence review, WI composer, ledger façade |
| 2026-08-05 | **Upload** | Bite 13: `UploadService` — session/JWT/bulk/presign → register + ImportService enqueue; dual storage façades retained |
| 2026-08-05 | **Discovery / Library** | Bite 12: `ImportService` spine — Discover (PubMed/arXiv/ORCID/…), Drive/OneDrive, Upload enqueue, manual attach, UFTR converge |
| 2026-08-05 | **Governance** | Strategic pivot: AI Platform freeze; next bites = Library spine Phases A–E; Workflow Completeness KPI |
| 2026-08-05 | **Cost Ledger** | Bite 11: `ledger_facade.record_platform_execution` — AI Ledger + CostLedger projection; Gateway `skip_cost_ledger` |
| 2026-08-05 | **Search** | Bite 10: JWT `/api/documents/search` + `/api/rag` retrieve → `invoke_query_embedding` + AI Ledger |
| 2026-08-05 | **Writing** | Bite 9: assistant uses `invoke_prompt_llm` only; `responses_text` fallback removed |
| 2026-08-05 | **AI Invocation** | Bite 8: `utility_engine` — compare/gaps, project research, embed, memory/titles/metadata on ACR + ledger |
| 2026-08-05 | **Governance** | AI execution coverage matrix + Bites 9–11 sequencing in Architecture Health |
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
- Infra fashion (Kafka, K8s, microservices, CQRS, event sourcing) → **rejected** until production usage demands them
