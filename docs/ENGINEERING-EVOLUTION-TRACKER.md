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
| **AI Invocation** | Chat model via **Capability Router** (`resolve_chat_execution`); transport still Responses SSE. WI already Router→Gateway | Single path Router → Gateway → Provider (incl. streaming) | **High** | ADR-0016; chat bite 2026-08-05 |
| **Cost Ledger** | Dual stores; chat now writes **CostLedger + AI Ledger** provenance | **Unified AI Ledger** (one attribution story) | **High** | Don't delete half; see `ai_ledger` dual-write note |
| **Research Scope** | Gateway present (ADR-0017); chat gated | Scope enforced on all research AI entry points | **High** | ALLOW · CLARIFY · REDIRECT |
| **UFTR** | Platform service (ADR-0015) | Default path for full-text resolution across Discovery/Library | **Medium** | Shared pipeline, not per-provider forks |
| **Upload** | Dual HTTP + dual storage façades (ADR-0014) | Shared abstraction; one policy surface | **Low** | Accepted V1; unify only with ADR |
| **server.py** | Monolith (models + many routes) | Thin composition root (`create_app` / register_*) | **Medium** | Peel by blueprint; models extract = separate ADR |
| **Library** | Mixed (files, connect, storage concerns interleaved) | **Library** product domain ownership | **Medium** | Separate from Discovery |
| **Discovery** | Provider-specific clients + some shared scholarly ops | Shared **resolver / import / metadata / fulltext** pipeline; providers at edges | **Medium** | PubMed ≠ OpenAlex only at the edge |
| **Evidence** | Strong + frozen contracts | Keep growing; single research truth | **Low** (maintain) | ADR-0003 / 0005 / 0007 — don’t reopen casually |
| **Writing** | Studio + WI + bindings; reviewer FE polish | Writing domain: binder · composer · grounding · citations · exports | **Medium** | Reviewer may extract later |
| **Reviewer** | Backend persistence; FE incomplete | Clear Reviewer domain (or owned submodule of Writing) | **Medium** | Product-critical polish |
| **Research Intelligence / SUE** | Analysis packages present | Isolated RI domain (quality / methodology / …) | **Medium** | Don’t merge into Evidence |
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

## Recently moved (changelog)

| Date | Area | Change |
|------|------|--------|
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
