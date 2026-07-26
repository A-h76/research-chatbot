# Security Baseline Report — PR2

**Date:** 2026-07-26  
**Scope:** Authorization residuals (project ownership) + Prometheus metrics protection  
**Status:** Complete (PR2 only — PR3 not started)

---

## Changes delivered

### 1. Metrics protection
- `GET /metrics` gated via `security/metrics_access.py`:
  - `METRICS_TOKEN` set → require `Authorization: Bearer <token>`
  - Token unset → **loopback only** (`127.0.0.0/8`, `::1`)
  - Escape hatch: `METRICS_ALLOW_UNAUTHENTICATED=1` (dev only)
- Denied scrapes emit `metrics_access_denied` security events
- Worker Prometheus bind defaults to `127.0.0.1` (`WORKER_METRICS_BIND`)

### 2. Project ownership (authz)
- Helper: `security/authz.py` (`resolve_owned_project_id`, `project_owned_by_user`)
- Enforced / logged on:
  - `POST /api/files` (session upload)
  - `POST /api/uploads/presign`
  - `POST /api/chat` project load
  - `POST /api/citations/from-paper/<id>`
  - `POST /api/conversations` (+ inherit from paper)
  - `POST /api/notes`, `POST /api/citations`
- Unowned `project_id` is **not** persisted (cleared); `authz_denied` logged
- Legacy chat assembler (`_build_system_prompt_legacy`) drops cross-owned projects when `CHAT_USE_PROMPT_BUILDER=false`

### 3. Explicit non-changes
- No PromptBuilder `build_chat_instructions` behavior change
- No Phase 1 / Phase 2 AI pipeline changes
- No MIME / ClamAV (PR3)
- No CSP / session TTL (PR4)
- `/api/worker/health` remains public (ops liveness by design)

---

## Test evidence
```
48 passed — security/test_authz.py, security/test_metrics_access.py,
security/test_pr2_metrics.py, security/test_startup.py,
security/test_pr1_limits.py, observability/test_observability.py,
test_worker_health.py, test_chat.py
```

---

## Files touched
- `security/authz.py`, `security/metrics_access.py`, tests
- `server.py`
- `worker.py`
- `observability/metrics.py`
- `.env.example`
- `docs/SECURITY_BASELINE_PR2.md`

---

## Residual risk (deferred)
- Magic-byte MIME + optional ClamAV → PR3  
- CSP / session absolute+idle TTL → PR4  
- Notes/citations PATCH already ownership-checked; list filters still rely on `user_id` row scope  

---

## Ops checklist
1. Set `METRICS_TOKEN` for non-loopback Prometheus scrapers  
2. Keep `WORKER_METRICS_BIND=127.0.0.1` unless a sidecar needs another interface  
3. Never set `METRICS_ALLOW_UNAUTHENTICATED` in production  
