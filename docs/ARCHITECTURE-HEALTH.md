# Architecture Health

**Status:** Living KPI sheet — rescore when Evolution Tracker rows move.  
**Date opened:** 2026-08-05  
**Type:** Measurable architecture health (not product OKRs, not aesthetic cleanliness)  
**Companions:** [`ENGINEERING-CONSTITUTION-v1.md`](ENGINEERING-CONSTITUTION-v1.md) · [`ENGINEERING-EVOLUTION-TRACKER.md`](ENGINEERING-EVOLUTION-TRACKER.md) · [`00-constitution.md`](00-constitution.md)

**Intent:** Score whether Dhund is becoming a replaceable, inspectable **engineering platform** — the same picture for every engineer.

**Higher scores do not imply more abstraction.** Higher scores imply **fewer competing implementations of the same responsibility**. Do not extract interfaces or merge folders for appearance.

---

## Scoring scale (per dimension)

| Score | Meaning |
|-------|---------|
| **1** | Missing / contradictory |
| **2** | Partial; dual paths or unclear ownership |
| **3** | Mostly true in the hot path; gaps named |
| **4** | Solid; exceptions rare and documented |
| **5** | Default path; swapping / testing / provenance routine |

**Overall** = average of the seven dimensions (report to 1 decimal).

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

| Check | Pass looks like |
|-------|-----------------|
| Connectors converge on `enqueue_import` (or documented successor) | PubMed / Drive / OneDrive → same spine |
| Full-text via UFTR | No per-provider fulltext forks |
| Analysis → evidence → writing | Worker queue + canonical engines |
| Connectors don’t reimplement accept/store policy | Policy in Library / Trust / upload service |

**Baseline:** **3** — UFTR + scholarly ops exist; still provider-specific forks in places.

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

**Why score is ~2.5 today (2026-08-05):**

| Rule | Canonical path | Still duplicated |
|------|----------------|------------------|
| Hot LLM execution | `resolve_*` → `invoke_*` / `execute_*` → Gateway | session `/api/search` embed in `search/routes.py`; writing assistant fallback |
| Import → analysis → evidence | Shared worker queue + engines | Connector-specific attach/store bits |
| Upload accept/store | Two façades (`storage/` vs `backend/storage/`) | Two HTTP entry stacks (ADR-0014) |
| Cost / attribution | AI Ledger (provenance) + CostLedger ($) | Dual write sites |

**Score 4/5 when (not perfection):**

- ✅ Every AI feature routes **Capability Router → Gateway** (utility/embed on explicit shim list).
- ✅ Every connector uses the **same import pipeline** after acquisition (`enqueue_import` → SUE → Evidence).
- ✅ Full-text via **shared UFTR**, not per-provider forks.
- ✅ Evidence / SUE / Writing / Reviewer: **one canonical implementation** per rule, regardless of entry surface.
- ✅ Multiple APIs/providers allowed — they **delegate**, not reimplement.

**5/5** = intentional dual paths retired; single implementation is the default everywhere (including ledger unify).

**PR gate:** Does this PR introduce a **second implementation** of an existing business rule? If yes → require **why**, **temporary?**, **ADR?**, **retirement plan?** — otherwise reject. See Evolution Tracker High rows.

**Does not reduce this score:** two APIs, two frontends, two providers at the edge — as long as they call the same service.

**Baseline:** **2.75** — Bites 1–8 unified utility + hot LLM paths; session search embed + dual ledger remain.

---

### 4. Single source of truth

> Evidence. Ledger. Research Jobs. One truth each.

| Truth | Current | Target |
|-------|---------|--------|
| Research claims for writing | Evidence objects (+ contracts) | Keep — do not fork |
| AI cost / attribution | Dual ledgers | Unified AI Ledger |
| Async work | `upload_jobs` + outbox (Postgres) | Keep — Redis cache only |

**Baseline:** **3.5** — Evidence + jobs strong; ledger dualism pulls score down.

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

**Baseline:** **4** — Hot LLM paths on Router → Gateway; storage dual façades and utility shims remain (see Dimension 3).

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

**Baseline:** **4.5** — Evidence First + RI freeze are strengths; extend the same bar across workflow events and all AI entrypoints.

---

## Scorecard (baseline)

| # | Dimension | Score |
|---|-----------|-------|
| 1 | Capability ownership | 3 |
| 2 | Canonical pipelines | 3 |
| 3 | Business logic — single implementation | 2.75 |
| 4 | Single source of truth | 3.5 |
| 5 | Replaceability | 4 |
| 6 | Testability | 4 |
| 7 | Inspectability | 4.5 |
| | **Overall** | **3.6 / 5** |

*Narrative constitution score (~8.5/10 product+doctrine maturity) ≠ this KPI. Architecture Health is stricter on dual paths and replaceability.*

**Aim:** Overall **≥ 4.0 / 5** without a rewrite — **primary lever:** Dimension 3 (2.5 → 4): ledger unify, upload service, UFTR, utility/embed shims retired. See Evolution Tracker High rows.

---

## What does NOT improve the score

| PR change | Score impact |
|-----------|--------------|
| `backend/library/` → `backend/library2/` (rename only) | **0** — no behavior change |
| New abstraction layer with no call-site convergence | **0 or down** — more surface, same dual paths |
| PubMed + OpenAlex both call `enqueue_import()` | **+** — business rule became canonical |
| Second HTTP stack that reimplements upload policy | **down** — second implementation |
| Folder tidy with ADR but no retirement plan for old path | **0** until old path is gone or documented |

---

## Architectural drift (ongoing check — not a separate score)

> Is the implementation still following the ADR and contracts?

| Drift signal | Action |
|--------------|--------|
| New bypass around Capability Router / Gateway | Block or ADR + retirement plan |
| Duplicate pipeline for same journey | Merge to canonical spine or score Dimension 2/3 down |
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
