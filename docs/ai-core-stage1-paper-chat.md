# Sprint 5 — First Production Integration  
## Stage 1: Paper Chat pipeline (behaviour-identical)

**Status:** Implemented — **soak in progress** (do not start Stage 2)  
**Date:** 2026-07-26  
**Soak runbook:** [`ai-core-stage1-soak.md`](ai-core-stage1-soak.md)  
**Depends on:** `backend/ai_core` through Sprint 4.5 · [ADR-0002](adr/0002-ai-core-layer-boundaries.md)  
**Non-goal:** IdentityPack doctrine, Phase 1 ResearchContext as the answer ground, prompt quality changes, validator regenerate/rewrite

**Checkpoint tag (after soak is green — not before):** `v0.8-ai-core-stage1`

---

## 0. One rule

> **The only observable change is the call path.**  
> Users must not notice Stage 1. If they notice, Stage 1 changed too much.

Stage 2 (later) is when Identity + ResearchContext may improve behaviour.  
Stage 1 must not smuggle Stage 2 in.

---

## 0.1 Design-review refinements (locked)

These three contracts are required before / during Stage 1 implementation:

1. **`PromptPlan` is immutable** — `@dataclass(frozen=True)`; executor and route must not mutate it after the router returns it. Nested `metadata` is read-only (e.g. `MappingProxyType`).
2. **Legacy prompt version is a first-class constant** — `LEGACY_PAPER_CHAT_PROMPT_VERSION` (value `"legacy_paper_chat_v1"`). Router, `AIExecutionResult`, and golden tests all import that symbol — no scattered string literals.
3. **Stage 1 validation is observe-only** — Observe → Record → Warn. Never modify streamed output. Never regenerate. Regenerate/rewrite is Stage 2+.

---

## 1. Scope

### In scope (Paper Chat only)

Triggered when `conversations.file_id` is set and ownership checks pass — today’s M7 Paper Chat path inside `POST /api/chat`.

Relocate **only**:

1. System prompt selection → `PromptRouter` → template keyed by `LEGACY_PAPER_CHAT_PROMPT_VERSION`  
2. Model invocation entry → `AIExecutor` (wrapping the **existing** Responses streaming loop)  
3. Execution observability → `AIExecutionResult` stamps (even if stream path records them after/alongside SSE)

### Explicitly out of scope (must stay as today)

| Concern | Stage 1 behaviour |
|---------|-------------------|
| SSE event shapes the SPA expects | Unchanged |
| OpenAI **Responses API** streaming | Unchanged transport |
| `rag_retrieve(..., file_id=paper_file_id)` | **Keep** — same excerpts, same developer message |
| Attachments / vision / inline docs | Unchanged |
| Web search / memory off for paper chat | Unchanged |
| Conversation CRUD, titles, history assembly | Stay in the route |
| General (non-paper) chat | Untouched |
| Identity doctrine injection | **Forbidden** in Stage 1 |
| Replacing RAG with Phase 1-only context | **Forbidden** in Stage 1 |
| Validator regenerate / rewrite of answer text | **Forbidden** in Stage 1 |

---

## 2. Target call path

```
Paper Chat branch of POST /api/chat
        │
        ▼
AIRequest  (question, file_id, conversation_id, model, …)
        │
        ▼
IntentClassifier  (hint=READING or PAPER_CHAT — must not change prompt)
        │
        ▼
ResearchContextBuilder  (optional / may be no-op for answers in Stage 1)
        │
        ▼
PromptRouter → template_key / prompt_version = LEGACY_PAPER_CHAT_PROMPT_VERSION
        │         (text === today’s build_paper_chat_prompt output)
        ▼
PromptPlan  (frozen — log / serialize this exact object)
        │
        ▼
AIExecutor.execute_stream(plan, …)   ← must drive Responses SSE; plan read-only
        │
        ▼
OpenAI Responses API (existing stream contract)
        │
        ▼
ResponseValidator  (Stage 1: Observe → Record → Warn only)
        │
        ▼
AIExecutionResult  (observability; response text mirrors what was streamed)
```

**Important:** Stage 1 does **not** require Phase 1 evidence/entities in `ResearchContext` to answer. Context builder may run for metrics (`entity_count`, `evidence_count`) but **must not** replace or omit RAG excerpts in the model input.

---

## 3. Contracts

### 3.0 Frozen `PromptPlan`

```python
@dataclass(frozen=True)
class PromptPlan:
    ...
```

Rules:

- Once `PromptRouter.route(...)` returns a plan, **neither** `AIExecutor` **nor** the route may mutate fields or nested metadata.
- Every Stage 1 execution should log (or attach to `AIExecutionResult`) the **exact** plan that was executed — typically via `plan.to_json()` / a stable serialization, not a mutated copy.
- Debugging benefit: one immutable plan object = one ground truth for “what we sent.”

### 3.0.1 Version constant (no string drift)

In `backend/ai_core/versions.py` (or equivalent):

```python
LEGACY_PAPER_CHAT_PROMPT_VERSION = "legacy_paper_chat_v1"

PROMPT_VERSIONS = {
    ...,
    "legacy_paper_chat": LEGACY_PAPER_CHAT_PROMPT_VERSION,
}
```

Consumers **must** import `LEGACY_PAPER_CHAT_PROMPT_VERSION`:

| Consumer | Use |
|----------|-----|
| `PromptRouter` | Forced template / `prompt_version` for Paper Chat Stage 1 |
| `AIExecutionResult` | `prompt_version` stamp |
| Golden tests | Assert equality against the constant |

Do not compare against a raw `"legacy_paper_chat_v1"` literal in new code.

### 3.0.2 Validator policy (Stage 1)

| Allowed | Forbidden |
|---------|-----------|
| Observe streamed / final text | Rewrite answer text |
| Record `ValidationResult` on `AIExecutionResult` | Regenerate a second model call |
| Emit warnings / structured log | Block or replace SSE bytes mid-flight |
| Soft-fail flags for operators | Alter user-visible content based on validator |

Flow:

```
Observe → Record → Warn
```

Not:

```
Observe → Regenerate → Rewrite
```

Regeneration belongs in **Stage 2 or later**.

---

## 4. Parity locks (non-negotiable)

### 4.1 Prompt parity — `LEGACY_PAPER_CHAT_PROMPT_VERSION`

- Extract today’s `build_paper_chat_prompt(user, paper)` into a versioned template keyed by that constant.
- `PromptRouter` for paper chat **must select this template only** when the flag is on (forced — not keyword-inferred).
- Golden test: for fixed `(user, paper)` fixture,  
  `plan.system_text` (or skill+system composition used as system) **equals** legacy function output byte-for-byte (or normalised newline-stable equality).
- Assert `plan.prompt_version == LEGACY_PAPER_CHAT_PROMPT_VERSION`.

Do **not** prepend IdentityPack in Stage 1.

### 4.2 RAG parity

- Continue calling `rag_retrieve(user_id, convo_id, project_id, query, file_id=paper_file_id)`.
- Same top_k and developer-message framing as today.
- Golden test: fixed chunks fixture → identical JSON excerpt payload in the request assembly.

### 4.3 Streaming parity

Today’s path uses **OpenAI Responses API + SSE**, not Chat Completions.

Stage 1 `AIExecutor` requirements:

| Requirement | Detail |
|-------------|--------|
| Stream API | Must invoke the same Responses streaming path (or a dedicated `ResponsesStreamClient` behind `LLMClient`) |
| SSE contract | Preserve event types/payloads the frontend already consumes |
| Stop / cancel | Existing behaviour preserved |
| Partial tokens | User-visible streaming unchanged |

**Forbidden in Stage 1:** silently switching Paper Chat to non-streaming `ModelRegistry.call` / Chat Completions.

If the current `AIExecutor` cannot stream Responses yet, Stage 1 work **includes** adding `execute_stream` (or equivalent) before flipping the flag for real users.

### 4.4 Equivalence definition

“Equivalent” means **fixture equality**, not subjective answer quality:

1. System prompt text (legacy template)  
2. RAG developer payload  
3. Ordered input items structure for fixed history/attachments (where tested)  
4. SSE event sequence shape with a **FakeResponsesStream** (recorded transcript)  
5. `PromptPlan.to_json()` ≡ fixture (deterministic serialization)

Live model free-form A/B is optional later — **not** a merge gate.

---

## 5. Architectural constraints (route)

When `paper_chat_pipeline_enabled` is ON for a paper chat:

| Must not | Must |
|----------|------|
| Import OpenAI SDK in the route | Call `AIExecutor` / stream client only |
| Call `build_paper_chat_prompt` directly | Resolve prompt via `PromptRouter` → `LEGACY_PAPER_CHAT_PROMPT_VERSION` |
| Read identity markdown files | Use frozen `PromptPlan` only (no mutation) |
| Reach into adapter/retrieval internals | Pass `file_id` / ids into builder/source at the edge |
| Change general-chat assembly | Gate solely on paper `file_id` path |
| Mutate `PromptPlan` after route | Treat plan as read-only input to executor |

Conversation loading, auth, SSE `yield`, persistence of assistant messages remain in the route (or existing helpers).

---

## 6. Feature flag & rollout

```
PAPER_CHAT_PIPELINE_ENABLED=false   # default  (false | true | shadow)
```

| Value | Behaviour |
|-------|-----------|
| `false` | Exact legacy path (today’s code) |
| `true` | Stage 1 pipeline path |
| `shadow` (recommended if implemented) | Build pipeline `PromptPlan`; **still serve legacy stream**; log hash parity only |

### Shadow mode logging (hashes, not full prompts)

If shadow is implemented, log **at most**:

```text
legacy_prompt_hash = <sha256>
pipeline_prompt_hash = <sha256>
identical = true|false
prompt_version = <LEGACY_PAPER_CHAT_PROMPT_VERSION>
```

Do **not** store full prompt bodies in shadow logs (parity without excessive logging / PII sprawl).

Optional: same pattern for RAG developer-payload hash.

### Rollout sequence (locked)

1. Land code behind flag **OFF** in production  
2. Enable in **staging**; compare golden fixtures  
3. Run **shadow** mode (if implemented); confirm `identical=true` on soak traffic  
4. Enable for a **small allowlist**  
5. Roll out broadly after soak  
6. Remove the legacy branch **only after** the new path has proven itself (later sprint — not Stage 1)

Quick rollback = set flag OFF. No deploy required if env-driven.

---

## 7. Observability (every Stage 1 execution)

Record on `AIExecutionResult` (and/or structured log):

| Field | Source |
|-------|--------|
| `model` | Active chat model |
| `prompt_version` | `LEGACY_PAPER_CHAT_PROMPT_VERSION` |
| `identity_version` | Stamp present; **do not inject identity text** in Stage 1 |
| `context_schema_version` | Context schema constant |
| `latency_ms` | End-to-end generation |
| `usage` | Prompt/completion/total tokens when API provides them |
| `validator` | Observe-only result (warnings OK; **never** rewrite streamed text) |
| Context stats | e.g. RAG excerpt count, `file_id`, optional Phase 1 counts if builder ran |
| Plan stamp | Stable plan serialization or hash of `plan.to_json()` |

Identity version may be recorded for forward compatibility even while IdentityPack is not in the prompt.

---

## 8. Testing (merge gates)

### Required

1. **Prompt golden** — template for `LEGACY_PAPER_CHAT_PROMPT_VERSION` ≡ `build_paper_chat_prompt` on fixtures  
2. **RAG golden** — excerpt assembly unchanged  
3. **SSE shape** — Fake stream client → expected event types  
4. **`PromptPlan` serialization** — deterministic: `plan.to_json() == fixture` (protects router ↔ executor interface)  
5. **Plan immutability** — frozen; mutating fields raises / is impossible  
6. **Flag OFF** — existing Paper Chat tests / behaviour path unchanged  
7. **Flag ON** — pipeline path used; no OpenAI import in route module under test (lint or architecture test)  
8. **General chat** — unaffected smoke  
9. **Validator observe-only** — unit test that Stage 1 path does not regenerate or rewrite answer text  

### Explicitly not required for merge

- Live OpenAI quality A/B  
- IdentityPack in system prompt  
- Phase 1-only answering without RAG  
- Validator regenerate loop  

---

## 9. Acceptance criteria (checklist)

### Functional

- [ ] Paper Chat answers feel unchanged to users (manual soak)  
- [ ] Streaming still works (tokens, stop, reconnect behaviour as today)  
- [ ] Citations / page-section guidance behaviour unchanged (same RAG + prompt rules)  
- [ ] Conversation history and paper scope unchanged  

### Architectural

- [ ] No OpenAI SDK import in the Paper Chat route path when flag ON  
- [ ] No direct `build_paper_chat_prompt` call when flag ON  
- [ ] No identity file I/O from the route  
- [ ] No retrieval-adapter internals from the route  
- [ ] `PromptPlan` frozen; route/executor do not mutate it  
- [ ] All version stamps use `LEGACY_PAPER_CHAT_PROMPT_VERSION`  
- [ ] Validator is observe → record → warn only  

### Operational

- [ ] Each flagged execution records model, versions, latency, tokens, validator, context stats  
- [ ] Shadow (if on) logs hashes + `identical`, not full prompts  
- [ ] Flag default OFF; rollback verified  

### Testing

- [ ] Golden prompt + RAG fixtures pass  
- [ ] `PromptPlan.to_json()` fixture test passes  
- [ ] Stream contract test passes with fake client  
- [ ] Flag OFF regression suite green  

---

## 10. Stage 2 boundary (do not start in Stage 1)

Only after Stage 1 is stable in production:

- Prepend / merge **IdentityPack** into system text  
- Use **Phase 1 ResearchContext** as primary grounding (RAG policy may evolve)  
- Replace `LEGACY_PAPER_CHAT_PROMPT_VERSION` with intent skills (`reading_vN`, etc.)  
- ResponseValidator **regenerate / rewrite** for ungounded claims  

---

## 11. Implementation notes (for the coding sprint)

Suggested order of work:

1. Ensure `LEGACY_PAPER_CHAT_PROMPT_VERSION` + register in `PROMPT_VERSIONS`; golden test vs `build_paper_chat_prompt`  
2. Confirm `PromptPlan` is frozen + add `to_json()` + serialization fixture test  
3. Add `AIExecutor.execute_stream` (Responses SSE) + FakeResponsesStream; plan remains read-only  
4. Wire flag in `/api/chat` paper branch: router → plan → executor stream; keep RAG where it is  
5. Wire observe-only validator stamps (no rewrite)  
6. Optional: shadow mode with prompt-hash parity logs  
7. Staging soak → allowlist → broad ON  

`IntentClassifier` may return `READING` with an explicit hint from the paper-chat branch so classification noise cannot change the template selection — **template must be forced via `LEGACY_PAPER_CHAT_PROMPT_VERSION` for Stage 1**, not inferred from keywords.

---

## 12. Related docs

- [ADR-0002 — AI Core layer boundaries](adr/0002-ai-core-layer-boundaries.md)  
- [Chat → Prompt Engine roadmap](chat-migration-roadmap.md) (normal chat Phase A; Paper Chat Stage 1 supersedes “deferred A3” for plumbing)  
- `backend/ai_core/` — IdentityLoader, ContextBuilder, PromptRouter, AIExecutor  
- `backend/ai_core/versions.py` — `LEGACY_PAPER_CHAT_PROMPT_VERSION`, `IDENTITY_VERSION`, `CONTEXT_SCHEMA_VERSION`

---

*End of Stage 1 spec — behaviour-identical Paper Chat pipeline (approved for implementation).*
