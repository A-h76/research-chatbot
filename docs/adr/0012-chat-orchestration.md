# ADR-0012: Chat orchestration layer boundaries

Status: accepted  
Date: 2026-07-30

## Context

Mechanical extraction of `server.py` route clusters (Writing, Files, Search,
Analysis, Conversations, Memories) reduced the monolith from ~7399 to ~5445
lines without behavior change. The remaining `/api/chat` handler is different:

- It is ~500 lines acting as an **orchestrator**, not a single HTTP concern.
- Responsibilities currently mixed in one function:
  1. Request gate (auth, limits, AI gate)
  2. Conversation / project load and authz
  3. Attachment binding
  4. Prompt assembly (general + paper-chat / Stage-1 pipeline)
  5. Retrieval (RAG, web search tools)
  6. SSE token/event streaming
  7. Side effects (persist message, cost ledger, title, memory extract)
- Moving all of it into `chat_routes.py` would recreate a god module under a
  new name — the opposite of the extraction campaign's purpose.
- Ordinary unit tests do not cover SSE regressions (latency, cancellation,
  reconnect, token streaming, error propagation, client disconnect).

ADR-0002 already freezes AI Core layering for Paper Chat executors. This ADR
defines how the **session chat HTTP path** (`POST /api/chat`) must be split
before any code move, so extraction does not fight that boundary.

## Decision

**Do not relocate `/api/chat` as a monolithic blueprint.**  
Refactor it into preparation, orchestration, streaming, and event-driven
completion side effects — with a thin HTTP/SSE route and an explicit
`ToolExecutor` port for growing tool surface area.

```text
HTTP Request
    ↓
ChatPreparationService
    ↓
ChatOrchestrator
    ↓
ToolExecutor          (when tools are selected)
    ↓
ChatStreamService
    ↓
ChatCompleted event
    ↓
Side-effect handlers (save, cost, memory, analytics, …)
```

### 1. ChatPreparationService

(Formerly informal “request service” — renamed so the role stays clear:
validate, authorize, load conversation, bind files, build turn context.)

Owns:

- authentication / session user
- rate limits and message-size validation
- `ai_gate.preflight`
- conversation lookup and ownership
- project lookup and authz
- attachment binding (conversation/project)

Must not: call models, assemble prompts, emit SSE, execute tools, or own
post-stream side effects.

### 2. ChatOrchestrator

Owns the brain:

```text
Prompt → Retrieval → Reasoning → Tool selection → Model selection
```

Produces a plan / turn context for the streamer (system prompt, history,
retrieval context, selected tools, model params, paper-chat plan if any).

Delegates tool *execution* to `ToolExecutor` — orchestrator selects and
sequences; it does not permanently embed every tool body.

Must not: know SSE framing, Flask `Response`, or HTTP status codes.  
Must not: own persistence of the final assistant message.

Aligns with ADR-0002: orchestration may consume `ai_core` plans/executors;
it must not embed provider SDK streaming details.

### 3. ToolExecutor

Owns running selected tools (today: web search, RAG-adjacent helpers;
tomorrow: Zotero, Mendeley, citation lookup, Reviewer, Knowledge Graph,
export, …).

Receives tool calls from the orchestrator / stream loop via a narrow port.
Returns structured results into the turn context.

Must not: assemble system prompts, choose models, or emit SSE.

### 4. ChatStreamService

Owns only:

```text
model → tokens → events → SSE sink
```

Consumes an already-built orchestration plan. Emits stream events
(`status`, `delta`, `done`, `error`) to a caller-supplied sink.

Must not: assemble prompts, query permissions, or open its own ORM sessions
for business state. Tool I/O goes through `ToolExecutor` / injected ports.

### 5. Completion side effects (event-driven)

On terminal stream state, emit a domain event (e.g. `ChatCompleted`) rather
than a monolithic sequential service body:

```text
ChatCompleted
    ↓
Handlers
    - PersistAssistantMessage
    - CostLedger
    - TitleGeneration
    - MemoryExtraction
    - Analytics / ops
    - Reviewer (future)
    - …
```

First implementation may dispatch handlers in-process; target shape is
outbox / worker jobs so handlers stay independently retryable.

Today’s daemon-thread `extract_memories` is an interim acceptable shape
until outbox/worker owns it.

### Thin HTTP layer

`create_chat_blueprint` (future) may only:

- parse JSON body
- open the request-scoped DB session (see Transaction boundary)
- call Preparation → Orchestrator → Stream
- wrap the stream sink as SSE
- publish `ChatCompleted` (or equivalent) on terminal states
- apply Flask rate-limit / login decorators

### Transaction boundary

```text
The HTTP layer opens the request-scoped database session.

Services receive repositories or session abstractions via dependency
injection.

No service creates its own ORM session except isolated background jobs
(outbox workers / daemon side-effect handlers that opt into their own
unit of work).

The request commits or rolls back once for request-scoped work.
```

This prevents transaction fragmentation across preparation, streaming,
and accidental nested sessions.

### Dependency rule

```text
ChatPreparationService
  may depend on → Repositories / session abstractions

ChatOrchestrator
  may depend on → Retriever, PromptBuilder, ModelRouter, ToolExecutor
                  (and ADR-0002 ai_core plan types)

ToolExecutor
  may depend on → Tool adapters / external clients / repositories as needed
                  for that tool only

ChatStreamService
  may depend on → Model SDK / stream client only (+ ToolExecutor port for
                  mid-stream tool rounds)

Completion handlers
  may depend on → Repositories, Queue/Outbox, Ledger, Analytics

No reverse dependencies are allowed.
(StreamService must not import Orchestrator; Orchestrator must not import
Flask; handlers must not import StreamService.)
```

### Sequence (happy path)

```text
User
  → POST /api/chat
  → ChatPreparationService   (validate, authz, load, bind)
  → ChatOrchestrator         (retrieve, prompt, model/tools)
  → ToolExecutor             (as needed)
  → ChatStreamService        (model tokens → SSE events)
  → Client                   (SSE)
  → ChatCompleted handlers   (save, cost, memory, analytics, …)
```

## Alternatives considered

1. **Move entire `chat()` into one blueprint (mechanical extraction)**  
   Rejected: preserves accidental complexity; new god module; high SSE risk
   for zero architectural gain.

2. **Three layers (Preparation / Orchestrator+Stream / Side effects)**  
   Rejected: streaming and orchestration stay coupled; SSE tests still force
   re-running prompt/retrieval logic.

3. **Four+ layers with ToolExecutor and event-driven completion (this ADR)**  
   Chosen: matches observed responsibilities; tools can grow without
   bloating the orchestrator; completion handlers remain independently
   extensible; keeps ADR-0002 executor boundary intact.

4. **Do nothing / leave chat in `server.py` indefinitely**  
   Acceptable until a focused SSE-validation window exists. Long-term
   rejected because chat remains the largest behavioral hotspot in the
   entrypoint.

## Consequences

- `/api/chat` stays in `server.py` until implementation follows this ADR.
- Do **not** implement this split opportunistically; schedule focused time
  for SSE checklist validation before deleting the inline path.
- Platform work for Track 2 is **done** (A-401 Reviewer persistence, A-402
  Evidence API freeze, A-403 Ranking/Consensus, A-404 Job observability,
  A-405 Documentation freeze). Chat split remains independent and deferred.
- Remaining low-risk mechanical extractions (account/export/support) may
  continue independently; chat is design-gated, not line-count-gated.
- Implementation order when scheduled:
  1. Extract pure helpers behind service interfaces (behavior parity)
  2. Wire thin route without changing SSE event contract
  3. Run SSE checklist: latency, cancellation, reconnect, token streaming,
     error propagation, client disconnect
  4. Only then remove the inline path

## Cost / Security / Observability / Extensibility

- **Cost:** Unchanged at first; CostLedger handler is the home for richer
  usage writes without touching the streamer.
- **Security:** PreparationService owns authz gates; StreamService must not
  broaden data access beyond orchestrator-supplied context.
- **Observability:** Latency becomes measurable per phase (prep / orchestrate /
  stream / handlers), not one opaque handler.
- **Extensibility:** New tools plug into ToolExecutor; new post-turn work
  plugs into ChatCompleted handlers without SSE changes.

## Non-goals

- Rewriting the OpenAI Responses streaming protocol or SSE event names.
- Migrating all chat to `ai_core` in one step (Paper Chat Stage-1 already
  uses `AIExecutor` under flag; general chat migrates incrementally).
- Fully async/outbox-backed handlers in the first implementation slice
  (event shape first; queue transport second).

## Rollback

If a partial service extraction regresses SSE behavior:

1. Re-point the route at the previous inline `chat()` / generate path.
2. Keep new service modules unused until parity is restored.
3. Do not delete the inline path until the SSE checklist is green.

## Acceptance criteria (before implementation is considered done)

- [ ] Preparation, Orchestrator, ToolExecutor, StreamService, and completion
      event/handlers exist under `backend/chat/` (or agreed package)
- [ ] HTTP blueprint contains no prompt/retrieval/tool business logic
- [ ] No service imports Flask `request`, `Response`, `current_app`, or `g`
      (framework stays isolated to the HTTP blueprint)
- [ ] SSE event contract unchanged vs current clients
- [ ] SSE checklist documented and executed against staging or local harness
- [ ] No `import server` from chat services
- [ ] Transaction boundary respected (request-scoped session; no ad-hoc
      sessions in request-path services)
