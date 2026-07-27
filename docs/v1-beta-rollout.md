# V1 Beta — controlled production rollout

**Frame:** Version 1 Beta — validate the whole product with real users.  
**Not:** more architecture, Writing/Compare/Gaps, or Stage 2 Identity until this path is proven.

Paper Chat Stage 1 flag stays **behaviour-identical**. Rollback = env only:

```bash
PAPER_CHAT_PIPELINE_ENABLED=false
```

Detailed Paper Chat soak signals: [`ai-core-stage1-soak.md`](ai-core-stage1-soak.md) · Spec: [`ai-core-stage1-paper-chat.md`](ai-core-stage1-paper-chat.md)

---

## Phase 1 — Deploy to production (now)

Ship current codebase with:

```bash
PAPER_CHAT_PIPELINE_ENABLED=false
```

**Verify the deployment itself (not the AI pipeline):**

- [ ] Authentication (login / session / JWT as you use in prod)
- [ ] Uploads
- [ ] Paper processing (worker + job completion)
- [ ] RAG retrieval on a known paper
- [ ] Database migrations applied
- [ ] Background workers healthy (`GET /api/worker/health`)
- [ ] Streaming chat (general + paper)
- [ ] Logging reachable for ops

Exit: prod is healthy on the **legacy** Paper Chat path.

---

## Phase 2 — Shadow mode

```bash
PAPER_CHAT_PIPELINE_ENABLED=shadow
```

Users still get the legacy stream. Low risk.

**Monitor for days (match your traffic):**

- Errors / `paper_chat_stage1_plan_failed`
- Latency (baseline)
- Token / cost signals (existing cost ledger)
- Prompt parity → `paper_chat_stage1_shadow` `identical=True`
- Validator is N/A on legacy stream; watch plan-build exceptions only

Exit: shadow clean → Phase 3.

---

## Phase 3 — Enable the pipeline

```bash
PAPER_CHAT_PIPELINE_ENABLED=true
```

**Monitor:**

- Response quality (spot-check)
- Streaming stability
- API cost vs Phase 1/2
- User feedback
- `paper_chat_stage1_exec` (latency_ms, tokens, validator_*)

Anything odd → set flag back to `false` (no code rollback).

When Phase 3 is stable: tag **`v0.8-ai-core-stage1`**, then consider Stage 2 / next features guided by usage.

---

## Before announcing publicly

| Basics | Notes in this repo |
|--------|--------------------|
| HTTPS | Deploy/platform concern — confirm at host |
| Env vars | `.env.example`; production secret checks at startup |
| DB backups | Ops — confirm schedule before invite |
| Error monitoring (Sentry etc.) | Confirm if wired in your deploy; add if missing before broad invite |
| Request + AI logs | App logs + `paper_chat_stage1_*` + cost rows |
| Rate limiting | Flask-Limiter on `/api/chat` and others |
| File upload limits | `MAX_FILE_MB` / `MAX_DOCUMENT_UPLOAD_MB` + quotas |
| Health check | `GET /api/worker/health` (worker); confirm process liveness at edge |
| Basic analytics | Cost/usage ledgers + simple product questions below |

---

## What this beta is for

Enough already shipped for real feedback:

Auth · Projects · Upload · Paper processing · RAG · AI orchestration · Paper Chat · flags · observability

Use the beta to answer:

1. Do users actually use Paper Chat?  
2. Which prompts work?  
3. Where do they get stuck?  
4. What do they ask for next?  
5. AI cost per active user?

Those answers beat another month of architecture.

**After validation:** Stage 2 (Identity + ResearchContext), then Writing / Compare / Gaps — prioritized by what users actually need.
