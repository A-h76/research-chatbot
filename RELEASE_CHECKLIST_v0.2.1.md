# RELEASE_CHECKLIST_v0.2.1

Release target: **v0.2.1 Evidence-backed Literature Review**

Mark each item only when verified in app or tests.

- [x] Import works
- [x] Extraction works
- [x] Evidence acceptance works
- [x] Literature Review generation works
- [x] Citation Binder complete
- [x] Reviewer complete
- [x] Verify UI complete
- [x] Export works
- [x] Metrics collected
- [ ] Smoke test passes

## Smoke Test Path

- [ ] Import a paper
- [ ] Run extraction
- [ ] Accept evidence in Inspector
- [ ] Generate Evidence-backed Literature Review
- [ ] Verify paragraph evidence links and reviewer status
- [ ] Export draft

## Verification Notes (2026-07-29)

- Import works: `python -m imports.test_imports` → 9 passed.
- Extraction works: `backend/evidence/tests/test_evidence_layer_unit.py` → 9 passed (includes extraction plan/idempotency coverage).
- Evidence acceptance works: `tests/test_evidence_api.py::test_review_accept` included in suite → pass.
- Literature Review generation works: `tests/test_evidence_writing_intelligence.py` + `backend/evidence/tests/test_writing_*` suites → pass.
- Citation Binder complete: `backend/evidence/tests/test_writing_binder_reviewer_unit.py` → pass.
- Reviewer complete: Research Reviewer unit tests + API writing response contains `review` + primary metrics.
- Verify UI complete: `GroundedDraftVerify.tsx` — hover markers → cards → Accept/Revise; bindings persist on Insert.
- Export works: Markdown builder + Export tab Lit Review row (body + Evidence appendix + bibliography + generation metadata); unit tests pass. **Manual smoke still required.**
- Metrics collected: writing response includes `metrics`; UI emits `grounded_insert`, `edits_before_export`, `grounded_export`.
- Researcher Validation: kit active — `docs/RESEARCHER_VALIDATION_v0.2.1.md` (5 → friction → 20).

## Definition of Done

Release is done only when every checkbox above is checked.
