# Architecture Health

**Status:** Living KPI sheet — rescore when Evolution Tracker rows move.  
**Date opened:** 2026-08-05  
**Type:** Measurable architecture health (not product OKRs, not aesthetic cleanliness)  
**Companions:** [`ENGINEERING-CONSTITUTION-v1.md`](ENGINEERING-CONSTITUTION-v1.md) · [`ENGINEERING-EVOLUTION-TRACKER.md`](ENGINEERING-EVOLUTION-TRACKER.md) · [`00-constitution.md`](00-constitution.md)

**Intent:** Score whether Dhund is becoming a replaceable, inspectable **engineering platform** — the same picture for every engineer.

**Higher scores do not imply more abstraction.** Higher scores imply **fewer competing implementations of the same responsibility**. Do not extract interfaces or merge folders for appearance.

---

## Strategic pivot (post Bite 11)

**AI Platform is no longer the highest-leverage architectural risk.**

Canonical AI path is in place:

```text
Research Job → Capability Router → Gateway → AI Ledger → Artifact
```

**Do not chase 100% AI purity** — ROI drops sharply. Maintain the path; do not add abstraction layers for residual shims (`responses_text`, gateway embed adapter) unless a product change forces it.

**Biggest remaining weakness:** Dimensions **2**, **3**, and **8** — acquisition / import / upload / UFTR / worker / evidence still have multiple entry points with little differences.

**Invest next:** Maintain Library spine; close remaining thin-edge gaps (Zotero/BibTeX → ImportService). Product focus over architecture % chasing.  
Workflow contracts frozen: [`docs/contracts/WF-v1.0-COMPLETE-FREEZE.md`](contracts/WF-v1.0-COMPLETE-FREEZE.md).

**Explicitly out of scope for now:** CQRS · Kafka · microservices · event sourcing · Kubernetes · graph DBs (until Knowledge Graph is a real product).

---

## Scoring scale (per dimension)

| Score | Meaning |
|-------|---------|
| **1** | Missing / contradictory |
| **2** | Partial; dual paths or unclear ownership |
| **3** | Mostly true in the hot path; gaps named |
| **4** | Solid; exceptions rare and documented |
| **5** | Default path; swapping / testing / provenance routine |

**Overall** = average of the **eight** dimensions (report to 1 decimal).

---

## Dimensions

### 1. Capability ownership

> Every **capability** has one owner — not every folder.

Packages move; capabilities survive. Example: **Evidence** owns extraction, review, and bindings — regardless of whether that lives in `backend/evidence/` today or splits tomorrow.

| Check | Pass looks like |
|-------|-----------------|
| PR names the Platform Layer or Product Domain **capability** it extends | Reviewer can answer “who owns this?” |
| New code location predictable from constitution + Evolution Tracker | No circular ownership |
| No orphan `utils.py` growth | Shared code under `shared/<concern>/` |
| Owns / Does not own documented | README or package docstring on touched areas |
| ADR matches where code actually lives | Drift flagged (see Architectural drift) |

**Simplicity signal (cognitive load):** Can a new engineer predict where new code belongs? If not, score ≤ 3 until boundaries are clarified.

**Baseline (2026-08-05):** **3** — many `backend/*` packages exist; `server.py` still mixed; dual stacks blur Library/Storage.

---

### 2. Canonical pipelines

> One **execution pipeline** per research journey — providers differ only at the edges.

Not “shared code somewhere.” A named spine everyone uses:

```text
Discovery → Import → UFTR → SUE → Evidence → Writing
```

Target acquisition spine (Library):

```text
Acquire → ImportService → UploadService → UFTR → enqueue_import → Worker → Evidence
```

| Check | Pass looks like |
|-------|-----------------|
| Connectors converge on `enqueue_import` (or documented successor) | PubMed / Drive / OneDrive → same spine |
| Full-text via UFTR | No per-provider fulltext forks |
| Analysis → evidence → writing | Worker queue + canonical engines |
| Connectors don’t reimplement accept/store policy | Policy in Library / Trust / upload service |

**Baseline:** **4.5** — Bite 16: WF contracts + Constitution §0.5 (One Journey / One Rule); pipeline named end-to-end. Zotero/BibTeX metadata still on LibraryImportService.

---

### 3. Business logic has a single implementation

> Every business rule exists in exactly one place — not “one endpoint,” not “one folder.”

**Not the goal:** delete duplicate code for aesthetics.  
**The goal:** one canonical implementation per rule; every caller delegates to it.

| Check | Pass looks like |
|-------|-----------------|
| Same rule (attach PDF, import, extract, AI call) | One function/service; providers/APIs call it |
| Second implementation introduced | ADR + retirement plan, or reject |
| Two HTTP APIs (JWT + session) | Fine — if both call `UploadService` |
| Two providers (PubMed, arXiv) | Fine — thin edges; canonical pipeline after acquisition |

**Duplication map (post Bite 11):**

| Rule | Canonical path | Still duplicated |
|------|----------------|------------------|
| Hot LLM execution | `resolve_*` → `invoke_*` / `execute_*` → Gateway → ledger façade | Legacy `responses_text` / direct registry (maintain only) |
| Import → analysis → evidence | **ImportService** → UFTR / `attach_pdf_bytes` → enqueue `import` | Zotero/BibTeX metadata still via `LibraryImportService` (same stub shape) |
| Upload accept/store | **UploadService.register** (+ Session/Jwt StorageFacade) | Dual storage *folders* remain (ADR-0014) — OK |
| Cost / attribution | `record_platform_execution` (AI Ledger → CostLedger projection) | Legacy paths only |

**Score 4/5 when (not perfection):**

- ✅ Every AI feature routes **Capability Router → Gateway** (utility/embed on maintain list).
- ⬜ Every connector uses the **same import pipeline** after acquisition (`enqueue_import` → SUE → Evidence).
- ⬜ Full-text via **shared UFTR**, not per-provider forks.
- ✅ Evidence / SUE / Writing / Reviewer: **one canonical implementation** per rule on hot paths.
- ✅ Multiple APIs/providers **delegate** to UploadService / ImportService — not reimplement (upload done; Zotero/BibTeX metadata remaining).

**5/5** = intentional dual paths retired; single implementation is the default everywhere.

**PR gate:** Does this PR introduce a **second implementation** of an existing business rule? If yes → require **why**, **temporary?**, **ADR?**, **retirement plan?** — otherwise reject.

**Does not reduce this score:** two APIs, two frontends, two providers at the edge — as long as they call the same service. **Do not merge** `storage/` and `backend/storage/` folders — converge on UploadService instead.

**Baseline:** **3.75** — UploadService owns register policy; storage façades remain dual by ADR.

---

### 4. Single source of truth

> Evidence. Ledger. Research Jobs. One truth each.

| Truth | Current | Target |
|-------|---------|--------|
| Research claims for writing | Evidence objects (+ contracts) | Keep — do not fork |
| AI cost / attribution | AI Ledger owns execution; CostLedger = projection | Legacy paths only |
| Async work | `upload_jobs` + outbox (Postgres) | Keep — Redis cache only |

**Baseline:** **4.0** — Bite 11 ledger façade; `ai_usage_ledger` reconciliation still separate.

---

### 5. Replaceability

> Can any **infrastructure dependency** be replaced without changing product logic?

Not only LLM providers. Product code should not care which implementation sits behind an interface.

| Dependency class | Pass looks like |
|------------------|-----------------|
| LLM (OpenAI, Anthropic, Gemini, …) | Capability Router → Gateway → Provider; no SDK in features |
| Storage (local, R2, S3) | Swappable backend; policy in one service |
| Cache (Redis) | Optional; Postgres remains source of truth |
| Vector / embed store | Behind gateway or documented adapter |
| Model selection | Policy-driven (registry / router), not hardcoded |

**Baseline:** **4** — Hot LLM paths on Router → Gateway; storage dual façades remain (see Dimension 3).

---

### 6. Testability

> Every major platform layer has independent tests.

| Check | Pass looks like |
|-------|-----------------|
| Layer tests without full monolith when possible | `backend/*/test_*.py`, contracts |
| Real Postgres for integration (constitution) | CI + local |
| Worker/queue behavior tested | Job claim / handlers |

**Baseline:** **4** — good coverage on hot paths; monolith coupling remains in places.

---

### 7. Inspectability

> The full chain from user action to artifact is traceable — not only AI calls.

```text
User action → Workflow event → Research decision → Artifact → Evidence → AI Ledger
```

| Check | Pass looks like |
|-------|-----------------|
| Evidence spans / confidence / bindings | Inspectable UI + API |
| AI jobs / WI drafts | Ledger + hashes where required (RI-009) |
| Workflow / research decisions | Append-only trails |
| Async jobs | `upload_jobs` status + outbox provenance |
| End-to-end link | Can answer “why does this draft cite this span?” |

**Baseline:** **4.7** — Bite 14: sync DomainEventBus + structured `domain_event` logs on canonical emit sites (Import / Evidence / Writing / AI Ledger). Complementary to durable outbox contract events.

---

### 8. Workflow Completeness

> Can this entire research journey be described by **one canonical workflow**?

```text
Discover → Import → UFTR → SUE → Evidence → Writing → Review → Publish
```

| Score | Meaning |
|-------|---------|
| **1** | Multiple competing workflows |
| **3** | Mostly shared spine; some forks |
| **5** | Every entry point converges on the same workflow |

| Check | Pass looks like |
|-------|-----------------|
| Upload, Drive, OneDrive, Zotero, PubMed, arXiv, EuropePMC, manual attach | Thin acquire edges → same Import → Upload → UFTR → worker → Evidence |
| Writing / Review / Publish | Named pipeline contracts (WF-003–005) — frozen like RI |
| New connector PR | Adds a provider edge only — does not invent a parallel pipeline |

This KPI measures what Dimensions 2–3 only capture indirectly: **journey-level convergence**, not just “one function exists somewhere.”

**Baseline:** **4.5** — Bite 16: Import / Evidence / Writing / Review / Publication contracts freeze the journey; engine + domain events already inspect steps.

---

## Scorecard (post Bite 16 · Library-spine era)

| # | Dimension | Score |
|---|-----------|-------|
| 1 | Capability ownership | 3 |
| 2 | Canonical pipelines | 4.5 |
| 3 | Business logic — single implementation | 4.0 |
| 4 | Single source of truth | 4.0 |
| 5 | Replaceability | 4 |
| 6 | Testability | 4 |
| 7 | Inspectability | 4.7 |
| 8 | Workflow Completeness | 4.5 |
| | **Overall** | **4.2 / 5** |

*Bite 16 raised Dim 2, 3, 8 after Research Workflow Contracts + Constitution §0.5. Library-spine Phases A–E complete.*

*Narrative constitution score (~8.5/10 product+doctrine maturity) ≠ this KPI.*

### Expected progression (Library-spine era)

| Milestone | Expected overall | What moves |
|-----------|------------------|------------|
| Post Bite 11 | ~3.5 (8 dims) | AI freeze; Workflow Completeness named |
| Bite 12 ImportService | ~3.7 | Dim 2 + 3 + 8 ↑ |
| Bite 13 UploadService | ~3.8 | Dim 3 + 8 ↑ |
| Bite 14 domain events | ~3.9 | Dim 7 + 8 ↑ (sync bus; not Kafka) |
| Bite 15 workflow engine | ~4.0 | Dim 2 + 8 ↑ — named steps + inspect |
| **Bite 16 workflow contracts (now)** | **~4.2** | Dim 2 + 3 + 8 → Research OS contracts |

**Aim met:** Overall **≥ 4.0 / 5** without a rewrite. Maintain; do not chase AI purity or folder aesthetics.

---

## AI execution coverage (maintain checklist)

Companion to Dimension 3 — **Bites 1–11 complete.** Treat as a **maintain** checklist, not an active migration board. Update only if a new AI entry point ships or a shim is forced by product work.

| AI entry point | ACR | Gateway | AI Ledger | Status |
|----------------|:---:|:-------:|:---------:|--------|
| Chat (`/api/chat`) | ✅ | ✅ | ✅ | Complete |
| Writing assistant | ✅ | ✅ | ✅ | Complete |
| WI composer | ✅ | ✅ | ✅ | Complete |
| Reviewer | ✅ | ✅ | ✅ | Complete |
| Evidence extract | ✅ | ✅ | ✅ | Complete |
| Paper analysis / SUE | ✅ | ✅ | ✅ | Complete |
| Search RAG (`POST /api/rag`) | ✅ | ✅ | ✅ | Complete |
| Compare / gap finder | ✅ | ✅ | ✅ | Complete |
| Project research | ✅ | ✅ | ✅ | Complete |
| Metadata / memory / title | ✅ | ✅ | ✅ | Complete |
| Embeddings (chunk + session + retrieve + JWT) | ✅ | ⚠️ | ✅ | Maintain — gateway embed adapter deferred |
| Upload analysis (worker) | ✅ | ✅ | ✅ | Complete |

**Legend:** ✅ = on canonical path · ⚠️ = partial / shim (acceptable debt) · ❌ = bypass

**Guardrail:** Do not grow `utility_engine.py` into a second monolith. Do not open ADR-0016 v1.1 job promotions unless a product feature needs them.

---

## What does NOT improve the score

| PR change | Score impact |
|-----------|--------------|
| `backend/library/` → `backend/library2/` (rename only) | **0** — no behavior change |
| New abstraction layer with no call-site convergence | **0 or down** — more surface, same dual paths |
| PubMed + OpenAlex both call `enqueue_import()` | **+** — business rule became canonical |
| Second HTTP stack that reimplements upload policy | **down** — second implementation |
| Folder tidy with ADR but no retirement plan for old path | **0** until old path is gone or documented |
| Gateway embed adapter / `responses_text` retirement for purity | **~0** — AI path already canonical; defer |
| CQRS / Kafka / microservices / event sourcing / K8s | **0 or down** — out of scope; increases surface without journey convergence |

---

## Architectural drift (ongoing check — not a separate score)

> Is the implementation still following the ADR and contracts?

| Drift signal | Action |
|--------------|--------|
| New bypass around Capability Router / Gateway | Block or ADR + retirement plan |
| New acquisition path that skips Import/Upload spine | Block — Dimension 2/8 |
| Duplicate pipeline for same journey | Merge to canonical spine or score Dimension 2/3/8 down |
| ADR says X; code does Y | Fix code or supersede ADR — do not let both stand |
| Contract test fails | Score may drop on Single source of truth or Inspectability |

**Score increases when:** call sites converge · ADR and code agree · contracts stay green.  
**Score decreases when:** hidden special cases · undocumented shims · “architecture on paper.”

Review drift on major PRs and when rescoring.

---

## How to rescoring

1. Only change scores when **behavior** changed (tests, call sites, contracts) — not folder renames.  
2. Note the PR / date under Changelog.  
3. If a score drops, require a one-line cause on the Evolution Tracker.  
4. Check **Architectural drift** before bumping any dimension.

### Changelog

| Date | Overall | Note |
|------|---------|------|
| 2026-08-05 | 4.2 / 5 | Bite 16: WF-v1.0 contracts + Constitution §0.5 One Journey / One Rule; Dim 2→4.5, 3→4.0, 8→4.5 |
| 2026-08-05 | 4.0 / 5 | Bite 15: Research Workflow Engine — Import→UFTR→SUE→Evidence→Writing→Review; Dim 2→4.0, 8→4.0 |
| 2026-08-05 | 3.9 / 5 | Bite 14: sync DomainEventBus — PaperImported / EvidenceAccepted / WritingGenerated / ResearchDecisionRecorded / AIExecutionCompleted; Dim 7→4.7, 8→3.5 |
| 2026-08-05 | 3.8 / 5 | Bite 13: UploadService — session/JWT/bulk/presign converge; Dim 3→3.75, 8→3.25 |
| 2026-08-05 | 3.7 / 5 | Bite 12: ImportService spine — Discover/Drive/Upload/attach/UFTR converge; Dim 2→3.5, 3→3.5, 8→3.0 |
| 2026-08-05 | 3.5 / 5 | **Strategic pivot:** AI Platform freeze; Dim 8 Workflow Completeness added (2.5); 8-dim rebase; next lever = Library spine |
| 2026-08-05 | 3.7 / 5 | Bite 11: `ledger_facade` — AI Ledger owns execution; CostLedger = projection (7-dim scorecard) |
| 2026-08-05 | 3.6 / 5 | Bite 8: utility shims on ACR — compare, project research, embed, memory/titles |
| 2026-08-05 | 3.7 / 5 | KPI #3 reframed: single implementation (not delete duplicate code); score 2.5; PR gate added |
| 2026-08-05 | 3.6 / 5 | Search RAG on ACR — Bites 1–7 complete for hot LLM paths |
| 2026-08-05 | 3.5 / 5 | SUE paper_analysis on ACR + Gateway + ledger; phase1 pipeline ledger |
| 2026-08-05 | 3.4 / 5 | Evidence extract on ACR + ledger — Single source of truth for platform executions inching up |
| 2026-08-05 | 3.3 / 5 | Reviewer on ACR + ledger (deterministic, no LLM) — Inspectability up |
| 2026-08-05 | 3.2 / 5 | Writing Assistant ACR + ledger; WI composer trace_id — Replaceability inching up |
| 2026-08-05 | 3.1 / 5 | Gateway owns chat Responses streaming — Replaceability + Testability bump; utility `responses_text` still direct |
| 2026-08-05 | 3.0 / 5 | Chat ACR model resolve + AI Ledger on done — Replaceability/Inspectability improved qualitatively; overall held at 3.0 until Gateway owns streaming |
| 2026-08-05 | 3.0 / 5 | Baseline at Engineering Constitution freeze |

---

## Anti-gaming

- Renaming packages without moving ownership → **no score change**  
- Deleting one ledger half without consolidating writes → **score may drop**  
- Adding a second queue “for clarity” → **fails** Single source of truth + Master ADR-0001  
- Extracting interfaces everywhere without converging call sites → **no score change** (see principle above)  
- Two APIs / two providers / two frontends → **fine** when all delegate to one implementation (Dimension 3)  
- Polishing AI shims after Bite 11 → **no material score change** — invest in Library spine instead
