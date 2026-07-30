# 05 — Migration Roadmap

**Goal:** Minimise refactoring, maximise long-term scalability.  
**Principle:** Extend interfaces (`Importer`, `StorageProvider`/`StorageBackend` façade, `HANDLERS`, Evidence APIs) — no rewrites without ADR.

> **Naming note (2026-07-30):** Product **Phase 2** is now [Research Intelligence](../docs/roadmap/PHASE-2-RESEARCH-INTELLIGENCE.md) (capability tickets RI-001…009).  
> Phases below are the older *architecture consolidation* sequence. Prefer product Phase 2 for planning; only pull architecture items when an RI capability needs them.

---

## Phase 1 — No breaking changes (now → near-term)

**Objective:** Make the current architecture *safe to build on*.

| Work item | Action | Outcome |
|-----------|--------|---------|
| Publish this Now-Status pack | Docs only | Shared truth for eng/product |
| Refresh Evidence/RI contracts | Docs | **Done (A-402/A-405)** — SoT is `docs/contracts/` (`contracts_version` 1.2.0); legacy `docs/api-contract.md` banners there |
| Refresh `docs/database-design.md` for evidence/writing/library | Docs | Onboarding (+ A-404 Redis note) |
| Align Phase 2 roadmap status with shipped writing/reviewer | Docs | Kill plan/code skew |
| Route SPA authenticated `fetch` through `apiClient` | Frontend | Consistent 401 |
| Add writing + evidence keys to `queryKeys.ts` | Frontend | Cache coherence |
| Progressive marketing already shipped | — | Keep separate from SPA |
| Guardrails: lint/CI note on `import server` in packages | DX | Prevent regression |
| Bootstrap runbook one-pager (create_all → migrate) | Ops | Reduce prod footguns |

**Forbidden in Phase 1:** schema renames, Celery, new Claim root, merging storage with behavior change, deleting dual upload routes.

**Exit criteria:** Engineers can answer “where is the contract?” from Now-Status + ADRs without reading all of `server.py`.

---

## Phase 2 — Extensions (evolutionary) — *architecture track*

**Objective:** Reduce dual stacks and harden trust — still additive to clients.  
**Defer** large items unless blocked on shipping [Research Intelligence](../docs/roadmap/PHASE-2-RESEARCH-INTELLIGENCE.md).

| Work item | Action | Notes |
|-----------|--------|-------|
| Extract `files` + `writing` HTTP into blueprints | **REFACTOR** | Same URLs/payloads; wire in `server.py` |
| `LibraryUploadService` façade | **MERGE** | Session + JWT routes call one service |
| Storage façade over `storage/` + `backend/storage/` | **MERGE** | One interface, adapters remain |
| Unified retrieval service | **MERGE** | Session search + JWT search/RAG share core |
| Persist `ReviewerResult` snapshots | **DONE (A-401)** | `reviewer_runs` / `reviewer_findings` + reconstruct APIs |
| Expand `PromptExecution` / cost coverage to chat SSE | **EXTEND** | Constitution §5 |
| Project-level evidence graph view | **EXTEND** | Derived from EvidenceObjects — no new graph DB |
| Deprecate or populate `search_index` | **DEPRECATE**/decide | ADR if remove |
| Soft-delete / GC polish for library | **EXTEND** | Existing storage GC patterns |

**API policy:** Additive JSON fields only; mark deprecated fields in docs for ≥1 release.

**Exit criteria:** One upload mental model; Reviewer audits durable; `server.py` thinner by ≥ writing + files routes.

---

## Phase 3 — Future modules (post-soft-launch)

**Objective:** Scale Research OS without abandoning the spine.

| Module | Approach |
|--------|----------|
| `/trust` marketing + API narrative | Explain retrieval, verification, AI allow/deny, privacy |
| Journal Submission Toolkit | Export packs (DOCX/LaTeX/BibTeX) from bindings |
| Citation Intelligence | Extend ranking/consensus — still EvidenceObject-backed |
| Research Gap Detection | Productize `research_gap` section + compare APIs |
| pgvector / dedicated ANN (optional) | **New ADR** if cosine-over-JSON hits scale wall |
| Split Evidence engines to services | Only after modular monolith proves boundaries (ADR-0003 consequence) |
| Teams / shared projects | New tenancy model + ADR |
| Billing (JazzCash / plans) | Parallel SaaS-PK track |
| Full “six-engine” Evidence Platform | Long-term vision — not next sprint |

**Still forbidden without ADR:** Celery cutover, parallel knowledge stores, Chat-as-SoT.

---

## Suggested sequencing diagram

```text
Phase 1 (stabilize)
  Docs + frontend fetch hygiene + contract visibility
        │
        ▼
Phase 2 (consolidate)
  Blueprint extract → upload/storage/search façades → reviewer persistence
        │
        ▼
Phase 3 (expand)
  Trust · export toolkit · optional vector · tenancy/billing
```

---

## Effort vs risk matrix (guidance)

| Item | Effort | Risk if skipped |
|------|--------|-----------------|
| Contract docs (P1) | Low | High — accidental breaks |
| Blueprint extract (P2) | Medium | Medium — velocity tax |
| Upload façade (P2) | Medium | High — dual-bug surface |
| Reviewer persistence (P2) | Low–Med | High for trust narrative |
| pgvector (P3) | High | Low until corpus scale |
| Celery rewrite | Very high | **Negative ROI** — ADR forbids casually |

---

## Success metric for this roadmap

> New Research OS features ship by **extending EvidenceObject + EvidenceQuery + HANDLERS**, not by adding bypass pipelines or duplicate tables.

If a proposal needs a bypass, it needs an ADR — and should usually be rejected.
