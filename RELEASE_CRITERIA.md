# RELEASE_CRITERIA

**Purpose:** Answers "Can we ship?" — distinct from ENGINEERING_ROADMAP ("What should we build?") and RELEASE_CHECKLIST_v0.2.1.md ("Is each item done?").

---

## v0.2.1 — Evidence-backed Literature Review

**Product Freeze:** No new workflows in this release. Allowed: bug fixes, polish, quality improvements, researcher feedback fixes.

### Must Have

- [ ] Literature Review workflow complete end-to-end
- [x] Citation Binder: every paragraph linked, stable ordering, no orphan citations
- [x] Reviewer: unsupported claim detection, weak-evidence warnings, pass/fail result
- [x] Verify UX: paragraph → supporting evidence → reviewer findings → accept/revise
- [x] Export: at minimum Markdown with evidence traceability
- [ ] Smoke path passes (Import → Extract → Accept → Generate → Verify → Export)
- [ ] Grounding % ≥ target (see PRODUCT_STRATEGY.md: 80% exported without major edits)
- [ ] Reviewer pass rate ≥ 80%
- [ ] No critical bugs in writing or evidence path
- [ ] Researcher validation: at least one researcher completes the full workflow
### Must Not
- No new workflows introduced
- No platform architecture work started (see PLATFORM_FREEZE_v1.0.md)

---

## Template for future releases

```
## vX.Y.Z — <workflow name>

**Product Freeze:** [scope]

### Must Have
- [ ] ...

### Must Not
- ...
```
