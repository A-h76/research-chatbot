# Security Baseline Report — PR1

**Date:** 2026-07-26  
**Scope:** Production secrets fail-closed, Redis-backed rate limiter, critical route limits, security event logging  
**Status:** Complete (PR1 only — PR2 not started)

---

## Changes delivered

### 1. Production secrets (fail-closed)
- New module: `security/startup.py`
- On `FLASK_ENV`/`APP_ENV=production`, startup **refuses** if:
  - `DEV_AUTO_LOGIN` is set
  - `FLASK_SECRET_KEY` missing
  - `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` missing
  - R2 selected/configured without R2 credentials
- Development may still use an ephemeral key with a warning
- `storage/manager.py` LocalProvider no longer silently invents secrets in production

### 2. Rate limiting + Redis
- Limiter storage: `REDIS_URL` when reachable; else `memory://`
- Production + `REDIS_URL` set but unreachable → **fail closed**
- New / tightened limits:

| Route | Limit |
|-------|--------|
| `POST /api/chat` | 60 / minute |
| `POST /api/files` | 60 / hour |
| `POST /api/uploads/presign` | 60 / hour |
| `POST /api/uploads/confirm` | 60 / hour |
| `POST /api/documents/upload` | 60 / hour |
| `POST /api/documents/<id>/analysis` | 20 / hour |
| `POST /api/uploads/bulk` | 20 / hour |
| `GET /auth/google` | 30 / hour |
| `GET /auth/callback` | 60 / hour |
| `POST /auth/magic-link/verify` | 20 / hour |
| Magic-link request | 3 / hour (existing) |
| Support / writing / compare / gaps | existing limits kept |

### 3. Security logging
- `rate_limit_exceeded` on 429 (path, method, user_id, remote)
- `oauth_denied` when allowlist blocks Google OAuth
- `magic_link_verify_failed` / `magic_link_denied` on verify failures
- Quota exceeded warnings (`event=quota_exceeded`) on JWT upload, analysis token check, and bulk upload

### 4. Explicit non-changes
- No Phase 1 / Phase 2 / PromptBuilder behavior changes
- No CSP / MIME / ClamAV / metrics auth (PR2+)
- No session TTL changes (PR4)
- **PR2 not started**

---

## Test evidence (2026-07-26)
```
87 passed — security/test_startup.py, security/test_pr1_limits.py,
backend/upload/test_upload.py, backend/upload/test_bulk.py,
test_chat.py, auth/test_magic_link.py, auth/test_auth.py
```

---

## Files touched
- `security/__init__.py`, `security/startup.py`, `security/test_startup.py`, `security/test_pr1_limits.py`
- `server.py`
- `storage/manager.py`
- `auth/magic_link.py`
- `backend/upload/routes.py`, `backend/upload/bulk.py`
- `.env.example`

---

## Residual risk (deferred)
- `/metrics` still public → PR2  
- Magic-byte MIME + ClamAV → PR3  
- CSP / session absolute idle TTL → PR4  
- Upload `project_id` ownership → PR2  

---

## Ops checklist before production
1. Set `FLASK_SECRET_KEY` (and optionally `JWT_SECRET_KEY`)
2. Set Google OAuth secrets; leave `DEV_AUTO_LOGIN` unset
3. Prefer `REDIS_URL` for multi-worker rate-limit sharing
4. Confirm R2 env vars if using object storage
