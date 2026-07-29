# Researcher Validation Sprint — v0.2.1

**Status:** Active  
**Parent:** [`BETA_EXECUTION_PLAN_v0.2.1.md`](./BETA_EXECUTION_PLAN_v0.2.1.md)  
**Rule:** No new features. Observe → record friction → fix **only** smoke-path blockers → invite 20.

```text
Internal smoke (you)
        ↓
Invite 5 researchers
        ↓
Observe sessions (session logs)
        ↓
Friction backlog (workflow blockers only)
        ↓
Fix blockers · re-smoke
        ↓
Invite → 20
```

---

## Freeze (do not expand)

| Allowed | Forbidden |
|---------|-----------|
| Bugfixes that unblock Import → Export | Discovery, Sessions, Assistant, Notion |
| Copy / UX clarity on the Lit Review path | New section types as defaults |
| Invite / support / ops to run sessions | New AI modes, architecture, security programs |
| Measuring the two KPIs | “While we’re here” features |

---

## KPIs (must record)

| KPI | Target | How to score |
|-----|--------|----------------|
| **Minimal edits** | ≥80% of generated paragraphs exported without major edits | Session log: researcher self-report + facilitator note |
| **Evidence Traceability** | **100%** — every exported paragraph has ≥1 verified EvidenceObject | Export metadata `evidence_traceability_100: yes` + Verify Accept |

Secondary (log, don’t expand scope for): grounding %, citation coverage %, unsupported claims, research reviewer pass/fail.

---

## Smoke path (only workflow under test)

```text
Import papers → Extract → Accept evidence
  → Writing Studio → Generate Literature Review
  → Verify (hover markers → cards → Accept | Revise)
  → Insert → Export Markdown (body + appendix + bibliography + metadata)
```

---

## Phase 0 — Facilitator smoke (before any invite)

Run once on production (or agreed host). **Do not invite until all pass.**

- [ ] Login works (Google / magic link / password)
- [ ] Worker healthy (`/api/worker/health`)
- [ ] Import ≥1 PDF (or library attach) into a project
- [ ] Extract evidence → Accept ≥3 EvidenceObjects in Inspector
- [ ] Generate Literature Review from evidence
- [ ] Verify: hover `[#id]` → quote/page card; Accept a section
- [ ] Insert into draft; bindings persist (no silent failure toast)
- [ ] Export tab → `.md` includes Evidence appendix + Bibliography + Generation metadata
- [ ] Export shows `evidence_traceability_100: yes` (or document why not)
- [ ] `/support` accepts category `beta` or `bug`

**Gate:** all checked → invite first 5.

---

## Phase 1 — Invite 5

Use closed-beta invites (`POST /api/admin/ops/invites` or admin UI).  
Prefer researchers who already write literature reviews (PhD / RA / faculty).

**Invite email (copy):**

> Subject: Dhund closed beta — Evidence-backed Literature Review  
>  
> We’re validating one workflow only: import papers → extract evidence → generate a literature review → verify citations → export Markdown with an evidence appendix.  
>  
> Please bring 2–5 papers you know. Session ~45–60 minutes with a facilitator.  
>  
> Login: [URL]  
> Support: [support path]  
>  
> This is not a feature tour — we watch where the workflow breaks.

Tracker: [`RESEARCHER_VALIDATION_v0.2.1_tracker.md`](./RESEARCHER_VALIDATION_v0.2.1_tracker.md)

---

## Phase 2 — Observe (per researcher)

1. Copy [`RESEARCHER_VALIDATION_v0.2.1_session_log.md`](./RESEARCHER_VALIDATION_v0.2.1_session_log.md) → `docs/sessions/v021-P0X.md`
2. Facilitator watches silently except for hard blockers (login, crash, empty extract)
3. After export: ask the two KPI questions (script in session log)
4. File friction in [`RESEARCHER_VALIDATION_v0.2.1_friction.md`](./RESEARCHER_VALIDATION_v0.2.1_friction.md)

**Hard friction (must fix before scaling):** prevents completing smoke path.  
**Soft friction:** annoyance; defer unless frequency ≥3/5.

---

## Phase 3 — Fix only blockers

After ≥5 completed sessions (or earlier if a P0 blocks everyone):

1. Triage friction backlog  
2. Implement **only** items marked `blocker` / `fix-before-20`  
3. Re-run facilitator smoke  
4. Optionally re-invite 1–2 researchers who hit the blocker  

Still no new features.

---

## Phase 4 — Invite → 20

**Go criteria (all required):**

- [ ] ≥5 session logs completed  
- [ ] ≥4/5 completed full smoke path with ≤1 facilitator rescue  
- [ ] Minimal-edits KPI: ≥80% among completed sessions (or documented waiver)  
- [ ] Traceability: export `evidence_traceability_100: yes` on ≥4/5 successful exports  
- [ ] All `blocker` frictions fixed or waived in writing  
- [ ] Facilitator smoke still green  

Then invite remaining seats to **~20** total. Same workflow only. Continue logging friction; still no feature expansion.

---

## Ops pointers

| Need | Where |
|------|--------|
| Invites / metrics | `/api/admin/ops/invites`, `beta-metrics`, `security-events` |
| Older Phase 2.0 kit (library-era) | `docs/phase-2.0-*` — **do not** reopen that gate; this sprint supersedes for v0.2.1 Lit Review |
| Security freeze | `docs/SECURITY_BASELINE_v1.0.md` |
| Product freeze | `Dhund-Flow/PLATFORM_FREEZE_v1.0.md` |

---

## Definition of Done (Beta row)

| Done when |
|-----------|
| ≥5 researchers completed Import → Export |
| KPIs recorded (80% minimal-edits + 100% traceability on successful exports) |
| Blockers fixed |
| Invite ladder opened toward 20 |
