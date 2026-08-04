# AI Capability Router — platform contract v1.0

**Service:** AI Capability Router (+ AI Ledger)  
**Version:** 1.0  
**Status:** Frozen (ADR-0016 v1.0)  
**Packages:** `backend.ai.capability_router`, `backend.ai.ai_ledger`  
**ADR:** [ADR-0016](../adr/0016-ai-capability-router.md)

## Product rule

Dhund is an **AI execution platform for research**.  
Product layer speaks **Research Jobs** only. The router is the sole model authority.

```text
Research Job
        ↓
Execution Profile
        ↓
Execution Policy
        ↓
Capability Router
        ↓
Prompt Registry
        ↓
Model Registry
        ↓
AI Gateway
        ↓
LLM Provider
        ↓
Evidence-Based Validation
        ↓
AI Ledger
        ↓
Research Artifact
```

## Frozen principles (v1.0)

1. Research Jobs are the only product-layer AI interface.
2. Execution Profile ≠ Execution Policy.
3. Capability Router alone selects models.
4. Prompt Registry, Model Registry, AI Ledger are mandatory.
5. No feature package calls LLM providers directly.
6. Prefer evidence/deterministic validation over LLM-as-judge.
7. Fallback / budget / complexity routing = planned extensions, not v1.0 blockers.

## Primary APIs

```python
from backend.ai.capability_router import resolve_execution, ACR_VERSION
from backend.ai.ai_ledger import record_execution, AILedgerEntry

assert ACR_VERSION == "1.0"

plan = resolve_execution(
    "literature_review",
    execution_policy="highest_quality",
    # optional: execution_profile=ExecutionProfile(...),
)

# After the model call:
record_execution(
    AILedgerEntry.from_plan(
        plan,
        prompt_version="literature_review@v3",
        tokens_in=…, tokens_out=…, cost_usd=…, latency_ms=…,
        output_hash="…",
    )
)
```

## Research Jobs

| Job id | Intent |
|--------|--------|
| `chat` | Research-scoped conversation (after Research Scope gate) |
| `analyze_paper` | Single-paper analysis |
| `compare_papers` | Methodology / findings compare |
| `literature_review` | Multi-source synthesis |
| `reviewer` | Critique / grounding / citation checks |
| `writing` | Academic drafting |
| `search` | Corpus / web-augmented retrieval |
| `ocr` | Page / figure understanding |
| `evidence_extraction` | Structured evidence extract |
| `bulk_processing` | Large-N triage / map |

## Capability ids (never model brands)

`scientific_reasoning` · `deep_synthesis` · `academic_writing` · `long_context` ·
`vision` · `code` · `translation` · `bulk_processing` · `structured_extraction` ·
`tool_use`

## Execution Profile (requirements)

| Field | Values |
|-------|--------|
| `reasoning` | `deep` \| `standard` \| `light` |
| `context` | `large` \| `medium` \| `small` |
| `vision` | bool |
| `structured_output` | bool |
| `temperature` | `low` \| `medium` \| `high` |

Jobs map to a default profile; advanced overrides come later.

## Execution Policy (constraints)

| Policy id | Meaning |
|-----------|---------|
| `highest_quality` | Quality first |
| `balanced` | Default |
| `lowest_cost` | Economy |
| `fastest` | Latency first |
| `offline` | Reserved |
| `enterprise_approved` | Reserved |

## Model Registry metadata (required shape)

Each registered model should declare (see `docs/AI_MODEL_REGISTRY.yaml`):

```yaml
capabilities:
  reasoning: low|medium|high
  writing: low|medium|high
  coding: low|medium|high
  long_context: low|medium|high
  structured_output: low|medium|high
  vision: low|medium|high
pricing:
  input_per_mtok: …
  output_per_mtok: …
latency_class: fast|standard|slow
context_limit: …
supports_tools: true|false
supports_streaming: true|false
```

## AI Ledger entry (system of record)

| Field | Required |
|-------|----------|
| `execution_id` | yes |
| `research_job` | yes |
| `capability` | yes |
| `execution_profile` | yes |
| `execution_policy` | yes |
| `provider` / `model` | yes |
| `prompt_version` | yes when Prompt Registry used |
| `tools_used` | optional |
| `evidence_source_ids` | optional |
| `tokens_in` / `tokens_out` / `cost_usd` / `latency_ms` | when known |
| `output_hash` | recommended |
| `evaluation` | future (evidence-based signals) |

Compact `ai_execution` on artifacts remains a **summary**; ledger is authoritative.

## Evidence-based validation (not LLM-as-judge)

Prefer: citation coverage, evidence coverage, schema/JSON validity, required sections,
grounding % / confidence from evidence. Do **not** require recursive LLM verification loops in v1.0.

## Explicitly out of v1.0

- Provider fallback chains (implement later)
- Budget-aware routing
- Complexity-aware auto-escalation
- Separate Task Analyzer in front of Research Jobs
- LLM-as-judge output evaluator loops

## Incremental adoption (ship order)

1. Scaffold: `ExecutionProfile` / `ExecutionPolicy` / `resolve_execution` / AI Ledger
2. First job: grounded writing (`writing` / `literature_review`) via router → gateway → ledger
3. Embed compact `ai_execution` on writing artifacts; verify provenance
4. Migrate remaining research jobs one by one

## Accepted follow-ups (non-blocking)

- Capability Scorecard scores on Model Registry (from `/evals`)
- Optional ledger debug fields via `extra` / later columns
- Formal `prompt_version` as `job@semver`
- Future Prompt Registry ADR (new number; 0017 is Research Scope)

## Forbidden

- Feature packages importing OpenAI/Anthropic/Google clients directly
- Research Modes named after Sol / Fable / Gemini / DeepSeek
- Default UX that asks users to pick a provider

## Versioning

- Additive jobs / profile fields / ledger columns: minor
- Changing sole-authority of the router or removing Profile≠Policy: major + ADR
