# Evidence Extraction — quality backlog

**Status:** V1 High items closed (Subsystem #6, 2026-08-02); residual = continuous improvement  
**Layer:** Evidence Extraction Pipeline (upstream of frozen Evidence Platform)  
**Rule:** Improve precision/recall and metadata; do not reopen Platform contracts (ADR-0005).

RI productization depends on a populated corpus of **accepted** EvidenceObjects. Prefer quality PRs here over bypassing into Analysis/PDF from Applications.

---

## Backlog

| Item | Why | Priority | V1 |
|------|-----|----------|----|
| Better claim detection / normalisation from Phase 1 projections | Fewer empty quotes; cleaner claims | High | ✅ `phase_projector.v1.1` — `normalize_claim`, skip trivial, `claim_equals_quote` flag |
| Richer facets for conflict mediators (population / dosage / method / outcome in provenance) | Improves Conflict stage coding | High | ✅ Facets from KG props + PICO stamped into provenance |
| Additional study-type coverage in projectors | Ranking / consensus quality | Medium | ✅ Partial — alias table (RCT / cohort / meta / …); expand as domains need |
| Precision/recall golden fixtures per domain | Measurable extraction quality | Medium | Tracked — not blocking Alpha |
| Review UX hints (why candidate is weak) | Faster accept/reject | Medium | ✅ Inspector weak chips + reject presets |
| Auto-enqueue extract after Research Ready | Fewer manual Extract clicks | Low (product) | Tracked — not blocking Alpha |

---

## Smoke path (manual)

1. Open a **Research Ready** paper in a project → **Extract evidence**  
2. Writing Studio → Inspector → **Accept** candidates  
3. Select a sentence → confirm RI chips (consensus / conflict / reason)  
4. **Generate from evidence** → insert or blocked state  

Do not treat Style-only transforms as research-backed.

---

## Related

- [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)  
- [FEATURE_MATRIX.md](FEATURE_MATRIX.md)  
- `backend/evidence/services/extract_service.py` · `phase_projector.py`
