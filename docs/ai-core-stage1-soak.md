# Stage 1 Paper Chat — soak runbook

**Parent plan:** [`v1-beta-rollout.md`](v1-beta-rollout.md) (deploy → shadow → pipeline → tag).  
**Goal:** Prove the pipeline before any Stage 2 behaviour change.  
**Do not** start IdentityPack / ResearchContext / regenerate-validator work until this checklist is green and the repo is tagged.

Canonical spec: [`ai-core-stage1-paper-chat.md`](ai-core-stage1-paper-chat.md)

---

## Freeze

Until soak passes:

- No Stage 2 prompt or grounding changes  
- No “while we’re here” architecture polish  
- Highest value = **parity evidence**, then **user-visible** work after the tag  

---

## Phase A — Shadow (first)

```bash
PAPER_CHAT_PIPELINE_ENABLED=shadow
```

Users still get the **legacy** stream. Pipeline builds a `PromptPlan` and logs hash parity only.

### Grep / monitor

| Signal | Log marker | Expect |
|--------|------------|--------|
| Prompt parity | `paper_chat_stage1_shadow` | `identical=True` (or `identical=true`) |
| Hashes only | same | `legacy_prompt_hash=…` `pipeline_prompt_hash=…` — **no** full prompt bodies |
| Plan failures | `paper_chat_stage1_plan_failed` | **zero** (auto-falls back to legacy) |
| Streaming / UX | product QA | indistinguishable from flag OFF |
| Exceptions | app error logs / SSE `error` | no new spike vs baseline |

Soak duration: enough Paper Chat traffic to trust the sample (staging continuously; optional small internal group).

**Exit criteria for Phase A**

- [ ] `identical=True` on essentially all shadow turns  
- [ ] No `paper_chat_stage1_plan_failed` (or investigated + fixed)  
- [ ] No streaming/UX regressions reported  
- [ ] No unusual exception rate on `/api/chat` paper conversations  

---

## Phase B — Pipeline ON (staging)

```bash
PAPER_CHAT_PIPELINE_ENABLED=true
```

Stream goes through `AIExecutor.stream_round` + observe-only validator stamps.

### Grep / monitor

| Signal | Log marker | Expect |
|--------|------------|--------|
| Exec stamps | `paper_chat_stage1_exec` | present every paper turn |
| Prompt version | `prompt_version=legacy_paper_chat_v1` | constant |
| Latency | `latency_ms=` | no material regression vs baseline (compare before/after) |
| Tokens | `tokens=` | sane; no unexplained inflation |
| Validator | `validator_ok=` / `validator_warnings=` | warnings OK; **no** answer rewrite |
| Streaming | product QA | deltas / stop / citations feel unchanged |

**Exit criteria for Phase B**

- [ ] Staging Paper Chat feels unchanged to testers  
- [ ] Latency/tokens within expected noise  
- [ ] Clean logs (no new error classes)  
- [ ] Validator warnings understood (observe-only; empty-answer warnings only when answer empty)  

---

## Phase C — Gradual production

1. Keep default **OFF** on prod until staging B is green  
2. Enable **shadow** on prod briefly if useful  
3. Enable **true** for a small allowlist / internal users  
4. Broad rollout after soak  
5. Leave legacy branch in place (do **not** delete in Stage 1)  

Rollback anytime:

```bash
PAPER_CHAT_PIPELINE_ENABLED=false
```

---

## Finish Stage 1 → tag

When A–C are clean (parity, no regressions, latency OK, logs/metrics stable):

```text
git tag -a v0.8-ai-core-stage1 -m "AI Core Stage 1 Paper Chat pipeline (behaviour-identical)"
```

That tag is the checkpoint before Stage 2 or other user-visible AI work.

**After the tag (not before):** user-visible improvements on top of the proven path — not more infrastructure for its own sake.

---

## Quick local check

```bash
# unit gates
python -m pytest backend/ai_core/test_paper_chat_stage1.py -q

# shadow smoke (staging env)
# set PAPER_CHAT_PIPELINE_ENABLED=shadow, ask a Paper Chat question,
# confirm logs contain paper_chat_stage1_shadow identical=True
```
