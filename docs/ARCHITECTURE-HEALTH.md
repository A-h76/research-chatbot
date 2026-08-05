# Architecture Health

**Status:** Living KPI sheet — rescore when Evolution Tracker rows move.  
**Date opened:** 2026-08-05  
**Type:** Measurable architecture health (not product OKRs, not aesthetic cleanliness)  
**Companions:** [`ENGINEERING-CONSTITUTION-v1.md`](ENGINEERING-CONSTITUTION-v1.md) · [`ENGINEERING-EVOLUTION-TRACKER.md`](ENGINEERING-EVOLUTION-TRACKER.md) · [`00-constitution.md`](00-constitution.md)

**Intent:** Score whether Dhund is becoming a replaceable, inspectable **engineering platform** — the same picture for every engineer.

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

> Every package has exactly one owner.

| Check | Pass looks like |
|-------|-----------------|
| New code lands in one Platform Layer or Product Domain | PR names the owner |
| No orphan `utils.py` growth | Shared code under `shared/<concern>/` |
| Package docstring / README: Owns / Does not own | Present on touched packages |

**Baseline (2026-08-05):** **3** — many `backend/*` packages exist; `server.py` still mixed; dual stacks blur Library/Storage.

---

### 2. Shared pipelines

> Provider logic should only differ at the edges.

| Check | Pass looks like |
|-------|-----------------|
| Discovery/import/metadata/fulltext/UFTR shared | Providers thin |
| Connectors don’t reimplement accept/store policy | Policy in Library / Trust |

**Baseline:** **3** — UFTR + scholarly ops exist; still provider-specific forks in places.

---

### 3. No duplicate business logic

> If PubMed and OpenAlex share logic, move it.

| Check | Pass looks like |
|-------|-----------------|
| Same algorithm not copy-pasted across providers | Extracted helper/pipeline |
| Dual upload policies don’t diverge silently | Divergence requires ADR |

**Baseline:** **2** — dual upload/storage and dual AI/cost paths are the main duplicates (named debt).

---

### 4. Single source of truth

> Evidence. Ledger. Research Jobs. One truth each.

| Truth | Current | Target |
|-------|---------|--------|
| Research claims for writing | Evidence objects (+ contracts) | Keep — do not fork |
| AI cost / attribution | Dual ledgers | Unified AI Ledger |
| Async work | `upload_jobs` + outbox (Postgres) | Keep — Redis cache only |

**Baseline:** **3** — Evidence + jobs strong; ledger dualism pulls score down.

---

### 5. Replaceability

> Could OpenAI disappear tomorrow? Dhund still works after swapping providers.

| Check | Pass looks like |
|-------|-----------------|
| Feature code never imports provider SDKs | Router → Gateway → Provider |
| Model/provider selected by policy | Capability Router / registry |
| Storage backends swappable | Provider interface (dual façades still debt) |

**Baseline:** **3** — Router/Scope locked (ADR-0016/0017); chat SSE path still special; storage dual.

---

### 6. Testability

> Every major platform layer has independent tests.

| Check | Pass looks like |
|-------|-----------------|
| Layer tests without full monolith when possible | `backend/*/test_*.py`, contracts |
| Real Postgres for integration (constitution) | CI + local |
| Worker/queue behavior tested | Job claim / handlers |

**Baseline:** **3** — good coverage in places; monolith coupling remains; some layers thinner.

---

### 7. Inspectability

> Every decision leaves provenance.

| Check | Pass looks like |
|-------|-----------------|
| Evidence spans / confidence / bindings | Inspectable UI + API |
| AI jobs / WI drafts leave ledger + hashes where required | RI-009 / ledger |
| Research decisions / workflow events | Append-only trails |

**Baseline:** **4** — Evidence First + RI freeze are a product strength; keep raising AI entrypoints to the same bar.

---

## Scorecard (baseline)

| # | Dimension | Score |
|---|-----------|-------|
| 1 | Capability ownership | 3 |
| 2 | Shared pipelines | 3 |
| 3 | No duplicate business logic | 2 |
| 4 | Single source of truth | 3 |
| 5 | Replaceability | 3 |
| 6 | Testability | 3 |
| 7 | Inspectability | 4 |
| | **Overall** | **3.0 / 5** |

*Narrative constitution score (~8.5/10 product+doctrine maturity) ≠ this KPI. Architecture Health is stricter on dual paths and replaceability.*

**Aim:** Overall **≥ 4.0 / 5** without a rewrite — driven by Evolution Tracker High rows (AI Invocation streaming via Gateway, Cost Ledger unify, Scope coverage).

---

## How to rescoring

1. Only change scores when **behavior** changed (tests, call sites, contracts) — not folder renames.  
2. Note the PR / date under Changelog.  
3. If a score drops, require a one-line cause on the Evolution Tracker.

### Changelog

| Date | Overall | Note |
|------|---------|------|
| 2026-08-05 | 3.0 / 5 | Chat ACR model resolve + AI Ledger on done — Replaceability/Inspectability improved qualitatively; overall held at 3.0 until Gateway owns streaming |
| 2026-08-05 | 3.0 / 5 | Baseline at Engineering Constitution freeze |

---

## Anti-gaming

- Renaming packages without moving ownership → **no score change**  
- Deleting one ledger half without consolidating writes → **score may drop**  
- Adding a second queue “for clarity” → **fails** Single source of truth + Master ADR-0001  
