# FEATURE_MATRIX — Implemented vs planned

**Legend:** **Implemented** · **Partial** · **Planned** · **Not Implemented**  
**Last updated:** 2026-07-28  
**Rule:** “Implemented” must exist in code; design-only stays Planned.

---

## Product surfaces

| Area | Status | Notes |
|------|--------|-------|
| Authentication (Google / magic / DEV) | Implemented | Session + JWT bridge |
| Streaming chat + tools | Implemented | Web search, save_citation |
| Knowledge Library / uploads | Implemented | Dual upload APIs (debt) |
| Library Bridge 1a–1c | Implemented | Import, sync, Ready, health, dupes |
| Discover / OpenAlex | Implemented | Stubs + DOI dedup |
| Paper Workspace (Phase 1 tabs) | Implemented | Structure → Graph, Narrative, Chat |
| Analysis pipeline 1.1–1.7 + worker | Implemented | Deterministic engines + orchestration |
| Writing Studio Shell | Implemented | `v0.1.0` — autosave, versions, lifecycle |
| Evidence Platform (2.2) | Implemented | Frozen `v0.2.0-rc1` |
| Research Intelligence (2.3) | Implemented | Sprints 0–6 APIs |
| Writing Intelligence (grounded) | Implemented | `/api/evidence/writing` — generation last |
| Legacy `POST /api/writing` transforms | Partial | Not the Studio foundation |
| Citations manager | Implemented | Styles + BibTeX; insert-into-draft Planned |
| Compare / Gaps | Implemented | Cached derived analyses |
| Notes / Projects / Memory | Implemented | |
| Dashboard / ⌘K / Design System v2 | Implemented | D1–D9 |
| Closed beta ops | Implemented | Invites, support, admin metrics |
| Prompt Engine | Partial | Wired paths; Paper Chat Stage 1 off by default |
| RAG | Implemented | Simple cosine; no ANN |
| Quotas | Partial | Storage + some token paths; chat not fully gated |
| Admin UI | Partial | APIs only |
| Payments / billing | Not Implemented | SaaS-PK parallel track |
| Product analytics / Sentry | Not Implemented | |
| Notifications product | Not Implemented | Transactional email only |
| Research Reviewer | Planned | ADD-0005 Month 8 — compiler-shaped |
| Research Assistant | Planned | Evidence Query → reason → answer |
| Publication engine | Planned | Later |

---

## Research Intelligence APIs (Phase 2.3)

| Stage | Endpoint | Status |
|-------|----------|--------|
| Query contract | EvidenceQuery v0 | Frozen (ADR-0007) |
| Retrieval | `POST /api/evidence/search`, `/retrieve` | Implemented |
| Ranking | `POST /api/evidence/rank` | Implemented |
| Consensus | `POST /api/evidence/consensus` | Implemented |
| Conflict | `POST /api/evidence/conflict` | Implemented |
| Reasoning | `POST /api/evidence/reason` | Implemented |
| Writing Intelligence | `POST /api/evidence/writing` | Implemented (`grounded_v0`) |
| Explain (platform) | `POST /api/evidence/explain` | Implemented (frozen) |

---

## Module map (summary)

| Module | Level |
|--------|-------|
| Auth / Projects / Library / Bridge / Discover | Implemented |
| Paper Analysis + Phase 1 engines + Graph JSON | Implemented |
| Writing Studio Shell | Implemented |
| Evidence + RI pipeline | Implemented |
| Prompt Engine | Partial |
| Storage | Implemented (two facades) |
| Worker / Observability | Implemented |
| Payments / Notifications / Feature-flag service | Not Implemented |

---

## Naming collision

- **Analysis “Phase 1 / 2”** = engines 1.1–1.7 + `AnalysisPipelineService`  
- **Product “Phase 0 / 1 / 2.x”** = Platform → Library → Writing / Evidence / RI  

See [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md).
