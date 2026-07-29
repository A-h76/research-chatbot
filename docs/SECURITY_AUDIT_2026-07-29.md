# Security Audit — 2026-07-29 (Phase 1)

**Status:** Phases 1–4 implemented; **baseline frozen** → `docs/SECURITY_BASELINE_v1.0.md`  
**Scope:** Flask + React + worker + evidence/writing/AI  
**Method:** Static review (`server.py`, `security/`, `auth/`, upload/search/evidence/library, frontend API client)  
**Next:** No broad security programs — Evidence-backed Literature Review + 20-user beta. Exceptions only per Security Baseline freeze rule.

---

## Phase 4 status (2026-07-29)

Implemented deferred Medium/High hygiene:

- [x] F8.1 — CSP **enforced** in production by default; `CSP_REPORT_ONLY=1` rollback; `CSP_DISABLE=1`
- [x] F1.4 — Library OAuth tokens sealed at rest (`enc:v1:` via itsdangerous; legacy plaintext passthrough)
- [x] F6 — Production requires `CLAMAV_ENABLED=1` unless `CLAMAV_OPTIONAL=1`
- [x] Shared request validation (`security/request_validation.py`) on high-risk writes: ops register/login, RAG body, library Zotero/Mendeley import

Still deferred (later):

- Migrate **all** write endpoints onto shared validation
- Dependency / supply-chain CI scanning

Tests: `tests/test_security_phase4.py`, `security/test_headers.py`, `security/test_startup.py`

**Deploy notes:** set `CLAMAV_ENABLED=1` (or `CLAMAV_OPTIONAL=1`); if SPA breaks under CSP use `CSP_REPORT_ONLY=1`; re-connect Zotero/Mendeley so new tokens are sealed.

---

## Phase 3 status (2026-07-29)

Implemented Medium items:

- [x] CSRF covers `/auth/*` as well as `/api/*`
- [x] Single-use magic-link tokens (`magic_link_tokens` + migration 0034)
- [x] Magic-link rate limits: email **and** IP
- [x] Production requires `OPENAI_API_KEY`; warns if Resend missing
- [x] PromptBuilder fail-closed without matching `user_id` for project context
- [x] Chat message length cap (32k)
- [x] Dev email logs redact magic-link tokens
- [x] Expanded `.gitignore` for `.env.*`, keys, credentials
- [x] Persist more security events (csrf, jwt revoke, rate limit, magic verify)

---

## Phase 2 status (2026-07-29)

Implemented P0:

- [x] F2.1 — JWT ``sv`` claim + refresh/access reject after logout-all
- [x] F2.2 — `/api/dev-login` requires `DEV_AUTO_LOGIN and not IS_PRODUCTION`
- [x] F10.4 — RAG/search limiter + `ai_gate` + query length caps
- [x] `.env.example` — `DEV_AUTO_LOGIN` default blank
- [ ] OPS — rotate any Resend/API keys exposed outside `.env` (manual)

Tests: `tests/test_security_phase2.py`, existing search/auth suites.

---

## Executive summary

Foundations are strong (prod secret boot checks, session TTL + versioning, ownership helpers, magic-byte uploads, CSRF on `/api/*`, metrics gating, AI kill switch on chat). Highest residual risks:

1. **JWT refresh survives logout-all** (no `session_version` in JWT)
2. **`/api/dev-login` gated only by env var** (not `not IS_PRODUCTION`)
3. **`/api/rag` + JWT document search ungated** (no rate limit, no `ai_gate`)
4. **ClamAV off by default** in production
5. **Ops:** rotate any keys exposed outside `.env`; Redis for multi-worker limits

---

## Existing strong controls

| Area | Control |
|------|---------|
| Secrets boot | `security/startup.py` — refuses prod without secrets; blocks `DEV_AUTO_LOGIN` when `IS_PRODUCTION` |
| Sessions | HttpOnly, SameSite=Lax, Secure in prod; idle/absolute TTL; cookie `session_version` |
| CSRF | Origin/Referer allowlist on state-changing `/api/*` |
| Headers | nosniff, frame-deny, Referrer-Policy, Permissions-Policy, HSTS (prod); CSP enforce (prod; Report-Only rollback) |
| Authz | `user_id` filters; evidence `require_owned_*`; RAG scoped by owner |
| Uploads | Extension allowlist, magic bytes, size caps, `secure_filename`; ClamAV when enabled |
| Magic link | Non-enumerating responses; rate limits; 15m expiry |
| AI chat | `ai_gate.preflight` + limiter |
| Frontend | No provider API keys; Bearer from server |
| `.env` | Gitignored |

---

## Priority matrix (Phase 2 input)

| Pri | ID | Title | Severity |
|-----|-----|-------|----------|
| **P0** | F2.1 | JWT refresh / access ignore `session_version` after logout-all | High |
| **P0** | F2.2 | `/api/dev-login` missing `not IS_PRODUCTION` check | Critical* |
| **P0** | F10.4 | Ungated `/api/rag` + `/api/documents/search` (cost/DoS) | High |
| **P0** | OPS | Rotate keys that appeared in chat/screenshots; verify Resend key in `.env` | High |
| P1 | H2 | Prod boot does not require `OPENAI_API_KEY` / Resend when magic-link on | High |
| P1 | H3 | Rate-limit keys: prefer IP+user; magic-link email-only bypass; Redis for multi-worker | High |
| P1 | F1.2 | `.env.example` defaults `DEV_AUTO_LOGIN=1` | Medium–High |
| P1 | F6 | ClamAV fail-open by default | High (prod malware) |
| P1 | F4.1 | Cap chat/RAG query length at HTTP edge | Medium |
| P1 | §9 | Trust `X-Forwarded-For` only behind stripping proxy | Medium |
| P2 | F2.3 | CSRF does not cover `/auth/*`; missing Origin passes | Medium |
| P2 | F2.4 | Magic-link tokens reusable until expiry | Medium |
| P2 | F2.5 | `/api/auth/token` unthrottled | Medium |
| P2 | F1.4 | Library OAuth tokens plaintext at rest | High if DB breached |
| P2 | F8.1 | CSP Report-Only only | Medium |
| P2 | F10.1 | Prompt injection residual | Medium |
| P2 | F3.2 | PromptBuilder project inject if `user_id` omitted | Medium (latent) |
| P2 | F1.1 | `.gitignore` only `.env` (not `.env.local` / pem) | Medium |
| P3 | Logging persist gaps, prompt template disclosure, health info | Low–Medium |

\*Critical only when `DEV_AUTO_LOGIN` is set and host is **not** flagged production.

---

## Detailed findings (High / Critical)

### F2.1 — JWT refresh survives logout-all

- **Files:** `server.py` (`POST /api/auth/token`), JWT issuance, `revoke_all_sessions`
- **Issue:** Cookie sessions honor `session_version`; JWTs do not embed/check it.
- **Exploit:** Stolen refresh token (~30d) works after password reset / logout-all.
- **Fix:** Embed `sv` claim; reject stale; optional refresh jti store.
- **Likelihood:** Medium | **Priority:** P0

### F2.2 — `/api/dev-login` incomplete gate

- **Files:** `server.py` ~`POST /api/dev-login`
- **Issue:** Checks `DEV_AUTO_LOGIN` presence; login **page** also checks `not IS_PRODUCTION`, endpoint may not.
- **Exploit:** Mis-set `FLASK_ENV` + `DEV_AUTO_LOGIN=1` on public host → instant session as `dev@localhost`.
- **Fix:** `if not (DEV_AUTO_LOGIN and not IS_PRODUCTION): 404/403`; never register in prod builds.
- **Likelihood:** Medium | **Priority:** P0

### F10.4 — Ungated JWT RAG / document search

- **Files:** `backend/search/routes.py`
- **Issue:** JWT auth present; **no** Flask-Limiter; **no** `ai_gate.preflight` (unlike `/api/chat`).
- **Exploit:** Script embed + completion → OpenAI spend / quota exhaustion.
- **Fix:** Limiter (IP+user) + `ai_gate` + query length cap.
- **Likelihood:** High | **Priority:** P0

---

## OWASP Top 10 (brief)

| Item | Posture |
|------|---------|
| A01 Access control | Strong ownership on evidence/search/files; residual latent PromptBuilder edge |
| A02 Crypto | Cookies OK; encrypt library OAuth tokens (P2); rotate leaked keys |
| A03 Injection | ORM + upload sniffing; AI prompt injection residual |
| A04 Insecure design | CSRF partial path coverage; CSP not enforcing |
| A05 Misconfig | Strong prod boot; DEV_AUTO_LOGIN example; ClamAV/Redis warnings |
| A06 Components | Add pip-audit / npm audit / Dependabot (P2–P3) |
| A07 Auth | JWT logout gap; magic-link reuse; refresh unthrottled |
| A08 Integrity | Magic bytes good; malware scan optional |
| A09 Logging | Security events good; persist rate-limit/JWT failures |
| A10 SSRF | Discover import does not fetch user URLs; scholarly hosts fixed |

---

## AI-specific

| Risk | Status |
|------|--------|
| Prompt injection | Residual Medium — treat corpus as untrusted |
| Cross-user RAG | Filtered by `user_id` — sound |
| Memory cross-user | Scoped — sound |
| Token exhaustion | **High** via ungated RAG |
| Prompt leakage | Avoid returning full templates to all users (P3) |
| Tool abuse | Low surface today — keep gateway-only |

---

## Phase 2 scope (approved when requested)

Implement **only**:

1. F2.1 — JWT `session_version` binding  
2. F2.2 — harden `/api/dev-login`  
3. F10.4 — rate limit + `ai_gate` on RAG/search  
4. OPS — key rotation checklist confirmation  
5. Tests for each change; no API shape breaks  

**Defer:** CSP enforce, full validation rewrite, ClamAV infra (unless explicitly promoted), library token encryption, Medium/Low items.

---

## Phase 3+ backlog

Shared schema validation for auth/upload/AI/search/writing/library; CSRF on `/auth/*`; single-use magic links; CSP enforce; ClamAV in prod; dependency CI; encrypt OAuth tokens at rest.
