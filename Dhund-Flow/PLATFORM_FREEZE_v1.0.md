# PLATFORM_FREEZE_v1.0

**Date:** 2026-07-29  
**Status:** Active  
**Scope:** v0.2.x delivery window

Platform is considered sufficient for v0.2.x. New platform work is frozen unless it directly unblocks the active researcher workflow or fixes a demonstrated production limitation.

---

## Foundations Frozen

- [x] Evidence Platform frozen (`v0.2.0-rc1`)
- [x] Research Intelligence architecture frozen (staged RI over EvidenceObjects)
- [x] AI Infrastructure v1.0 frozen (AI Gateway + policy + modes + telemetry + guardrail)
- [x] AI Policy v1.0 frozen (`docs/AI_POLICY_v1.0.md`)
- [x] Security Baseline v1.0 frozen (`docs/SECURITY_BASELINE_v1.0.md`)
- [x] UI/UX Vision Beta v1.0 frozen (`docs/UI_UX_VISION_BETA_v1.0.md`)
- [x] Product strategy frozen around Evidence-backed Literature Review first
- [x] Product decisions governance in place (`docs/PRODUCT_DECISIONS.md`)
- [x] Engineering roadmap aligned to workflow-first delivery

---

## AI Infrastructure v1.0 Scope

### Included
- AI Gateway
- Policy routing
- Quality modes (`fast`, `balanced`, `publication`)
- Confidence routing
- Telemetry (`task`, `mode`, `model`, `latency`, `tokens`, `cost`, `confidence`, `success`)
- Cost tracking
- Guardrail against direct feature-level model selection
- Platform decision record (`PLATFORM-001`)

### Explicitly Excluded (v2.0+)
- Multi-provider routing
- Automatic model benchmarking
- Dynamic cost optimization
- A/B routing
- User model selection
- Provider failover orchestration

---

## AI Policy Change Control

Routing policy/model assignment changes are allowed only with evidence:

- benchmark results
- telemetry trend evidence
- researcher feedback
- cost analysis

And must show acceptable quality, cost, and latency trade-offs.

---

## Current Build Focus

**Finish the Evidence-backed Literature Review vertical.**

1. Citation Binder quality + stable ordering + no orphan citations
2. Reviewer quality (unsupported claim detection, weak-evidence warnings, coverage scoring)
3. Verify UX (paragraph -> evidence -> reviewer findings -> revise/accept)
4. Export with practical evidence traceability
5. Researcher validation against release metric

---

## Freeze Rule

No new platform work unless it:

1. directly unblocks a validated researcher workflow, or
2. fixes a demonstrated production limitation.

**Security** follows the same rule — see `docs/SECURITY_BASELINE_v1.0.md`: no new security infrastructure unless it fixes a demonstrated vulnerability, a high-severity audit finding, or directly supports the active researcher workflow.

---

## Product Freeze (per release)

For each release, the workflow scope is locked when the release enters its final phase.

**v0.2.1 — locked to Evidence-backed Literature Review only.**

Allowed during product freeze:
- Bug fixes
- Polish
- Quality improvements (grounding, reviewer pass rate)
- Researcher feedback fixes

Not allowed:
- New workflows or product surfaces
- New platform subsystems
- Scope expansion beyond the declared release workflow

---

## V1 Evidence Platform close-out (2026-08-03)

**V1 = frozen Evidence Platform contracts + extract quality + Compare UX on existing RI APIs — not new RI stages.**

- Platform contracts remain frozen (`v0.2.0-rc1`); do not reopen ADR-0005 envelopes.
- Extract-quality High backlog closed under Subsystem #6 (`EXTRACTION_QUALITY_BACKLOG.md`).
- Compare / consensus / conflict UX uses existing `POST /api/evidence/consensus|conflict` and Matrix/Gaps/Graph surfaces — no RI-010+, Neo4j, or new stages in V1.
- Continuous improvement (golden fixtures, auto-enqueue extract) stays tracked, non-blocking for Alpha.
