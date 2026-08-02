# Researcher Validation v0.2.1 — Friction backlog

**Rule:** Fix only rows with Decision = `fix-before-20` (workflow blockers).  
Everything else → `defer` or `waive`. No new features.

Living list — append from session logs and engineering vertical smoke.

| ID | Observation | Freq (n/N) | Severity | Decision | Owner | Status | Sessions |
|----|-------------|------------|----------|----------|-------|--------|----------|
| F-001 | Generate Lit Review blocked (`no_supporting_evidence`) after Accept when EvidenceObjects have empty `supports[]` (common extract without KG edges) | eng vertical | blocker | fix-before-20 | eng | **done** 2026-08-02 — `classify_stance` claim-bearing default + projector outcome stamp | vertical E2E |
| F-002 | | | | | | | |
| F-003 | | | | | | | |
| F-004 | | | | | | | |
| F-005 | | | | | | | |

---

## Severity

| Level | Meaning |
|-------|---------|
| **blocker** | Cannot complete Import → Export without facilitator rescue |
| **soft** | Confusion or extra clicks; path still completable |
| **kpi** | Hurts 80% minimal-edits or 100% traceability |

---

## Decision

| Decision | Meaning |
|----------|---------|
| `fix-before-20` | Must ship before scaling invites |
| `defer` | After 20 / later release |
| `waive` | Accepted risk; note why |

---

## Fix loop

```text
Log friction → Triage weekly (or after each 2 sessions)
  → Implement fix-before-20 only
  → Re-smoke facilitator path
  → Mark Status = done
```
