# PLATFORM_DECISIONS

Purpose: infrastructure governance records for cross-cutting platform rules.

---

## PLATFORM-001 — AI Gateway v1.0

- Date: 2026-07-29
- Status: Accepted
- Owner: Platform Engineering

### Decision
No product feature may directly select an LLM model. All AI requests resolve through:

Task -> Quality Mode -> Policy -> Model Router -> Provider.

### Why
- Keeps architecture stable across model generations.
- Prevents cost drift from feature-level model hardcoding.
- Makes upgrades/config changes policy-only, not code-wide edits.

### Scope (pre-v0.2.1)
- Introduce `backend/ai/gateway.py` + `backend/ai/policy.yaml`.
- Route feature calls by `(task, mode)` in critical paths.
- Emit gateway telemetry for task/mode/model/latency/tokens/cost/confidence/success.
- Enforce guardrail against direct `model=` selection outside approved AI infra modules.

### Out of scope
- Dynamic multi-model orchestration.
- Cross-provider benchmarking program.
- Full vendor abstraction rewrite.

### Related
- `Dhund-Flow/PRODUCT_STRATEGY.md`
- `docs/PRODUCT_DECISIONS.md` (PD-0001)
