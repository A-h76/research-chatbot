# `/api/chat` → Prompt Engine migration roadmap

Not attempted in this task — this is the plan for a later phase, plus a
stub (`server.py`'s `preview_chat_prompt_builder_migration()`) for
comparing old vs. new output without touching the live route. Read
alongside `docs/prompt-engine-architecture.md` (§11 already covers
`backend/upload`/`backend/search`'s integration; this extends that to
the one route deliberately left out there).

---

## 1. Why `/api/chat` wasn't touched in this task

`/api/chat` calls `client.responses.create()` directly — OpenAI's
Responses API, not `ModelRegistry.call()`. This was a deliberate,
previously-recorded decision (see the module's own comments at the
`_log_chat_cost()` call site), not an oversight: the route has real
capabilities `ModelRegistry`/`PromptBuilder` don't reproduce today —

- **Streaming** (SSE, token-by-token) — `ModelRegistry.call()` returns
  one complete result; there's a `_call_openai_streaming` path but
  nothing in `PromptBuilder`/`ModelRouter` accounts for a streaming
  response shape.
- **Multi-round tool-calling** (web search, citation-saving) — `/api/chat`
  runs its own loop over `input_items`/tool results; `ModelRegistry.call()`
  is one request in, one response out.
- **Vision** (image attachments) — not exercised anywhere in the Prompt
  Engine's message-building yet.

Swapping the model-call layer out from under those without first
building equivalent support would mean *dropping* web search,
citation-saving, and real-time streaming, not migrating them. That's a
bigger, separate piece of work than "point this route at PromptBuilder."

## 2. What's already true today (no new code needed to see it)

`/api/chat`'s current prompt assembly is `build_system_prompt(user,
project, memory_enabled)` (`server.py`), which does:

1. `_get_chat_system_opening(db)` — `PromptRegistry.get_prompt("chat_system")`
   with a hardcoded fallback string if that lookup fails.
2. `"The user's name is {user.name}."` + current date/time.
3. `user.custom_instructions`, if set.
4. `"Current project: {project.name}."` + `project.instructions`, if a
   project is active.
5. Global memories (`Memory.project_id IS NULL`) + project memories
   (`Memory.project_id == project.id`), each as a bullet list.

`PromptBuilder.build()`'s layers cover **1 and part of 4/5 already** —
System (same `chat_system` lookup via `SystemPromptManager`... actually
a *different* name, `system_prompt`, see §3), Project Context
(`project.description` + `project.instructions`), and Memory (same
global+project query, via `MemoryEngine`, verified to match exactly —
see `memory_engine.py`'s own docstring). **Not covered yet**: items 2
and 3, and half of item 4 (the `project.description` isn't part of
`/api/chat`'s current prompt at all, and `project.name`'s
`"Current project: ..."` framing isn't something `Project Context`
produces either). None of this is a design flaw in `PromptBuilder` — it
was never asked to cover "user identity" as a layer; it's just the
concrete list of what a real migration still has to account for.

## 3. The one naming collision to resolve first

`/api/chat`'s opening line comes from `PromptRegistry.get_prompt("chat_system")`
— a **different name** than `SystemPromptManager`'s fixed
`"system_prompt"` (see `system_prompt.py`). These are two different rows
in `prompt_versions` today. Migrating `/api/chat` onto `PromptBuilder`
means deciding, explicitly, which one governs `/api/chat`'s system
message going forward:

- **Option A** (recommended): keep them separate. `chat_system` is
  `/api/chat`'s own opening line (a chat-specific persona/tone), distinct
  from `SystemPromptManager`'s single global instruction meant for
  *every* prompt-engine task (RAG, analysis, chat alike). Migrating
  `/api/chat` onto `PromptBuilder` would mean calling `builder.build(...,
  task_name="chat_system", persona=...)` and layering the *global*
  system prompt **above** `chat_system`'s own opening as a `Persona`-like
  layer, not collapsing the two into one.
- **Option B**: retire `chat_system`, make the global `system_prompt`
  `/api/chat`'s only system content. Simpler, but loses `/api/chat`'s
  own distinct opening tone/persona unless that content gets folded into
  a dedicated `Persona` row instead (e.g. a "Chat Assistant" persona).

Not resolved here — a real product decision, not a technical one.

## 4. Phased plan

1. **Done, this task**: `PromptBuilder` proven end-to-end on a real route
   (`backend/search/routes.py`'s `rag_answer()`) and a real
   optional-but-adopted one (`backend/upload/routes.py`'s
   `analyze_document()`, model routing + audit logging only, not full
   assembly — see that route's own docstring for why).
2. **Next**: resolve §3's naming decision. Add the missing layers
   `/api/chat` needs and `PromptBuilder` doesn't have yet — user
   identity/date and `custom_instructions` most naturally become their
   own layer (call it "User Context", inserted after Persona) rather
   than overloading Project Context or Memory for content that isn't
   either.
3. **Next**: decide streaming's fate. Either (a) teach `ModelRegistry`
   a real streaming call path and reroute `/api/chat` through it, which
   unblocks a full switch, or (b) keep `client.responses.create()` as
   the model-call layer permanently and *only* replace the
   prompt-assembly half (`build_system_prompt()` → `PromptBuilder.build().final`),
   leaving the streaming/tool-calling loop untouched. (b) is
   meaningfully smaller and doesn't require solving streaming inside the
   Prompt Engine at all — worth strongly considering as the actual
   target rather than a stepping stone.
4. **Next**: web search / tool-calling and vision — audit whether either
   actually needs anything from `PromptBuilder` (they may not; tool
   definitions and image parts are message-shape concerns, not prompt-text
   concerns, and could stay exactly as they are regardless of where the
   system-prompt text comes from).
5. **Last**: cut `/api/chat` over, behind a feature flag if the risk
   profile at the time warrants one (this route is the highest-traffic
   one in the app — brain.md's route inventory lists it as the core chat
   path). Roll back by flipping the flag, not by reverting code, if
   anything looks wrong in the first real traffic.

## 5. Testing this migration when it happens

- Diff `preview_chat_prompt_builder_migration()`'s legacy vs. candidate
  output for a sample of real users/projects before switching anything —
  the stub returns both side by side plus the specific fields
  `PromptBuilder` doesn't cover yet, precisely so that diff is possible
  without guessing.
- Everything `PromptBuilder` itself does is already covered by
  `backend/ai/test_prompt_builder.py`'s 20 tests — a `/api/chat`
  migration doesn't need to re-test assembly correctness, only that
  `/api/chat`'s own remaining pieces (streaming, tool loop, vision,
  cost logging) still work with `PromptBuilder`-sourced text substituted
  in for `build_system_prompt()`'s output.
