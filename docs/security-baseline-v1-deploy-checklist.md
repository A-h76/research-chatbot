# Security baseline V1 — deploy checklist

**Subsystem:** #20 Security baseline (V1)  
**Companions:** [`SECURITY_BASELINE_v1.0.md`](./SECURITY_BASELINE_v1.0.md) ·
[`auth-v1-deploy-checklist.md`](./auth-v1-deploy-checklist.md) ·
[`upload-worker-v1-deploy-checklist.md`](./upload-worker-v1-deploy-checklist.md) ·
[`.env.example`](../.env.example)

Engineering has wired fail-closed boot + shared rate limits + optional Sentry.
Ops must set env correctly before inviting closed-beta testers.

---

## 1. No `DEV_AUTO_LOGIN` in production

| Check | Expected |
|-------|----------|
| `FLASK_ENV` / `APP_ENV` | `production` |
| `DEV_AUTO_LOGIN` | **Unset / empty** |
| Boot with `DEV_AUTO_LOGIN=1` | Process exits (`security/startup.py`) |
| `/api/dev-login` | 403/404 when not (`DEV_AUTO_LOGIN` ∧ ¬production) |

Also covered by [`auth-v1-deploy-checklist.md`](./auth-v1-deploy-checklist.md) §1.

- [ ] Host env dump has no `DEV_AUTO_LOGIN`

---

## 2. ClamAV (upload virus scan)

| Mode | Env | Behavior |
|------|-----|----------|
| **Required (recommended)** | `CLAMAV_ENABLED=1` + reachable clamd | Uploads scanned; malware → quarantine |
| Risk accepted | `CLAMAV_OPTIONAL=1` (and ClamAV off) | Boot allowed; magic-byte MIME only |

Production **refuses boot** if ClamAV is off and `CLAMAV_OPTIONAL` is unset.

- [ ] Prefer `CLAMAV_ENABLED=1` with `CLAMAV_HOST`/`CLAMAV_PORT` or `CLAMAV_SOCKET`
- [ ] If optional: document who accepted the risk

---

## 3. Invite mode (closed beta)

| Check | Expected |
|-------|----------|
| `BETA_INVITE_ONLY` | `1` for closed beta |
| Invites / allowlist | Admin SPA `/admin/invites` and/or `ALLOWED_EMAILS` |

Details: [`auth-v1-deploy-checklist.md`](./auth-v1-deploy-checklist.md) §2.

- [ ] Uninvited register → `403 not_invited`
- [ ] At least one admin can open `/admin`

---

## 4. Redis limiter (multi-worker / multi-instance)

Flask-Limiter uses `REDIS_URL` when set so limits are **shared** across Gunicorn
workers and horizontally scaled web processes.

| Mode | Env | Behavior |
|------|-----|----------|
| **Required (recommended)** | `REDIS_URL=redis://…` reachable | Shared fixed-window limits |
| Single-process only | `RATE_LIMIT_MEMORY_OK=1` (no Redis) | Boot allowed; **memory://** — not safe with >1 worker/instance |

Production **refuses boot** if `REDIS_URL` is unset and `RATE_LIMIT_MEMORY_OK` is unset.
If `REDIS_URL` is set but unreachable → fail closed (existing behavior).

- [ ] Production has reachable `REDIS_URL` **or** explicit `RATE_LIMIT_MEMORY_OK=1`
- [ ] If scaling web replicas / `WEB_CONCURRENCY` > 1 → Redis is **mandatory**

Automated: `pytest security/test_startup.py -v`

---

## 5. Sentry (optional for closed beta; prefer before open Alpha)

| Check | Expected |
|-------|----------|
| Closed beta (~20 invitees) | May omit — Prometheus + security events still ship |
| Before open Alpha traffic | Set `SENTRY_DSN` (SDK init in `security/sentry_init.py`) |
| Traces | Optional `SENTRY_TRACES_SAMPLE_RATE` (default `0`) |
| Environment tag | Optional `SENTRY_ENVIRONMENT` (falls back to `APP_ENV` / `FLASK_ENV`) |

Boot never requires Sentry. Missing `sentry-sdk` with DSN set → warning log only.

- [ ] (Optional closed beta) `SENTRY_DSN` unset is OK
- [ ] (Before open Alpha) DSN set; confirm a test error appears in the project

---

## 6. Pre-invite operator pass (rollup)

- [ ] §1 `DEV_AUTO_LOGIN` absent
- [ ] §2 ClamAV enabled **or** optional risk acknowledged
- [ ] §3 `BETA_INVITE_ONLY=1` + invite/allowlist smoke
- [ ] §4 Redis for shared limits (or single-process ack)
- [ ] §5 Sentry decision recorded (omit vs wire)
- [ ] HTTPS termination (HSTS + Secure cookies) — see [`SECURITY_BASELINE_v1.0.md`](./SECURITY_BASELINE_v1.0.md)
- [ ] Smoke: login → upload PDF → search/RAG → writing path

---

*Out of V1:* Full pentest program, CSP report-uri pipeline, dependency SBOM CI as a platform program.
