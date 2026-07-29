# SECURITY_BASELINE_v1.0

**Date:** 2026-07-29  
**Status:** Frozen  
**Scope:** Controlled beta (≈20 invitees) — Evidence-backed Literature Review window  
**Supersedes incremental baselines:** `SECURITY_BASELINE_PR1` … `PR4` (historical); live audit trail: `SECURITY_AUDIT_2026-07-29.md`

---

## Freeze rule

**No new security infrastructure** unless it:

1. fixes a **demonstrated** vulnerability (beta incident, repro, or external report), or  
2. addresses a **high-severity** finding from a scoped audit, or  
3. **directly** supports the active researcher workflow (e.g. authz for a shipping Evidence/Writing path).

Allowed without lifting the freeze: bugfixes to existing controls, config/ops hardening, test coverage for shipped controls, documentation updates.

---

## Maturity checklist (verified)

| Area | Status | Where |
|------|--------|--------|
| AI Gateway governance | ✅ | `backend/ai/gateway.py`, `docs/AI_POLICY_v1.0.md`, registry validate-on-boot |
| Platform / product governance | ✅ | `PLATFORM_FREEZE_v1.0`, `PRODUCT_DECISIONS`, release criteria |
| Rate limiting | ✅ | Flask-Limiter + Redis (prod preferred); chat/upload/auth/RAG limits |
| Input validation (high-risk writes) | ✅ | `security/request_validation.py` (+ chat length caps) |
| Secrets management | ✅ | Prod fail-closed `security/startup.py`; no commit of `.env` |
| CSP | ✅ | Enforced in prod; `CSP_REPORT_ONLY=1` rollback |
| OAuth token protection | ✅ | Library tokens sealed at rest (`enc:v1:`) |
| File scanning | ✅ | ClamAV required in prod unless `CLAMAV_OPTIONAL=1` |
| Telemetry / security events | ✅ | Metrics + security event store |
| Security documentation | ✅ | This baseline + audit + PR1–PR4 history |

---

## Pre-beta verification (headers / cookies / uploads)

### Security headers (every response)

| Header | Value |
|--------|--------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | camera/microphone/geolocation/payment/usb disabled |
| `Strict-Transport-Security` | prod only (`max-age=31536000; includeSubDomains`) |
| `Content-Security-Policy` | prod enforce (Phase 4); Report-Only via `CSP_REPORT_ONLY=1` |
| `Cache-Control` | `no-store` on `/api/*` and `/auth/*` (not static assets) |

Implementation: `security/headers.py` via `after_request` in `server.py`.

### Session cookies

| Flag | Setting |
|------|---------|
| HttpOnly | `True` |
| SameSite | `Lax` |
| Secure | `True` when `IS_PRODUCTION` |
| Lifetime | Absolute + idle TTL (`SESSION_ABSOLUTE_HOURS`, `SESSION_IDLE_MINUTES`) |
| Session version | Cookie + JWT `sv` reject after logout-all |

### Upload validation

| Control | Status |
|---------|--------|
| Extension allowlist | ✅ `backend/upload/validation.py` |
| Magic-byte / MIME sniff | ✅ must match extension |
| Size limits | ✅ `MAX_DOCUMENT_UPLOAD_MB` / `MAX_CONTENT_LENGTH` |
| Filename sanitisation | ✅ `secure_filename` + empty-name fallback |
| Virus scan | ✅ ClamAV when enabled; **required in prod** unless optional opt-out |

---

## Explicitly out of scope for v1.0 (do not build now)

- Full request-validation migration of every write endpoint  
- Dependency / SBOM CI as a new platform program  
- Multi-provider auth, step-up reauth for account deletion (unless a beta incident forces it)  
- CSP `report-uri` pipeline (optional later if violations block UX)  
- Broad pentest remediations beyond demonstrated issues  

---

## Ops checklist before inviting testers

1. Production: `CLAMAV_ENABLED=1` (or accept risk with `CLAMAV_OPTIONAL=1`)  
2. Confirm HTTPS termination (HSTS + `Secure` cookies)  
3. `REDIS_URL` set so rate limits are shared across workers  
4. Rotate any secrets that ever left `.env`  
5. Smoke: login → upload PDF → RAG/search → writing path; if SPA breaks, set `CSP_REPORT_ONLY=1`  
6. Re-connect Zotero/Mendeley after deploy so tokens are sealed  

---

## Change control

Amendments to this baseline require a short note in `docs/SECURITY_AUDIT_2026-07-29.md` (or a dated addendum) stating **why** the freeze rule exception applies. Prefer fixing the demonstrated issue over expanding the security surface.
