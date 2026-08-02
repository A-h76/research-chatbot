# FEATURE_MATRIX — Implemented vs planned

**Legend:** **Implemented** · **Partial** · **Planned** · **Not Implemented**  
**Last updated:** 2026-08-02  
**Rule:** “Implemented” must exist in code; design-only stays Planned.

---

## Product surfaces

| Area | Status | Notes |
|------|--------|-------|
| Authentication (Google / magic / DEV) | Implemented | Session + JWT bridge; step-up account delete; invite checklist (#16) |
| Streaming chat + tools | Implemented | Web search, save_citation |
| Knowledge Library / uploads | Implemented | Dual upload APIs (debt) |
| Library Bridge 1a–1c | Implemented | Import, worker sync, PDF pull; **Integrations catalog SoT** (#11) + landing honesty (#12) 2026-08-02 |
| Discover / OpenAlex | Implemented | Stubs + DOI dedup |
| Paper Workspace (Phase 1 tabs) | Implemented | Structure → Graph, Narrative, Chat |
| Analysis pipeline 1.1–1.7 + worker | Implemented | Deterministic engines + orchestration |
| Evidence Extraction Pipeline | Implemented | Sync API + worker; quality `phase_projector.v1.1` (claim norm + facets + study_type); High backlog closed 2026-08-02 |
| Writing Studio Shell | Implemented | V1 Ready 2026-08-03 (#2 — autosave/versions/lifecycle; DocumentBlock out of V1) |
| Evidence Platform (2.2) | Implemented | Frozen `v0.2.0-rc1`; V1 Ready 2026-08-03 (#1 — quality + Compare UX on existing RI APIs) |
| Research Intelligence (2.3) | Implemented | Sprints 0–6 APIs |
| Writing Intelligence (grounded) | Implemented | `grounded_v1` + binder alignment + `accept_allowed` fail-closed + Verify/export gates (V1 Production Ready 2026-08-02) |
| Evidence Discovery | Planned | Milestone 2 |
| Research Session | Planned | Orchestration (not knowledge store) |
| RI Inspector enrichment | Implemented | Consensus / conflict / reason in Writing Inspector |
| Legacy `POST /api/writing` transforms | Partial | Labeled **style only** — not evidence-backed |
| Citations manager | Implemented | Styles + BibTeX; insert-into-draft (Writing picker + resolve-evidence + bindings) V1 Ready 2026-08-02 |
| Compare / Gaps | Implemented | Matrix/Gaps/AI Compare + RI consensus/conflict strip (#1); cached derived analyses |
| Notes / Projects / Memory | Implemented | Personal projects V1 Ready 2026-08-03 (#19 hub empty/error + ownership IDOR); sharing/teams out of V1 |
| Dashboard / ⌘K / Design System v2 | Implemented | D1–D9 |
| Closed beta ops | Implemented | Invites, support, admin metrics |
| Prompt Engine | Partial | Wired paths; Paper Chat Stage 1 off by default |
| RAG | Implemented | Simple cosine; no ANN |
| Quotas | Implemented | EntitlementService; chat / WI / extract gated; soft≥80% / hard 100%; admin overrides + analytics (#13) |
| Feature flags | Implemented | DB `feature_flags` + FeatureFlagService; admin toggle; Discover + WI gated (#14) |
| Admin UI | Implemented | `/admin` SPA — invites, AI kill switch, beta metrics, security events, flags (#15) |
| Payments / billing | Not Implemented | SaaS-PK parallel track |
| Product analytics / Sentry | Partial | Optional `SENTRY_DSN` → `security/sentry_init.py` (#20); product analytics UI still out |
| Notifications product | Not Implemented | Transactional email only |
| Research Reviewer | Implemented | Durable runs + FE severity accordion + export gate on severity=error (V1 Production Ready 2026-08-02) |
| Grounded Writing Trust Vertical (Alpha Gate) | Implemented | Eng Success Gate PASS 2026-08-02 — `test_grounded_writing_vertical` + `PRIVATE_ALPHA_SUCCESS_GATE_v1.md`; human invite cohort ops follow-up |
| Research Assistant | Planned | Evidence Query → reason → answer |
| Publication engine | Planned | Later |

**Naming:** Paper “Evidence” tab = Phase 1.5 GRADE grading. RI EvidenceObjects live under Writing Inspector / Evidence Platform — not the same surface.

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
| Writing Intelligence | `POST /api/evidence/writing` | Implemented (`grounded_v1`, Gateway + Reviewer + Verify + server-gated MD/BibTeX export #18) |
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
| Storage | Implemented (two facades) | Dual stack accepted V1 — ADR-0014 |
| Worker / Observability | Implemented | Heartbeat `/api/worker/health`; extract_metadata drain shim (#17) |
| Payments / Notifications | Not Implemented |
| Feature-flag service | Implemented | #14 — Discover + Writing Intelligence |

---

## Naming collision

- **Analysis “Phase 1 / 2”** = engines 1.1–1.7 + `AnalysisPipelineService`  
- **Product “Phase 0 / 1 / 2.x”** = Platform → Library → Writing / Evidence / RI  

See [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md).
