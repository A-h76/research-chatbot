# Security Baseline Report — PR4

**Date:** 2026-07-26  
**Scope:** Security headers, CSP Report-Only, session idle/absolute TTL  
**Status:** Complete (PR4 — production hardening slice series finished)

---

## Changes delivered

### 1. Baseline security headers (all environments)
Applied on every response via `after_request`:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()`
- `X-XSS-Protection: 0`

### 2. HSTS (production only)
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`

### 3. CSP Report-Only
- **Production:** `Content-Security-Policy-Report-Only` with a same-origin SPA policy (allows `https:` images for Google avatars, `data:`/`blob:` previews, `'unsafe-inline'` styles for KaTeX/markdown)
- **Development:** omitted by default (Vite HMR-safe); enable with `CSP_REPORT_ONLY=1`
- Disable: `CSP_REPORT_ONLY_DISABLE=1`
- Override: `CSP_REPORT_ONLY_POLICY=...`
- **Not enforced** (Report-Only only) — no blocking CSP yet

### 4. Session TTL
- Idle default: **60 minutes** (`SESSION_IDLE_MINUTES`)
- Absolute default: **12 hours** (`SESSION_ABSOLUTE_HOURS`)
- Set either to `0` to disable that check
- Login stamps `_session_started_at` / `_session_last_activity_at` (OAuth, magic link, dev login)
- Pre-PR4 sessions bootstrap stamps on first request (no mass logout)
- Expiry clears session, logs `session_expired`, returns `401` for `/api/*` or redirect to login
- Logout clears session and logs `logout`
- Flask `PERMANENT_SESSION_LIFETIME` aligned to absolute hours

### 5. Explicit non-changes
- No Phase 1/2 / PromptBuilder changes
- No enforced (blocking) CSP
- No frontend asset changes required for Report-Only

---

## Test evidence
```
38 passed — security/test_headers.py, test_session_ttl.py,
test_pr4_headers_session.py, test_startup.py, test_pr1_limits.py,
test_pr2_metrics.py, auth/test_magic_link.py
```

---

## Files touched
- `security/headers.py`, `security/session_ttl.py` + tests
- `server.py`, `auth/magic_link.py`
- `.env.example`
- `docs/SECURITY_BASELINE_PR4.md`

---

- Residual / follow-ups
- Review CSP reports in prod, then consider enforcing CSP  
- ~~Step-up reauth for account deletion~~ → done (#16, `security/ops/step_up.py`)  
- Optional `CSP report-uri` / report-to endpoint  

---

## Ops checklist
1. Confirm HTTPS termination so HSTS is appropriate  
2. Tune `SESSION_IDLE_MINUTES` / `SESSION_ABSOLUTE_HOURS` for your threat model  
3. Collect CSP Report-Only violations before flipping to enforce  
