# Response Contract

**Layer:** 7 / Response Contract  
**Status:** Doctrine (Sprint 2). Target shape for all AI features (Phase B).

## Canonical shape

Every Soro AI feature should converge on:

- **answer** — primary response text (grounded)
- **evidence** — supporting pointers / excerpts from corpus or Phase 1
- **confidence** — exactly one of: `High` | `Medium` | `Low`
- **limitations** — what is missing, skipped, weak, or out of scope
- **workspace_refs** — navigable Paper Workspace references (stable ids)

This matches `backend.ai_core.schemas.ai_response.AIResponse`.

## Confidence guide

| Level | When |
|-------|------|
| **High** | Direct support in retrieved / Phase 1 context; low ambiguity |
| **Medium** | Partial support, mild conflict, or inference required |
| **Low** | Thin context, skipped phases, or substantial uncertainty |

## Inheritance

Task prompts (reading, writing, compare, critique, …) **add** skill instructions.  
They do **not** replace Identity → Evidence First → Integrity → Grounding → Citation → Reasoning → this contract.
