# A-402 — Versioning Policy

**Status:** Frozen (A-402 + A-403/A-404 additives; A-405 doc freeze)  
**contracts_version:** `1.2.0`  
**Parent:** [IDD-0008](../idd/IDD-0008-Versioning.md)

This policy answers: *when does a change need a bump, an ADR, or a new API version?*

---

## 1. Layers that version independently

| Layer | Mechanism | Example |
|-------|-----------|---------|
| HTTP API surface | Path `/api` = **API v1**; future `/api/v2` | Rename `objects` → `items` |
| Living contracts pack | `contracts_version` in `docs/contracts/README.md` | `1.2.0` (A-403 ranking + metrics) |
| Evidence extract pipeline | `pipeline_version` on EvidenceObject / extract | `2.2.0` |
| RI stages | `versions.{stage}` + `*_version` fields | `retrieval: 1.0.0`; ranking/consensus/conflict `1.1.0` |
| Writing | `writing_version` | `2.0.0` |
| Reviewer | `reviewer_version` | `1.1.0` |
| Events | payload + outbox `event_type` | `ReviewCompleted` (+ optional `reviewer_run_id`) |
| Job status API | additive fields under A-404 | `lifecycle`, `retry`, `timings` |

Changing a **pipeline/reviewer/writing** semver does **not** by itself require `/api/v2` if the HTTP JSON shape stays compatible.

---

## 2. Decision table

| Change | API path | `contracts_version` | ADR? |
|--------|----------|---------------------|------|
| Add optional JSON field; clients ignore unknowns | stay `/api` | **minor** (e.g. 1.1 → 1.2) | no |
| Add new endpoint under existing nouns | stay `/api` | **minor** | no (notify B) |
| Add new EvidenceQuery intent or ranking_strategy | stay `/api` | **minor** | no if additive; yes if changes defaults meaningfully |
| Rename / remove frozen field; change meaning | **`/api/v2`** (or dual-read period) | **major** | **yes** |
| Change HTTP status for same semantic (e.g. validation 422→400) | breaking for clients | **major** | **yes** |
| Change EvidenceObject `status` enum meanings | breaking | **major** | **yes** |
| Fix docs to match already-shipped code | n/a | patch / minor note | no |
| Swap RI list key `objects` → `items` | breaking | **major** | **yes** |
| Introduce `{data,meta,errors}` on v1 | forbidden without dual-read | **major** | **yes** |

---

## 3. Semver for `contracts_version`

- **MAJOR** — incompatible with Developer B code written against previous freeze  
- **MINOR** — additive, backward compatible  
- **PATCH** — clarifications, examples, typo fixes only  

---

## 4. Dual-run rule (breaking HTTP)

1. Ship ADR.  
2. Prefer new path `/api/v2/...` (clearer than Accept headers).  
3. Keep v1 behavior ≥ one release (SPA can migrate faster internally).  
4. Document sunset (≥ 90 days if any external client).  

---

## 5. What “frozen” means (A-405)

Developer B can rely on:

- Routes and methods in [api-contracts.md](./api-contracts.md)  
- EvidenceObject / RI / writing / reviewer fields in [evidence-contract.md](./evidence-contract.md)  
- Error body shape in [error-contract.md](./error-contract.md)  
- Job status enrichment in [job-observability.md](./job-observability.md)  

Backend work after A-405 **treats those as compatibility commitments**, not sketches.  
See [A-405-documentation-freeze.md](./A-405-documentation-freeze.md).
