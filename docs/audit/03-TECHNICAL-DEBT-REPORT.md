# Technical Debt Report

**Product:** Dhund Research OS  
**Audit date:** 2026-08-02  
**Purpose:** Duplicate stacks, dead schema, incomplete APIs, V1 shortcuts, redesign-before-scale areas.

**Related:** [01-CURRENT-ARCHITECTURE-AUDIT.md](01-CURRENT-ARCHITECTURE-AUDIT.md) · [02-PRODUCT-COMPLETION-AUDIT.md](02-PRODUCT-COMPLETION-AUDIT.md) · [04-RESEARCH-OS-ROADMAP.md](04-RESEARCH-OS-ROADMAP.md)  
**Living register:** also see `Dhund-Flow/TECHNICAL_DEBT.md` (keep both aligned when fixing items).

---

## 1. Severity legend

| Severity | Meaning |
|----------|---------|
| **Critical** | Blocks scale, trust, or correct ops if ignored |
| **High** | Structural dual paths / cost / abuse risk |
| **Medium** | Schema-ahead, stale docs, incomplete unify |
| **Low** | Hygiene, naming, unused helpers |

**Rule:** No big-bang rewrites. Prefer ADRs + incremental façades. Respect PLATFORM_FREEZE / RI freezes.

---

## 2. Structural debt (High) — dual stacks

| Debt | Stack A | Stack B | Risk | Recommended action |
|------|---------|---------|------|--------------------|
| Storage | `storage/` | `backend/storage/` | Divergent validation / providers | **V1 accepted** ([ADR-0014](../adr/0014-upload-storage-dual-stack-accepted-v1.md)); unify ADR later |
| Upload APIs | Session `POST /api/files` | JWT documents / bulk / presign | Two policies | **V1 accepted** (ADR-0014); keep shared `UploadJob` |
| Search | Session `/api/search` | JWT `/api/documents/search`, `/api/rag` | Client confusion | Document + converge clients |
| AI invoke | `server.py` Responses SSE chat | ModelRegistry Completions (WI) | Dual cost/attribution | Thin Responses executor or finish Prompt Engine migration |
| Cost ledgers | Legacy usage | Registry / Prompt Engine ledger | Billing lies | Consolidate write sites |
| Discover import | Direct OpenAlex calls | `OpenAlexAdapter` exists | Bypass adapter policy | Route through adapter |

Both upload stacks enqueue the same worker jobs — debt is **entry**, not queue.

---

## 3. Dead / zombie / schema-ahead

| Item | Location | Status | Action |
|------|----------|--------|--------|
| `feature_flags` table | `migrations/0008_feature_flags.sql` | **Resolved #14** — `FeatureFlagService` + admin API; Discover + WI gated | Keep extending known flags |
| `SearchIndex` | `server.py` model | Never populated | Wire or deprecate |
| `ImportSession` | model + migration 0003 | Unused checkpoints | Implement resume **or** drop |
| `get_work_by_doi` unused | `backend/scholarly/openalex.py` | Dead helper | Wire or delete |
| `ImportAdapter.import_files` | `backend/library/adapters/base.py` | `NotImplementedError` Phase 1b | Implement (product gap, not dead) |
| `extract_metadata` job | `worker.py` HANDLERS | **Resolved #17** — drain shim → `phase1_analysis` (no LLM) | Remove HANDLER entry after prod queue shows zero pending |
| `send_research_complete` | email events | No/few callers | Wire to job complete **or** remove |
| Paper Chat Stage 1 | `backend/ai_core/paper_chat/` | Off by default | Soak then enable or cut |
| Persona seed TODOs | `backend/ai/seed.py` | Placeholder prompts | Fill or trim catalog |
| Brand remnants | docs / mailto / templates | Soro / Personal AI / ResearchOS | Sweep naming |

---

## 4. Incomplete APIs & surfaces

| API / surface | Completeness | Gap |
|---------------|--------------|-----|
| `/api/admin/ops/*` | Backend complete | No Admin SPA |
| Reviewer reconstruct routes | Backend complete | FE unused |
| Library sync routes | Works in-request | No worker HANDLER; no PDF pull |
| `/api/writing` style transforms | Complete as style-only | Product confusion vs WI |
| Quotas | Partial | Chat/WI not fully gated |
| Feature flags | **Implemented (#14)** | Evaluation + admin API + Discover/WI gates |
| Billing | Design only | No routes |
| Public developer API | Absent | First-party only |
| External webhooks | Absent | Outbox is internal |
| `/trust` marketing | Absent | SPA catch-all → home |

---

## 5. TODOs / FIXMEs / hacky shortcuts

### Inline code TODOs (sparse — good)

| Finding | Path |
|---------|------|
| Naive token-overlap memory (no embeddings) | `backend/ai/memory_engine.py` |
| Persona / seed placeholders | `backend/ai/seed.py` (historical) |

App code is relatively clean of scattered FIXME noise. Debt lives in **architecture dualism** and **Dhund-Flow** registers — prefer fixing there over sprinkling markers.

### V1 shortcuts (acceptable if documented)

| Shortcut | Why taken | When to revisit |
|----------|-----------|-----------------|
| Personal-only AuthZ | Closed beta | Before teams |
| Env feature flags | Speed | Before risky public rollouts |
| Style transforms beside WI | Keep useful editor tools | Label forever; never call “grounded” |
| Chat demoted but not deleted | Users still need Q&A | Evidence Assistant later |
| Evidence Engine → Evidence Layer rename | ADR collapse | Done — don’t resurrect old name |
| In-request library sync | Ship Bridge faster | Before large libraries / prod SLA |
| itsdangerous sealed tokens (`enc:v1:`) | Adequate for beta | Enterprise → stronger crypto ADR |
| O(n) cosine RAG | Avoid pgvector early | Before 10k chunks / user |
| Jinja mega-landing + separate auth templates | Ship marketing | Consolidate UX (Medium) |

### Hacky / fragile patterns

| Pattern | Concern |
|---------|---------|
| `server.py` monolith owning models | Import constraint; hard to navigate |
| JSON embeddings in Text columns | Matches constitution; scales poorly |
| Discover bypassing adapter | Soft-fail policy drift |
| Dual auth (session vs JWT) on neighboring routes | Easy to wire wrong decorator |
| ClamAV optional in non-prod | Don’t ship prod with `CLAMAV_OPTIONAL=1` by accident |

---

## 6. Legacy architecture & obsolete files

| Area | Notes |
|------|-------|
| Constitution dual storage | Documented intentional debt — not accidental copy-paste |
| Celery | Explicitly rejected (ADR-001); docs mentioning Celery are obsolete |
| Target.md ADR numbers | Partially superseded by Evidence/RI ADRs 0003–0007 |
| PRODUCTION_READINESS migration “through 0033” | Doc drift — migrations exist through **0038** |
| FEATURE_MATRIX Reviewer = “Planned” | Stale — BE Partial; update when convenient |
| Some public-saas docs claiming lit-review “not built” | Stale vs WI path |

---

## 7. Unused / thin frontend components

| Item | Notes |
|------|-------|
| `writingStore` / `useWritingWorkspace` | Removed 2026-08-03 (#2) — shell state lives in `WritingPage.tsx` |
| Paper tab placeholders | Unfinished paper tabs |
| Settings “API” section | Informational (server `.env` key), not product API keys |
| Writing raw `fetch` vs shared API client | Called out in DevB reviews |

Prefer unused-export tooling for a full dead-component pass; do not mass-delete without product confirmation.

---

## 8. Security concerns

| Concern | Severity | Mitigation |
|---------|----------|------------|
| Open signup + empty `ALLOWED_EMAILS` | Critical on public | Keep `BETA_INVITE_ONLY` or populate allowlist |
| `DEV_AUTO_LOGIN` in prod | Critical | Startup fail-closed; verify deploy env |
| Account delete without step-up | **Resolved #16** | Password or email reauth + `DELETE` confirm |
| Prompt injection via PDF text | Medium (accepted residual) | Keep grounded paths fail-closed |
| Token seal ≠ AES-GCM | Medium | ADR before enterprise |
| Multi-worker rate limits without Redis | Medium | Redis limiter in prod |
| No Sentry | Medium | Add before open alpha traffic |
| Worker LLM cost vs chat limiter | Medium | Apply AI gate per job type |

---

## 9. Performance issues

| Area | Issue | Scale trigger |
|------|-------|---------------|
| RAG / semantic search | O(n) cosine over all user chunks | Thousands of chunks |
| PDF import | Full document in memory | Large PDFs / bulk |
| Library sync HTTP | Request timeout | Large Zotero libraries |
| Hub queries | Capped (good) | Keep caps; watch N+1 |
| Analysis pipeline | Sync analyze endpoints | Prefer worker for heavy |

---

## 10. Missing tests (notable gaps)

| Area | Gap |
|------|-----|
| Onboarding e2e | Wizard exists; little CI e2e |
| Reviewer FE | Persistence BE tested; FE reconstruct unused |
| Library `import_files` | Tests assert NotImplemented — need positive tests when built |
| Quota on chat SSE | Partial coverage vs Feature Matrix claim |
| Admin SPA | N/A until built |
| Private Alpha Success Gate | Product validation, not unit tests |

Strong coverage exists for Evidence freeze, upload/magic-bytes, library sync metadata, writing shell unit paths.

---

## 11. Areas that should be redesigned before scaling

| Area | Why redesign-before-scale | Approach |
|------|---------------------------|----------|
| Retrieval | O(n) JSON embeddings | ADR → pgvector / ANN; populate or kill `SearchIndex` |
| AuthZ | Ownership-only | Org RBAC ADR before teams |
| Cost attribution | Dual ledgers | Single write path before paid plans |
| Upload entry | Dual stacks | Façade ADR |
| Chat vs Evidence Query | Dual answer paths | Evidence-required assistant mode |
| `server.py` models | Monolith constraint | Extract models package only with ADR |
| Library sync | In-request | Worker HANDLER (extend existing pattern) |

**Do not redesign:** EvidenceObject envelope, RI stage contracts, Writing shell tables, Postgres SKIP LOCKED queue, `ImportAdapter` interface.

---

## 12. Debt priority for next engineering cycles

1. **Document + decide** schema-ahead (`feature_flags`, `SearchIndex`, `ImportSession`) — implement or deprecate.  
2. **Worker library sync + PDF import** — durability before logo integrations.  
3. **Quota gate chat/WI** — cost abuse.  
4. **Reviewer FE + citation insert** — product trust (also in roadmap P0).  
5. **ADR thin façade** for storage/upload (no big-bang).  
6. **Sentry + doc sync** (migrations, Feature Matrix Reviewer status).  
7. **Defer** orgs, public API, Celery, Neo4j, Research Session until Alpha validates.

---

## 13. Summary

Most debt is **intentional dual-path architecture** and **paused SaaS surfaces**, not abandoned half-files. The dangerous debts for V1→scale are: **ungated chat cost**, **in-request sync**, **O(n) retrieval**, **unused feature_flags illusion**, and **ungrounded chat competing with Evidence**. Fix by finishing freezes and extending existing interfaces — not by rewriting the Research OS core.
