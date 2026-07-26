# ADR-0002: AI Core layer boundaries

Status: accepted  
Date: 2026-07-26

## Context

`backend/ai_core` is the orchestration brain for Soro AI features (identity,
context, routing, validation). Phase 1 results, notes, and citations already
exist in Postgres. Without a hard boundary, retrieval/ORM details leak into
prompt routers and response shapes — recreating the dual-stack debt we are
trying to escape.

## Decision

**Permanent layering rule:**

1. **No component below `PromptRouter` may query the database.**  
   Adapters (`ai_core/adapters/*`) translate JSON/dicts only.  
   `Phase1Source` implementations are the sole persistence edge for context
   retrieval; they must emit plain dicts (never ORM instances) into adapters.

2. **No component above `ResearchContextBuilder` may know how context is retrieved.**  
   `PromptRouter`, validators, executors, and feature routes consume
   `ResearchContext` / `PromptPlan` / `AIResponse` / `AIExecutionResult` only.

3. **No OpenAI / provider SDK calls outside `AIExecutor` (and its `LLMClient`).**  
   Paper Chat and other features call `AIExecutor.execute(PromptPlan)` only.

**Role map:**

| Component | Knows |
|-----------|--------|
| Adapters / `Phase1Source` | Persistence format → pure dicts |
| `Phase1Retrieval` + Ranking + Compression | Composition into `ResearchContext` |
| `PromptRouter` | Identity + skill + context → `PromptPlan` |
| `AIExecutor` + `LLMClient` | Model invocation → `AIExecutionResult` |
| `ResponseValidator` | Policy / schema → `ValidationResult` |
| `AIResponse` | User-facing presentation |

**Versioning (independent stamps on every execution):**

- `IDENTITY_VERSION` — doctrine pack  
- `prompt_version` — per-skill template (e.g. `reading_v1`)  
- `CONTEXT_SCHEMA_VERSION` — `ResearchContext` / adapter shape  

## Consequences

- Paper Chat / Writing / Compare migrate by swapping retrieval DI, not by
  rewriting prompts inside routes.
- Cost/analytics use `AIExecutionResult`, not fields hung on `AIResponse`.
- Tests can satisfy contracts with `MemoryPhase1Source` fixtures that mirror
  `analysis_pipeline_results.phase_results` JSON without a live DB.

## Non-goals

- This ADR does not migrate Paper Chat by itself.
- **Stage 1 Paper Chat** (behaviour-identical plumbing) is specified in
  [`ai-core-stage1-paper-chat.md`](../ai-core-stage1-paper-chat.md) — Responses
  SSE + RAG parity + `legacy_paper_chat_v1`; IdentityPack not injected.
- This ADR does not replace `backend.ai.PromptBuilder` yet — callers migrate
  incrementally onto `ai_core` plans.
