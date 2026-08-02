# Phase 2.0 — Ops readiness (scope frozen)

**Status:** Kit complete · operational go-live checklist  
**Parent:** [`phase-2.0-research-validation.md`](./phase-2.0-research-validation.md)  
**Rule:** Phase 2.0 ends when you are **operationally ready to observe users** — not when the product feels perfect.

---

## Scope freeze (do not expand)

| In scope for 2.0 | Out of scope (do not build now) |
|------------------|----------------------------------|
| Validation protocol + session logs + tracker | Writing Studio (Phase 2.1+) |
| Closed-beta invites + support tickets | PostHog / Plausible / custom event SDKs |
| Existing admin metrics + health APIs | New analytics dashboards |
| Deploy + smoke on dhund.com | Feature-flag service / ORM |
| Beta welcome copy aligned to Library path | Sentry (optional later if silent failures hurt) |
| Friction backlog from live sessions | “One more onboarding polish” loops |

Already shipped and sufficient:

- Protocol, invite email, rubric, session log, tracker, go/no-go — `docs/phase-2.0-*`
- `POST /api/support` + Support UI (`beta` / `bug` categories)
- `GET /api/admin/ops/invites`, `beta-metrics`, `security-events`, `health`
- `GET /api/worker/health`, `GET /api/library/health`
- `BetaBanner`, `BetaWelcomeModal`, `CLOSED_BETA` / invite gates

---

## Go-live sequence

```text
Phase 2.0 kit frozen (this doc)
        ↓
Deploy to dhund.com
        ↓
Smoke test (checklist below)
        ↓
Send invitations (protocol email)
        ↓
Run 5–10 sessions (session logs)
        ↓
Fix hard-gate issues only
        ↓
Begin Phase 2.1 Writing Studio Shell
```

---

## Pre-invite smoke checklist (dhund.com)

Run as admin / facilitator before the first invite.

### Platform

- [ ] App reachable at production URL (dhund.com or agreed host)
- [ ] Login works (Google / magic link / your auth path)
- [ ] `GET /api/worker/health` → healthy (jobs can complete) — see [`upload-worker-v1-deploy-checklist.md`](./upload-worker-v1-deploy-checklist.md)
- [ ] Frontend build is current (Library Health strip visible on `/library`)

### Library path (one throwaway account)

- [ ] Import BibTeX **or** Connect Library → papers appear
- [ ] Metadata-only row shows readiness / Attach PDF
- [ ] Attach or upload a PDF → job progresses beyond `pending`
- [ ] `GET /api/library/health` returns sensible counts
- [ ] Open `/research/compare` with ≥2 analysed papers (or note if none yet)

### Feedback path

- [ ] `/support` submits with category `beta`
- [ ] `SUPPORT_EMAIL` (or equivalent) delivers or tickets land in DB

### Invites

- [ ] Create invite via Admin → Invites (`/admin/invites`) or `POST /api/admin/ops/invites`
- [ ] Accept invite on a second email → lands in app
- [ ] Confirm `BETA_INVITE_ONLY=1` + no `DEV_AUTO_LOGIN` per [`auth-v1-deploy-checklist.md`](./auth-v1-deploy-checklist.md)
- [ ] Security baseline ops pass: [`security-baseline-v1-deploy-checklist.md`](./security-baseline-v1-deploy-checklist.md) (ClamAV, Redis limiter, optional Sentry)
- [ ] Optional: `GET /api/admin/ops/beta-metrics?days=14` returns without error

### During the validation week (reuse, don’t dashboard)

| Need | Use |
|------|-----|
| Session insight | `phase-2.0-session-log-*.md` (primary) |
| Invite funnel | `/api/admin/ops/security-events` + invites list |
| Coarse usage | `/api/admin/ops/beta-metrics?days=14` |
| Bugs from participants | `/support` → triage daily |
| Library readiness | `/api/library/health` on a test user if diagnosing |

---

## Definition of done for Phase 2.0 tooling

Phase 2.0 **tooling** is done when this checklist can be executed and the first invite is ready to send.

Phase 2.0 **validation** is done when ≥5 session logs exist and the [gate scorecard](./phase-2.0-participant-tracker.md) is filled.

**Do not** start Phase 2.1 until validation sessions are run (or explicitly waived).  
**Do not** start Phase 2.2 until hard fails from those sessions are fixed or waived in writing.

---

*If you catch yourself adding “one more dashboard,” stop and send an invite instead.*
