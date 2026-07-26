# `/api/chat` → Prompt Engine migration roadmap

## Status (Phase A — 2026-07-26)

**Done for normal chat:**
- `PromptBuilder.build_chat_instructions()` — chat_system only, flat output, all memories, project ownership
- `/api/chat` normal path uses it via `build_system_prompt()` (default `CHAT_USE_PROMPT_BUILDER=true`)
- Responses streaming / tools / vision unchanged
- Paper chat still uses `build_paper_chat_prompt` (A3)

**Rollback:** set `CHAT_USE_PROMPT_BUILDER=false` to use `_build_system_prompt_legacy`.

**Still future:**
- Paper chat → PromptBuilder
- Optional: layer global `system_prompt` above `chat_system` (product decision)
- Title / memory extract / writing / compare/gaps registry migration (A3+)
- ModelRegistry streaming/tools (not required for assembly unification)

---

## Phase A parity decisions (locked)

1. **System layer:** `chat_system` only — do not prepend global `system_prompt`
2. **Shape:** flat `\n\n` join — no `##` section headers
3. **Memory:** all global + project facts (not MemoryEngine top-5)
4. **Paper chat:** deferred to A3
5. **Flag:** `CHAT_USE_PROMPT_BUILDER` (default true after cutover)

---

## Why ModelRegistry was not used for chat calls

`/api/chat` uses `client.responses.create()` (streaming, tools, vision).
Phase A only replaces **prompt assembly**, leaving that loop intact.
