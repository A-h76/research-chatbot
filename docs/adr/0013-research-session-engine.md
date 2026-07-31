# ADR-0013: Research Session Engine (W7 contract — not implemented)

Status: proposed  
Date: 2026-08-01  
Roadmap alias: product discussions sometimes called this “ADR-0006”; that
number is already taken by `0006-research-intelligence-staged-pipeline.md`.
This ADR is the sequential repo id for the Research Session Engine.

**Do not implement yet.** Capture ownership, lifecycle, and contracts so W1–W6
remain a stable beta surface while researchers validate the Ask → Scope →
Retrieve → Synthesize → Verify → Extract/Write loop.

## Context

W1–W6 shipped a coherent research *workflow* without a persistent session hub:

| Week | Capability | Persistence today |
|------|------------|-------------------|
| W1–W2 | Trust Chat cites + unified retrieve | Message.sources envelope |
| W3–W4 | Skills + grounding | Grounding blob on message |
| W5 | Structured extract tables | Derived from Phase-1 (no new store) |
| W6 | Lit-review / theme-map jobs | `upload_jobs` + outbox result event |

That is enough for beta validation. Introducing a **Research Session** now
risks freezing the wrong hub before we know whether researchers want:

- Chat as the home, or
- Compare / Writing / Project as the home, or
- A new Session surface that owns scope across all of them.

W6 deliberately stores job results on the outbox (`research_job.result`) rather
than a dedicated history table — **durable multi-turn research state is a W7
concern**, not something to smuggle into job polling.

## Decision (proposed — freeze contracts, defer code)

**When W7 starts**, introduce a first-class `ResearchSession` that owns scope
and links turns/jobs across tools. Until then:

1. Keep `ResearchScope.session_id` nullable / reserved (already named in W1).
2. Do not add session tables, routes, or UI hubs.
3. Do not promote outbox job results into “session history.”
4. Validate W1–W6 with real researchers first.

### Ownership

| Concern | Owner |
|---------|--------|
| Who can open a session | Project member (same authz as project evidence) |
| Scope (paper / project / collection / web) | Session snapshot + per-turn overrides |
| Turns (chat, extract, jobs) | Append-only session events referencing existing entities |
| Writing drafts | Remain `WritingDocument`; session *links*, does not fork content |
| Evidence objects | Remain Evidence Layer; session never invents evidence |

### Lifecycle (proposed)

```text
draft → active → parked → archived
         │
         └─ cancelled (user abandon; soft)
```

- **draft**: scope chosen, no turns yet  
- **active**: at least one turn or job  
- **parked**: user paused; still resumable  
- **archived**: read-only; not shown in default lists  

### Contracts (proposed shapes — not shipped)

**ResearchSession**

```json
{
  "id": 1,
  "project_id": 9,
  "user_id": 3,
  "title": "Metformin glycemic control",
  "status": "active",
  "scope": {
    "mode": "project",
    "file_id": null,
    "collection_id": null,
    "web": "off",
    "session_id": 1
  },
  "created_at": "…",
  "updated_at": "…"
}
```

**SessionEvent** (append-only)

```json
{
  "session_id": 1,
  "kind": "chat_turn | extract_table | theme_map | literature_review | note",
  "ref": {
    "conversation_id": 12,
    "message_id": 44,
    "job_id": 88,
    "document_id": null
  },
  "payload_summary": { "skill": "synthesize", "confidence": 0.71 },
  "created_at": "…"
}
```

Rules:

- Events reference existing rows; they do not duplicate message bodies or
  writing drafts.
- Job results may be *linked* (`job_id`) once a dedicated result store exists;
  until then W6 outbox results remain poll-only.
- `ResearchScope.session_id` becomes required for session-originated turns;
  global chat / paper chat without a session stay valid (scope.session_id null).

### Persistence (deferred)

Preferred when implementing:

1. `research_sessions` + `research_session_events` (migration + models on
   `server.py` Base, factory blueprints — no `import server` from packages).
2. Optional later: promote W6 `research_job.result` outbox payloads into a
   `research_job_runs` table *owned by the session*, not by UploadJob alone.

Rejected for W7 v1:

- Replacing Chat or Writing Studio with the session UI
- Storing full LLM transcripts only inside the session (keep Message / Document)
- Building W8 (hypotheses / consensus memory) inside the first session ship

## Alternatives considered

- **Implement session now as part of W6.** Rejected — conflates job execution
  with durable research state; blocks beta learning.
- **Use Conversation as the session.** Tempting, but paper chat, project
  inquiry, and Writing Studio already fork conversation semantics; a session
  that spans tools needs its own identity.
- **Use Project as the session.** Too coarse — one project has many research
  threads (gaps, drafts, compares).

## Consequences

- W1–W6 remain the beta surface; no schema migration for sessions yet.
- Frontend may keep `scope.session_id` optional in types (already reserved).
- Next engineering step after researcher validation: accept this ADR, then
  implement Session + Events only — still not W8 Research Intelligence.

## Acceptance for this ADR (documentation only)

- [x] Ownership named  
- [x] Lifecycle named  
- [x] Session + Event contracts sketched  
- [x] Persistence deferred explicitly  
- [x] No W7 implementation in this change set  

## Related

- Research loop W1–W8 sequence (product)  
- `backend/research/scope.py` (`session_id` reserved)  
- ADR-0006 Research Intelligence staged pipeline (different concern)  
- ADR-0001 Postgres worker / outbox (W6 reuse)  
