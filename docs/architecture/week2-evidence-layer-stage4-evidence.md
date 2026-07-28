# Week 2 Evidence Layer — Stage 4 Verification Evidence

Date: 2026-07-28  
Scope: Phase 2.2 Evidence Layer MVP  
Environment: local SQLite test harness (`pytest`), Windows host  
Command:

```bash
python -m pytest tests/test_evidence_security.py \
  tests/test_evidence_reliability.py \
  tests/test_evidence_performance.py \
  tests/test_evidence_accessibility.py \
  tests/test_evidence_api.py \
  backend/evidence/tests -q
```

Result: **36 passed**

---

## Maturity snapshot (architecture review)

| Area | Status |
|------|--------|
| Architecture | Complete |
| Backend | Complete |
| Frontend | Complete |
| Contracts | Frozen & implemented |
| Core APIs | Complete |
| Worker integration | Complete |
| Evidence Inspector | Complete |
| Tests | Good first baseline (36 Stage 4 + unit) |
| Stage 4 verification | **Automated gates green** (this note) |
| Release candidate | Pending sign-off + Postgres `0033` apply |

---

## Security (release blockers)

| Gate | Result | Evidence |
|------|--------|----------|
| Unauthenticated routes blocked | Pass | `test_unauthenticated_evidence_routes_blocked` |
| Cross-user IDOR (get/review/binding) | Pass | `test_cross_user_evidence_idor` |
| Cross-project isolation (same user) | Pass | `test_cross_project_list_isolation_same_user` |
| Explain ownership | Pass | `test_explain_rejects_foreign_document`, `test_explain_never_returns_unowned_evidence_ids` |
| Binding ownership | Pass | `test_binding_rejects_foreign_evidence` |
| Extraction ownership | Pass | `test_extract_rejects_foreign_file` |
| Prompt-injection / untrusted paper text | Pass | `test_prompt_injection_*`, `test_ungrounded_injection_is_skipped` |

---

## Reliability

| Gate | Result | Evidence |
|------|--------|----------|
| Not Research Ready → skipped | Pass | `test_extract_not_ready_is_skipped` |
| Repeated extraction idempotent | Pass | `test_repeated_extraction_is_idempotent` |
| Force re-extract / supersede path | Pass | `test_force_reextract_supersedes_prior` + extract_service force run reuse |
| candidate→accepted / rejected | Pass | `test_candidate_to_accepted_and_rejected` |
| Edited review append-only supersede | Pass | `test_edited_review_supersedes_append_only` |

---

## Performance (measured, not estimated)

Warm local SQLite, 2026-07-28:

| Metric | Measured | Budget | Result |
|--------|----------|--------|--------|
| Explain p50 (20 bindings, n=25) | **7.94 ms** | &lt; 300 ms | Pass |
| Explain p95 | **9.53 ms** | &lt; 500 ms smoke | Pass |
| Extract 40 claims / paper | **13.80 ms** | &lt; 5000 ms | Pass |

Residual: re-measure on Postgres + production-shaped payload before calling sustained-load complete.

---

## Accessibility (structural)

| Gate | Result | Evidence |
|------|--------|----------|
| Inspector landmark + live region | Pass | `test_inspector_has_live_region_and_landmark` |
| Wired into Writing Studio | Pass | `test_inspector_mounted_in_writing_studio` |
| Insufficient / candidate copy | Pass | `test_inspector_candidate_and_sufficiency_copy_present` |

Residual: optional NVDA speech pass (same class as Week 1.1 residual).

---

## Go / no-go

| Decision | Status |
|----------|--------|
| Stage 4 automated verification | **GO** |
| Tag `v0.2.0-rc1` | **Pending** — apply `migrations/0033_evidence_layer.sql` on staging Postgres; human RC checklist; optional runtime a11y |
| Start Phase 2.3 Research Intelligence | **Blocked until RC approved** (ADD-0005) |

---

## Explicit non-starts

- Research Intelligence retrieval/ranking (Phase 2.3)
- Guided generation / Writing Intelligence
- Citation engine rebuild
