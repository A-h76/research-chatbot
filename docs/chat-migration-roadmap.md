# `/api/chat` → Prompt Engine / AI Core migration roadmap

## Status (2026-07-26)

**Done for normal chat (Phase A):**
- `PromptBuilder.build_chat_instructions()` — chat_system only, flat output, all memories, project ownership
- `/api/chat` normal path uses it via `build_system_prompt()` (default `CHAT_USE_PROMPT_BUILDER=true`)
- Responses streaming / tools / vision unchanged
- Paper chat still uses `build_paper_chat_prompt` (legacy)

**Rollback (normal chat):** set `CHAT_USE_PROMPT_BUILDER=false` to use `_build_system_prompt_legacy`.

**Next — Paper Chat Stage 1 soak (do not start Stage 2 yet):**  
See **[`ai-core-stage1-soak.md`](ai-core-stage1-soak.md)** and [`ai-core-stage1-paper-chat.md`](ai-core-stage1-paper-chat.md).  
Order: `shadow` → `true` (staging) → allowlist → broad → tag `v0.8-ai-core-stage1`.  
Flag: `PAPER_CHAT_PIPELINE_ENABLED` (default OFF).

**Still future (Stage 2+):**
- Paper chat → IdentityPack + ResearchContext (behaviour may improve)
- Optional: layer global `system_prompt` above `chat_system` (product decision)
- Title / memory extract / writing / compare/gaps registry migration
- ModelRegistry streaming/tools (not required for assembly unification)

---

## Phase A parity decisions (locked) — normal chat

1. **System layer:** `chat_system` only — do not prepend global `system_prompt`
2. **Shape:** flat `\n\n` join — no `##` section headers
3. **Memory:** all global + project facts (not MemoryEngine top-5)
4. **Paper chat:** Stage 1 spec in `ai-core-stage1-paper-chat.md` (plumbing); Stage 2 for doctrine
5. **Flag:** `CHAT_USE_PROMPT_BUILDER` (default true after cutover)

---

## Why ModelRegistry was not used for chat calls

`/api/chat` uses `client.responses.create()` (streaming, tools, vision).
Phase A only replaces **prompt assembly**, leaving that loop intact.

**Stage 1 Paper Chat inherits the same constraint:** `AIExecutor` must drive Responses streaming (or wrap the existing stream loop). Chat Completions-only executor is not acceptable for Paper Chat Stage 1.
