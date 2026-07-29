**Status:** Active  
**Date:** 2026-07-29  
**Owner:** Platform Engineering  
**Model mapping:** `docs/AI_MODEL_REGISTRY.yaml` (separate — changes to models do not require editing this document)

---

## Philosophy

Use the cheapest model that meets the quality requirement. Escalate only when measurable evidence justifies it.

This principle holds regardless of which specific models are active. The registry (`AI_MODEL_REGISTRY.yaml`) is the replaceable configuration. This document is the stable governance layer.

---

## Out of Scope

This policy does not define:

- Prompt design or prompt templates
- Retrieval algorithms or ranking logic
- Research Intelligence reasoning (consensus, conflict, provenance)
- Evidence Platform contracts
- Provider implementation details (API keys, retry logic, rate limits)
- UI/UX decisions
- Per-feature business logic

Those concerns are owned by their respective modules.

---

## 1. SLO Targets (Operational)

| Tier | Target | Alert threshold |
|------|--------|-----------------|
| Mini | ≥ 85% of LLM calls | < 80% |
| Standard | ≤ 14% | > 18% |
| Pro | ≤ 1% | > 2% |

These are operational health metrics, not product KPIs. Breaching an alert threshold triggers a policy review, not an automatic change.

---

## 2. Escalation Policy

Route by measurable signals, not feature labels alone.

### Fast → Standard

Escalate when any of the following applies:

- Retrieval confidence below threshold (source: Retriever)
- Ambiguous user intent detected (source: Planner)
- Multi-document synthesis required
- Complex comparison requested

### Standard → Pro

Escalate only when any of the following applies:

- Reviewer fails (source: Reviewer)
- Reviewer confidence below threshold (source: Reviewer)
- Unsupported claims detected above threshold (source: Reviewer)
- Citation coverage below threshold (source: Citation Binder)
- User explicitly requests publication-quality output (source: quality_mode=publication)

Everything else stays on lower tiers.

---

## 3. Confidence Sources

The gateway must record which signal triggered escalation. Recognised sources:

| Source | Signal |
|--------|--------|
| `retriever` | Retrieval confidence score from vector search |
| `planner` | Planner confidence in section structure and evidence allocation |
| `reviewer` | Reviewer pass/fail, unsupported claim rate, citation coverage |
| `user` | Explicit quality mode selection (`publication`) |

When escalation occurs, `reason` in telemetry must reference one of these sources (e.g. `"reason": "reviewer_failed"`, `"reason": "retriever_low_confidence"`).

---

## 4. Gateway Telemetry Schema

Required fields on every gateway call:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO-8601 | Call time |
| `task` | string | Top-level task name (e.g. `literature_review`) |
| `subtask` | string \| null | Sub-operation within task (e.g. `section_generation`) |
| `quality_mode` | enum | `fast` \| `balanced` \| `publication` |
| `policy_version` | string | Active policy version (e.g. `1.0`) |
| `resolved_model` | string | Actual model used (from registry) |
| `reason` | string \| null | Escalation reason if escalated (see Confidence Sources) |
| `confidence` | float \| null | Confidence score that drove routing decision |
| `latency_ms` | int | End-to-end latency |
| `prompt_tokens` | int | |
| `completion_tokens` | int | |
| `total_tokens` | int | |
| `estimated_cost` | float | USD |
| `reviewer_pass` | bool \| null | Reviewer result if applicable |
| `escalated` | bool | Whether tier was escalated from default |
| `success` | bool | Whether call completed without error |

The `reason` field is how future analysis answers "why did Pro usage increase." Never omit it when `escalated=true`.

---

## 5. Policy Versioning

Versions are additive. Never overwrite a version — create a new one.

Each version entry must state:

- **Rationale:** why the change was made
- **Benchmark:** results that justified it
- **Expected effect:** cost / quality / latency impact

### Version history

| Version | Date | Summary |
|---------|------|---------|
| 1.0 | 2026-07-29 | Initial policy. Three-tier routing, evidence-based escalation, telemetry schema, change control. |

---

## 6. Rollback

Any policy version that causes unacceptable degradation in cost, latency, or reliability must revert to the previous approved version until sufficient evidence supports the change.

Unacceptable thresholds (triggers mandatory rollback review):

- Pro tier usage breaches alert threshold (> 2%) without corresponding quality gain
- p95 latency increases > 40% vs prior version baseline
- Error rate increases > 1% vs prior version baseline

A rollback is not a failure. It is the policy working as designed.

---

## 7. Change Control

Policy changes require evidence. Any change to model assignment or escalation thresholds must include:

- Benchmark results
- Telemetry trend evidence
- Researcher feedback (where applicable)
- Cost analysis

And must answer:

1. Did quality improve (or remain acceptable)?
2. Did cost remain acceptable?
3. Did latency remain acceptable?

If any answer is no, do not change policy.

Model assignments live in `AI_MODEL_REGISTRY.yaml`. Changing a model assignment is a registry change, not a policy change, but still requires the same evidence standard.
