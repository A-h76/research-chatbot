# Week 2 Evidence Layer — Verification & QA Specification

Status: Stage 4 automated gates **GO** (2026-07-28); RC pending  
Depends on:  
- `docs/architecture/week2-evidence-layer-architecture.md`  
- `docs/architecture/week2-evidence-layer-backend-technical-design.md`  
- `docs/architecture/week2-evidence-layer-frontend-technical-design.md`  
Evidence note: `docs/architecture/week2-evidence-layer-stage4-evidence.md`

---

## 1) Objective

Ship Evidence Layer MVP only when:

- No invented evidence in Inspector / explain
- Strong tenant isolation on objects, bindings, reviews, extract
- Extraction is idempotent and Research Ready gated
- Accepted vs candidate semantics are correct
- Writing Inspector empty/weak states are honest

Go/no-go for `v0.2.0-rc1` (or equivalent) is governed by this doc.

---

## 2) Quality principles

- **Evidence First:** every Inspector fact traces to a stored row.
- **Contract-first:** fixtures for explain / bindings / reviews.
- **Security-first:** IDOR and cross-project leaks are release blockers.
- **Idempotency-first:** re-extract does not duplicate active graphs.
- **Honesty-first:** insufficient evidence beats padded prose.

---

## 3) Scope

In scope:

- Schema migration `0033`
- Extractor job + scoring v0
- Reviews + bindings APIs
- `POST /api/evidence/explain`
- Evidence Inspector UI on Writing Shell
- Authz, rate limits, provenance fields

Out of scope (must not block on):

- Reasoning chat, research memory, guided generation, citation rebuild, Neo4j, six engines

---

## 4) Test pyramid

| Layer | Target share | Examples |
|-------|-------------:|----------|
| Unit | 65% | scoring bands, content_hash, mappers, explain assembly |
| Integration | 25% | Postgres extract/idempotency/IDOR/reviews |
| E2E / UI | 8% | Inspector sufficient vs insufficient |
| Manual / exploratory | 2% | Prompt-injection samples, weak evidence UX |

---

## 5) Contract fixtures

Path: `tests/fixtures/evidence/` (backend) + mirrored frontend fixtures.

Required fixtures:

1. `explain_sufficient.json`
2. `explain_insufficient.json`
3. `explain_candidates_only.json`
4. `evidence_object.json`
5. `claim_review_accepted.json`
6. `binding_create.json`
7. Error shapes: `403`, `404`, `422`

Rules: API change ⇒ fixture + mapper update in same PR.

---

## 6) Functional verification matrix

| # | Journey | Pass criteria |
|---|---------|---------------|
| 1 | Extract Research Ready file | Candidates created with page+quote+provenance |
| 2 | Extract non-ready file | Skipped; no objects |
| 3 | Re-extract same hash | Idempotent; no duplicate active rows |
| 4 | Force re-extract new version | Prior superseded; new candidates |
| 5 | Accept / reject / edit review | Status + audit row; edit supersedes when claim changes |
| 6 | Bind sentence → evidence | Binding listed; explain returns object |
| 7 | Explain without bindings | `insufficient`; empty evidence |
| 8 | Cross-tenant evidence id | 403/404; no leak |
| 9 | Inspector UI | Renders bands, candidate labels, paper/page |
| 10 | Weak / contradict-only | `weak` or clear labeling; no fake support count |

Each journey: success + validation failure + authz failure where applicable.

---

## 7) Security gates (release blockers)

- [ ] Cross-user / cross-project IDOR on get/explain/bind/review/extract
- [ ] Explain never returns unowned evidence ids
- [ ] Paper text treated as untrusted in extractor unit tests (instruction-like payload discarded or ignored)
- [ ] Telemetry payloads omit full quotes
- [ ] Rate limit on extract enqueue verified

---

## 8) Performance smoke

- Explain p95 &lt; 300ms on warm local Postgres for ≤20 bindings (adjust with measured baseline).
- Extract job completes single-paper fixture within worker SLA used by analysis jobs (document measured time in Stage 4 evidence).

---

## 9) Accessibility

- Inspector region announced on sufficiency change
- Keyboard path to open card and follow paper link
- Contrast for supports vs contradicts without color-only encoding

---

## 10) Observability gates

- Extraction run rows written for success/fail/skip
- Structured logs include `pipeline_version`, `project_id`, `file_id` without default full quote
- Metrics hooks documented even if stubbed initially

---

## 11) Exit criteria for RC

| Gate | Owner | Required |
|------|-------|----------|
| Migration applied clean on Postgres | Backend | Yes |
| Contract suite green | Backend + FE | Yes |
| Security matrix green | Backend | Yes |
| Inspector journeys 7–10 | FE + QA | Yes |
| Non-goals not shipped | Eng leads | Yes |
| Stage 4 evidence note filed | QA | Yes |

Residual risks must be listed explicitly (e.g. NVDA speech optional).

---

## 12) Rollback

- Feature-flag Inspector panel if needed
- Stop enqueueing `evidence_extract` jobs
- Tables are additive — dropping not required for rollback; stop reads/writes via flag
