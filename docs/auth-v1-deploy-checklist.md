# Auth V1 — deploy checklist (invite / allowlist)

**Subsystem:** #16 Auth (V1 bar)  
**Companions:** [`.env.example`](../.env.example) · [`IDD-0007-Auth.md`](./idd/IDD-0007-Auth.md) · [`phase-2.0-ops-readiness.md`](./phase-2.0-ops-readiness.md) · Admin SPA `/admin/invites`

Verify these before any closed-beta or public-facing deploy. Engineering has wired the controls; ops must set env correctly.

---

## 1. Fail-closed secrets & dev login

| Check | Expected |
|-------|----------|
| `FLASK_ENV` / `APP_ENV` | `production` on the live host |
| `FLASK_SECRET_KEY` | Set (non-empty); app refuses to invent a multi-worker key in prod |
| `DEV_AUTO_LOGIN` | **Unset / empty** — `security/startup.py` refuses boot if set in production |
| `/api/dev-login` | Unreachable in production (`DEV_AUTO_LOGIN and not IS_PRODUCTION`) |

Smoke: start web process with prod flags; confirm boot succeeds with secrets and fails if `DEV_AUTO_LOGIN=1`.

---

## 2. Invite / allowlist mode

Open signup is the **code default**. Closed beta must opt in:

| Mode | Env | Behavior |
|------|-----|----------|
| Open (dev / public later) | `BETA_INVITE_ONLY` unset | Anyone can register (still rate-limited) |
| Closed beta (recommended V1) | `BETA_INVITE_ONLY=1` | Signup requires `ALLOWED_EMAILS` **or** a valid invite token |
| VIP allowlist | `ALLOWED_EMAILS=a@x.com,b@y.com` | Those emails always allowed even when invite-only |
| UI banner | `CLOSED_BETA=1` (optional) | Beta chrome; does **not** enforce invite alone |

**Verified in code:** `server.py` → `_signup_allowed` → `security.ops.invites.signup_allowed` with `require_invite=BETA_INVITE_ONLY`.

Ops smoke:

1. With `BETA_INVITE_ONLY=1` and empty allowlist, uninvited `POST /auth/register` → `403 not_invited`
2. Create invite from **Admin → Invites** (`POST /api/admin/ops/invites`)
3. Register with invited email → succeeds (or verify-email path)
4. Optional VIP: put your email in `ALLOWED_EMAILS` and confirm signup without invite

---

## 3. Session revoke & account delete (V1)

| Control | Where |
|---------|--------|
| Sign out all devices | Settings → Account → confirm → `POST /api/auth/logout-all` (bumps `session_version`) |
| Account delete step-up | Settings → Data controls → password **or** email re-entry + `DELETE` → `DELETE /api/account` |

---

## 4. Pre-invite operator pass

Reuse [phase-2.0-ops-readiness.md](./phase-2.0-ops-readiness.md) smoke list, plus:

- [ ] `BETA_INVITE_ONLY=1` on production
- [ ] At least one admin (`users.is_admin`) can open `/admin`
- [ ] Invite create + accept path smoke-tested
- [ ] `DEV_AUTO_LOGIN` absent from Render/host env dump

---

*Out of V1:* MFA, SAML, org SSO, device session list UI.

Also see the full security ops pass: [`security-baseline-v1-deploy-checklist.md`](./security-baseline-v1-deploy-checklist.md).
