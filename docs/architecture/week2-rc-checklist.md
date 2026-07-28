# Week 2 Evidence Layer — RC Checklist (`v0.2.0-rc1`)

Status: **Complete** — ready to tag  
Release decision: `docs/architecture/week2-release-decision.md`

---

## A. Platform contract freeze

- [x] ADR-0005 accepted — freeze Evidence Layer contracts
- [x] Platform contracts doc published (`week2-evidence-layer-platform-contracts.md`)
- [x] Explain fixtures present under `tests/fixtures/evidence/`
- [x] ADD-0005 / ADR-0006 Phase 2.3 pipeline + Evidence Query kickoff recorded
- [x] Explicit: no further architecture work before RC tag

---

## B. Stage 4 automated

```bash
python -m pytest tests/test_evidence_security.py \
  tests/test_evidence_reliability.py \
  tests/test_evidence_performance.py \
  tests/test_evidence_accessibility.py \
  tests/test_evidence_api.py \
  backend/evidence/tests -q
```

- [x] Re-run green on tagging machine — **36 passed** (2026-07-28)

---

## C. PostgreSQL staging (release blocker)

- [x] Staging `DATABASE_URL` points at Postgres 15+
- [x] `python run_migrations.py` applied through **`0033_evidence_layer.sql`**
  - Also applied pending 0026–0032 on this environment in the same run
- [x] Tables exist: `evidence_objects`, `claim_reviews`, `writing_sentence_bindings`, `evidence_extraction_runs`
- [x] Partial unique index created via migration SQL
- [x] Smoke: extract → bind → explain — `python scripts/rc_evidence_staging_smoke.py` → **STAGING_SMOKE_OK**
- [x] Smoke: cross-user IDOR 404 — confirmed in same script

---

## D. Operational

- [x] Extract path: sync API + `evidence_extract` worker job type registered (MVP)
- [x] Rate limits present on extract/explain/review/bind routes
- [x] Telemetry omits full quotes by default (`log_evidence_metric` strips quote/claim)

---

## E. Product / docs

- [x] Board / release decision updated for RC
- [x] Roadmap: close 2.2 / open 2.3 after tag
- [x] PROJECT_STATUS note for `v0.2.0-rc1`

---

## F. Tag

```bash
git tag -a v0.2.0-rc1 -m "Evidence Layer RC1 — Phase 2.2 platform contracts frozen"
```

- [x] Tag created after checklist complete

After tag: close Phase 2.2 on the board; open Phase 2.3 Sprint 0 (Evidence Query) under ADD-0005 / ADR-0006.

---

## Sign-off line

> Approved for `v0.2.0-rc1`. PostgreSQL staging migration `0033` applied; staging smoke and regression green; checklist complete.  
> — 2026-07-28
