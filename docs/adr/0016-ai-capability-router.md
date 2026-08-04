# ADR-0016: AI Capability Router v1.0 — Research OS execution backbone

Status: accepted (frozen v1.0)  
Date: 2026-08-04  
Supersedes: ADR-0016 draft 0.1 stack (Job → Capability → Policy only)

## Context

Dhund is an **AI execution platform for research**, not “AI chat with many models.”
Researchers declare **Research Jobs**; the platform resolves how to run them.

UFTR proved the resolve-behind-a-boundary pattern. The Capability Router is the
same idea for intelligence. This ADR freezes **v1.0** of that backbone with a
realistic ship-now scope and an explicit later/don’t-build list.

## Decision — seven frozen principles

1. **Research Jobs** are the only interface the product layer uses.
2. **Execution Profile** (requirements) and **Execution Policy** (constraints) remain distinct.
3. **Capability Router** is the sole authority for model selection.
4. **Prompt Registry**, **Model Registry**, and **AI Ledger** are mandatory platform components.
5. **No feature package may call an LLM provider directly**; all AI execution flows through router + gateway.
6. **Validation prefers evidence and deterministic checks** over LLM-as-judge wherever practical.
7. **Fallback routing, budget awareness, and complexity-aware routing** are planned extensions — not blockers for v1.0.

## Canonical flow (v1.0)

```text
Research Job
        ↓
Execution Profile      ← requirements (reasoning depth, context, vision, …)
        ↓
Execution Policy       ← constraints (quality/cost/latency/governance)
        ↓
Capability Router
        ↓
Prompt Registry        ← versioned prompt for this job
        ↓
Model Registry         ← capability metadata + pricing/latency/limits
        ↓
AI Gateway
        ↓
LLM Provider
        ↓
Evidence-Based Validation   ← citations, schema, grounding — not LLM-as-judge
        ↓
AI Ledger                   ← first-class platform record of every execution
        ↓
Research Artifact
```

Product UX remains: **Hybrid Research Mode → (job implied) → platform resolves.**  
Never default to “Claude or Gemini?”

## Ship now (v1.0)

| Component | Role |
|-----------|------|
| Capability-based routing | Job → capability → profile → policy → provider → model |
| Execution Profile | Declares *what the job needs* (not which model) |
| Execution Policy | Declares *constraints* (quality / cost / latency / governance) |
| Model Registry metadata | capabilities, pricing, latency, context_limit, tools, streaming |
| AI Ledger | First-class ledger of every AI execution (not only artifact footnotes) |
| Prompt Registry | Versioned prompts per research job (existing `PromptRegistry` is the home) |

### Execution Profile vs Policy (binding)

**Profile (requirements):**

```yaml
reasoning: deep | standard | light
context: large | medium | small
vision: true | false
structured_output: true | false
temperature: low | medium | high
```

**Policy (constraints):**

```yaml
# Named policies in code: highest_quality | balanced | lowest_cost | fastest | …
quality_priority: high | medium | low
cost_priority: high | medium | low
max_cost_usd: optional float
fallback: enabled | disabled   # reserved until v1.5
```

### AI Ledger (binding)

Every platform AI call records an entry (persist incrementally; schema first):

- `execution_id`
- `research_job`, `capability`, `execution_profile`, `execution_policy`
- `provider`, `model`, `prompt_version`
- `tools_used`, `evidence_source_ids` (optional)
- `token_usage`, `latency_ms`, `cost_usd`
- `output_hash`
- `evaluation` (future / evidence-based signals)

Artifacts may still embed a compact `ai_execution` summary; the **ledger** is the system of record.

## Build later (v1.5–v2) — not contract blockers

| Extension | Why later |
|-----------|-----------|
| Provider fallback chains | Implementation detail once Tier A is stable |
| Budget-aware routing | Needs orgs / labs / billing maturity |
| Complexity-aware routing | Estimation is hard; start with job+profile defaults |

## Do not build yet

| Idea | Why not |
|------|---------|
| Separate Task Analyzer before the router | Research Job already is the analyzer for product modes |
| LLM-as-judge Output Evaluator loops | Cost/latency explode; prefer evidence/schema/grounding checks |

## Capability Evals (platform intent)

Dhund should own `/evals` corpora per job family (`literature_review`, `paper_analysis`,
`reviewer`, `writing`, `evidence`, `citation`). Routing and model changes are
validated against **Dhund workloads**, not only public benchmarks. Suite
population is iterative after v1.0 freeze.

## Provider rollout

**Tier A:** OpenAI, Anthropic, Google.  
**Adapters later:** xAI, DeepSeek, Moonshot, MiniMax, GLM — no product-logic change.

## Relation to transitional code

`AIGateway` / `ModelRouter` remain migration shims. New code calls
`resolve_execution` → Prompt Registry → Model Registry → Gateway → **AI Ledger**.

## Living contract

[`docs/contracts/ai-capability-router-contract.md`](../contracts/ai-capability-router-contract.md) — **v1.0**.

## Consequences

- Feature packages declare jobs (+ optional profile/policy overrides for advanced users later).
- Model brand names never become Research Mode names.
- Cost, audit, reproducibility, and debugging converge on the AI Ledger.
- Evidence-based validation stays aligned with Evidence / Reviewer / grounding — not recursive LLM verification.

## Freeze note (v1.0 accepted)

Accepted as written for Dhund’s current maturity. Incremental adoption:

1. `ExecutionProfile` / `ExecutionPolicy` + router + ledger scaffold
2. Route one research job (`writing` / `literature_review`) through the router + ledger
3. Verify provenance on artifacts
4. Migrate remaining jobs one by one

### Accepted follow-ups (not v1.0 blockers)

| Follow-up | Notes |
|-----------|--------|
| Capability Scorecard on Model Registry | Measured scores from Dhund `/evals` corpora (not vendor benches) |
| Ledger optional debug fields | `request_id`, `workspace_id`, `project_id`, `paper_id`, `retry_count`, `cache_hit`, `provider_latency`, `validation_status` (use `extra` until persisted schema) |
| Formal `prompt_version` | `job@semver` e.g. `writing@5.4`, `literature_review@2.0` |
| Future ADR — Prompt Registry | Versioning, rollout, deprecation, eval, rollback, ownership — **new number** (0017 is Research Scope) |
