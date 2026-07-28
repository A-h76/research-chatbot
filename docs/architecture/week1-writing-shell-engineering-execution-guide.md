# Week 1 Writing Shell Engineering Execution Guide (Stage 5)

Status: Planning  
Purpose: Execution consistency and delivery governance only (no new architecture)

Depends on:
- `docs/architecture/week1-writing-shell-architecture.md`
- `docs/architecture/week1-writing-shell-backend-implementation-plan.md`
- `docs/architecture/week1-writing-shell-frontend-technical-design.md`
- `docs/architecture/week1-writing-shell-verification-and-qa-spec.md`

---

## 1) Scope and Guardrails

This guide defines how implementation is executed, reviewed, merged, and released.

It must not:
- introduce new architecture
- change approved service boundaries
- bypass Stage 4 quality gates

Any architectural deviation requires an ADR update and explicit approval before implementation.

---

## 2) Milestone and Slice Order

Execution sequence:

```text
Stage 5 setup
  -> Slice 0 (foundation)
  -> Slice A (schema/lifecycle + workspace shell)
  -> Slice B (core doc/list + authz)
  -> Slice C (versioning + autosave core)
  -> Slice D (history + restore)
  -> Slice E (conflict/offline/recovery)
  -> Slice F (hardening + observability + release gates)
```

Policy:
- no slice starts before prior slice exit criteria are met
- exceptions require written waiver and risk sign-off

---

## 3) Task Dependency Model

Dependency layers:

```text
Foundation -> Contracts -> Core flows -> Recovery flows -> Hardening -> Release
```

Required dependency rules:
- frontend implementation for a slice starts only after backend contract fixtures are frozen for that slice
- QA automation starts with slice implementation, not after all slices complete
- observability hooks are required in-slice, not deferred to final week

---

## 4) Branching Strategy

Recommended branch model:
- `main`: protected, releasable
- `slice/<id>-<name>`: one branch per slice (e.g., `slice/c-autosave-core`)
- optional `hotfix/*`: urgent production remediations

Rules:
- no direct commits to `main`
- one slice per PR stream (avoid cross-slice mega-PRs)
- rebase or merge from `main` daily for active slice branches

---

## 5) Pull Request Structure

Each PR must include:
- slice reference
- linked checklist items
- contract changes (if any)
- risk summary
- test evidence summary
- rollback/containment note

PR size policy:
- prefer small and reviewable units
- if large PR is unavoidable, split by backend/frontend/test boundaries

---

## 6) Code Review Checklist

Required reviewer checks:

Architecture and boundaries:
- layering/dependency rules respected
- no route-to-repo shortcuts
- no UI-to-transport shortcuts

Correctness:
- lifecycle/state transitions valid
- optimistic locking/conflict behavior intact
- restore semantics preserve history

Security:
- authz/tenant checks enforced
- CSRF and validation behavior preserved
- no sensitive logging or storage leakage

Reliability:
- autosave idempotency and retry contracts preserved
- no silent data loss path introduced

Observability:
- required events/logs/metrics emitted

Testing:
- slice-level required tests added or updated
- contract fixtures synchronized when needed

---

## 7) Definition of Ready (DoR)

A task/slice is Ready only when:
- scope and acceptance criteria are explicit
- contract fixtures exist or are updated
- dependencies are satisfied
- test plan for that scope is written
- rollback approach is identified
- feature flag strategy is defined

No development start without DoR confirmation.

---

## 8) Definition of Done (DoD)

A task/slice is Done only when:
- implementation complete for declared scope
- tests pass at required levels (unit/integration/e2e as applicable)
- Stage 4 gates for that scope are green
- observability hooks verified
- docs/checklists updated
- rollout/rollback notes verified

Done does not mean "code compiles"; it means "release-safe at slice scope."

---

## 9) Merge Requirements

Mandatory merge gates:
- CI green (including contract and security suites)
- required reviewers approved
- no unresolved critical review comments
- feature flag default state verified
- migration safety checks passed (for backend schema changes)

Blocked merge conditions:
- failing contract sync between frontend and backend
- missing rollback note
- missing test evidence for changed behavior

---

## 10) Release Workflow

```text
Slice complete
  -> RC deploy (staging)
  -> Stage 4 verification run
  -> Go/No-Go review
  -> Gradual flag enablement
  -> Monitor
  -> Full enablement
```

Release controls:
- start with internal cohort
- monitor autosave/conflict/error dashboards
- expand only after stability window passes

Rollback controls:
- disable affected feature flags first
- perform full rollback only when containment insufficient
- run post-rollback verification checklist

---

## 11) Drift Prevention Controls

To prevent implementation drift:
- weekly architecture conformance review against Stages 1-4
- ADR required for boundary/contract deviations
- slice retro captures scope creep and corrective actions
- reject unplanned feature additions during Week 1 execution window

---

## 12) Execution Cadence and Communication

Recommended cadence:
- daily slice standup (blocked/dependency/risk focus)
- mid-slice technical checkpoint
- end-slice quality review with QA evidence

Required artifacts per slice:
- implementation summary
- test evidence summary
- risk/rollback update
- go/no-go recommendation for next slice

---

## 13) Stage 5 Exit Criteria

Stage 5 is complete when:
- execution rules are acknowledged by backend, frontend, and QA owners
- slice backlog is sequenced with dependencies and owners
- review/merge/release gates are enabled in workflow tooling
- implementation can begin at Slice 0 without process ambiguity

