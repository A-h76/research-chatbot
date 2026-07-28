# Week 1 Writing Shell Backend Implementation Plan (Stage 2)

Status: Planning  
Depends on: `docs/architecture/week1-writing-shell-architecture.md`  
Scope: Backend implementation plan only (no frontend build details)

---

## 1) Purpose and Boundaries

This plan translates the approved Week 1 architecture into an executable backend work program.

In scope:
- Writing domain backend module structure
- migration sequencing
- service and repository contracts
- write-path controls (authz, validation, versioning, autosave)
- observability and security implementation tasks
- backend testing and rollout gates

Out of scope:
- frontend UI implementation details
- AI generation features
- Evidence/Citation business logic (future phases)

---

## 2) Delivery Strategy

Delivery model: vertical slices with hard exit criteria.

```text
Slice 0: Repository foundation + shared platform primitives
Slice A: Schema + lifecycle guards
Slice B: Core document service + permission guard
Slice C: Version service + restore flow
Slice D: Autosave coordinator + idempotency
Slice E: Activity/events/jobs + observability
Slice F: Hardening + tests + release readiness
```

Each slice ships only after passing functional, security, and reliability gates.

---

## 3) Target Backend Repository Layout

```text
backend/
  writing/
    api/
      routes.py
      serializers.py
      errors.py
    services/
      document_service.py
      version_service.py
      autosave_service.py
      permission_service.py
      activity_service.py
      transition_service.py
    repositories/
      document_repo.py
      version_repo.py
      activity_repo.py
    models/
      document_models.py
    validation/
      schemas.py
      guards.py
    events/
      event_types.py
      publisher.py
      subscribers.py
    jobs/
      handlers.py
    tests/
      unit/
      integration/
      security/
      concurrency/
```

Implementation rule: routes orchestrate; services own domain logic; repositories own persistence.

### Dependency rules (non-negotiable)

Allowed:

```text
Routes -> Services -> Repositories -> Database
Routes -> Services -> Events/Jobs
Services -> Validation/Guards
```

Disallowed:

```text
Routes -> Repositories
Repositories -> Services
Repositories -> Request/Session objects
Services -> HTTP response shaping
```

Violation of these rules fails code review.

---

## 4) Implementation Slices with Exit Criteria

## Slice 0: Repository Foundation

### Tasks
- establish writing module folder structure
- add dependency injection pattern for services/repositories
- centralize shared error taxonomy
- add shared validation scaffolding
- configure structured logging and request correlation
- baseline config wiring for env tiers and feature flags

### Exit criteria
- module boundaries compile and import cleanly
- DI pattern used by all writing services
- shared errors/validation/logging primitives available

### Performance budget
- framework overhead added by request plumbing: < 20ms p95

### Implementation checklist
- [ ] module structure
- [ ] DI container/factory
- [ ] shared errors
- [ ] validation framework
- [ ] logging/correlation
- [ ] config/feature flags
- [ ] baseline tests
- [ ] docs

### Rollback strategy
- if Slice 0 introduces instability, disable wiring behind module feature flag and keep legacy route paths active.

---

## Slice A: Schema and Lifecycle Foundation

### Tasks
- finalize model fields per ADD
- enforce project-scoped document ownership
- encode lifecycle statuses and transition matrix
- add migration(s) and index set
- add migration smoke checks in CI path

### Exit criteria
- all lifecycle states stored and validated
- invalid transitions rejected consistently
- migration applies cleanly on fresh and existing DB

### Performance budget
- create/list schema-backed operations in staging baseline: < 150ms p95

### Implementation checklist
- [ ] models
- [ ] migrations
- [ ] indexes
- [ ] transition rules
- [ ] tests
- [ ] metrics hooks
- [ ] docs
- [ ] feature flag

### Rollback strategy
- if migration issues arise, block Week 1 writing flag and serve existing writing endpoints unchanged.

---

## Slice B: Document Core and Authorization

### Tasks
- implement `DocumentService` operations (create/open/list/update/archive/delete/restore)
- implement centralized `PermissionService` guard
- add request-level validation and error taxonomy mapping

### Exit criteria
- no handler performs write without permission guard
- project/document ownership checks enforced on every path
- cross-tenant access tests pass

### Performance budget
- create/open/update document: < 150ms p95

### Implementation checklist
- [ ] repositories
- [ ] document service
- [ ] permission service
- [ ] validation
- [ ] routes integration
- [ ] tests
- [ ] metrics
- [ ] docs
- [ ] feature flag

### Rollback strategy
- if authz regressions occur, disable new document service routes and fall back to read-only mode for writing.

---

## Slice C: Versioning and Restore

### Tasks
- implement immutable `VersionService` append workflow
- restore operation creates new head version (no destructive rollback)
- enforce optimistic locking token checks

### Exit criteria
- version chain monotonic and immutable
- restore operation always appends new version
- conflict returns typed error and current head metadata

### Performance budget
- version restore: < 500ms p95

### Implementation checklist
- [ ] version repo
- [ ] version service
- [ ] restore workflow
- [ ] optimistic locking wiring
- [ ] tests
- [ ] metrics
- [ ] docs
- [ ] feature flag

### Rollback strategy
- if restore path is unstable, disable restore action while keeping create/edit/version append enabled.

---

## Slice D: Autosave and Idempotency

### Tasks
- implement `AutosaveService` with debounce-compatible semantics
- coalesce duplicate/unchanged submissions
- support idempotency keys
- add transient retry policy contracts

### Exit criteria
- unchanged autosave does not create redundant versions
- duplicate retries do not duplicate writes
- conflict and retry paths are deterministic and test-covered

### Performance budget
- autosave end-to-end ack: < 300ms p95

### Implementation checklist
- [ ] autosave service
- [ ] idempotency keys
- [ ] retry policy
- [ ] conflict response contract
- [ ] tests
- [ ] metrics
- [ ] docs
- [ ] feature flag

### Rollback strategy
- if autosave fails SLOs, disable autosave feature flag; manual save and core editing remain operational.

---

## Slice E: Activity, Events, Jobs, and Observability

### Tasks
- append `DocumentActivity` for write events
- publish domain events (created/updated/versioned/archived/restored/deleted)
- enqueue async jobs for indexing/metrics fan-out
- instrument logs/metrics/traces for write path

### Exit criteria
- all write actions emit activity and domain event
- async jobs are decoupled from request latency path
- observability baseline dashboards and alerts configured

### Performance budget
- post-commit event enqueue overhead: < 30ms p95

### Implementation checklist
- [ ] activity service
- [ ] event publisher
- [ ] job enqueue path
- [ ] subscribers
- [ ] logs/metrics/traces
- [ ] alerts
- [ ] docs
- [ ] feature flag

### Rollback strategy
- if event/job consumers fail, keep core writes active and circuit-break non-critical subscribers.

---

## Slice F: Security Hardening and Release Gating

### Tasks
- enforce CSRF on all mutating routes
- finalize payload constraints and sanitization policy
- tune per-action rate limits
- run security and concurrency suites
- complete release readiness checklist

### Exit criteria
- zero critical/high security findings for write path
- all concurrency conflict scenarios pass
- release gate checklist fully green

### Performance budget
- security middleware overhead on write paths: < 40ms p95

### Implementation checklist
- [ ] CSRF enforcement
- [ ] sanitization policy
- [ ] rate-limit tuning
- [ ] security tests
- [ ] concurrency tests
- [ ] release checklist
- [ ] docs/runbook
- [ ] feature flag readiness

### Rollback strategy
- if hardening introduces regressions, keep security controls on, disable risky subfeatures (restore/autosave async) until fixed.

---

## 5) Service Contracts (Behavioral)

### Service dependency diagram

```text
DocumentService
  -> PermissionService
  -> ValidationService
  -> TransitionService
  -> DocumentRepository
  -> VersionService
  -> ActivityService
  -> EventPublisher (post-commit)
```

## DocumentService
- owns lifecycle transitions and metadata writes
- never bypasses permission/validation guards
- emits domain events after successful transaction commit

## VersionService
- appends immutable version snapshots
- exposes history browse primitives
- performs restore as append-new-head operation

## AutosaveService
- accepts current version token and idempotency key
- writes only on content/metadata changes
- returns canonical save status (`saved`, `unchanged`, `conflict`, `retryable_error`)

## PermissionService
- validates user -> project -> document ownership chain
- returns typed authz outcomes (deny/not-found/forbidden semantics policy)

## ActivityService
- persists append-only activity events
- enforces logging privacy policy (no full draft body in activity metadata)

## TransitionService
- authoritative lifecycle state machine checker
- rejects non-allowed transitions

Allowed:
- draft -> active
- active -> archived
- archived -> active
- archived -> deleted
- deleted -> purged

Rejected:
- draft -> deleted
- deleted -> active
- purged -> anything

### Repository responsibilities contract

Repositories are responsible for:
- reads
- writes
- query composition
- persistence mapping

Repositories are not responsible for:
- authorization
- validation
- business rules
- event publication
- transaction ownership

---

## 6) Persistence and Transaction Strategy

### Transaction ownership

Owner: service layer.

```text
Route -> Service (begin tx) -> Repository calls -> commit/rollback -> publish events
```

Repositories never open/commit/rollback transactions.

Transactional boundaries:
- Document mutation + version append + activity append = single transaction
- Event publication uses post-commit emission pattern

Consistency rules:
- no partial success for write-path multi-entity updates
- version number increments atomically with content changes
- restore updates document head and version chain atomically

---

## 7) Error Taxonomy and Response Strategy

Canonical error classes:
- `validation_error`
- `authz_denied`
- `not_found`
- `version_conflict`
- `rate_limited`
- `transient_failure`
- `internal_error`

Policy:
- deterministic, machine-readable payloads
- conflict responses always include server head metadata needed for client recovery

---

## 8) Security Implementation Plan

Authentication:
- enforce session auth middleware for all writing routes

Authorization:
- central guard invocation before mutable loads

Input safety:
- strict schema validation and size limits
- safe rich-text sanitization policy boundary

Transport and headers:
- ensure response headers/security middleware include ADD baseline

Abuse controls:
- tuned rate limits for autosave/write/restore/archive/delete
- anomaly alert on excessive conflict or denial spikes

Audit:
- security-relevant denials and transitions logged without sensitive body data

---

## 9) Event and Job Implementation Plan

Phase 1 events:
- `DocumentCreated`
- `DocumentUpdated`
- `VersionCreated`
- `DocumentArchived`
- `DocumentRestored`
- `DocumentDeleted`

Initial subscribers/jobs:
- activity fan-out verifier
- search-index update scheduler
- metrics aggregation hook

Operational rule:
- subscriber failures do not fail primary write transaction once commit succeeds.

### Sync/async contract

```text
Synchronous path: validate -> authz -> write tx -> commit -> response
Asynchronous path: post-commit publish -> event bus -> subscribers/jobs
```

### Background job ownership model

```text
Queue -> worker -> retry policy -> dead-letter queue -> alerting
```

- retries: bounded exponential backoff
- DLQ required for poison events
- monitoring: queue depth, age, retry count, DLQ volume
- failure policy: subscriber/job failure is isolated from user write success

---

## 10) Caching Implementation Plan

Cache scope:
- project metadata
- document list summaries
- recent version headers

No-cache scope:
- authoritative draft content
- ownership decisions
- security-event outcomes

Invalidation policy:
- clear relevant project/document summary cache keys on state-changing writes

---

## 11) Observability Implementation Plan

Logs:
- structured logs with request_id, user_id hash/tokenized identity, project_id, doc_id, action, latency, outcome

Metrics:
- autosave success rate
- autosave latency percentiles
- conflict rate
- write error rate
- restore frequency

Tracing:
- spans for guard, validation, write, version append, activity append, post-commit event publish

Alerts:
- autosave error-rate threshold
- p95 write latency breach
- authz denial anomaly threshold

---

## 12) Testing Plan (Backend)

Unit (target ~70%):
- transition validation
- optimistic lock logic
- idempotency behavior
- error mapping

Integration (target ~20%):
- service + repository interactions
- transaction atomicity
- migration compatibility

E2E/API (target ~8%):
- create/edit/autosave/history/restore/archive/delete path
- refresh/retry behavior contracts

Manual/chaos (~2%):
- induced DB/network transient failure drills

Security suites (mandatory):
- IDOR and cross-project probes
- CSRF enforcement checks
- payload boundary abuse

Concurrency suites (mandatory):
- dual-client optimistic locking conflict scenarios
- replay/idempotency collision scenarios

---

## 13) Rollout and Release Plan

Release method:
- feature flag protected rollout
- staged enablement (internal -> beta cohort -> full cohort)

Pre-release checks:
- migrations tested on production-like staging
- rollback-forward contingency documented
- runbook for incidents updated

Post-release monitoring window:
- heightened alerting and on-call watch for conflict/error/latency spikes

---

## 14) Risks and Controls (Execution Phase)

Risk: service boundaries collapse back into route handlers  
Control: code review checklist enforces layering and dependency direction.

Risk: autosave introduces write amplification  
Control: coalescing, unchanged-write short-circuit, rate controls, metrics tracking.

Risk: version bloat early  
Control: retention and compaction strategy ticketed for next phase.

Risk: authz drift across endpoints  
Control: single permission service and contract tests.

Risk: observability blind spots  
Control: baseline dashboards/alerts required before release gate sign-off.

---

## 15) Backend Definition of Done (Week 1)

Functional:
- project-scoped document lifecycle fully operational
- immutable history and restore semantics in place

Security:
- ownership and CSRF controls enforced and test-proven
- no critical/high open security findings

Reliability:
- deterministic conflict handling
- autosave retry/idempotency behavior verified
- conflict resolution correctness: 100% in automated concurrency suite

Performance:
- write-path latency and autosave targets met in staging load profile
- document creation success: >= 99.9%
- autosave success: >= 99.0%

Operations:
- logs, metrics, traces, alerts active
- incident runbook and rollback notes complete
- unhandled write-path exceptions: 0 during release soak window

---

## 16) Handoff to Stage 3

After this backend plan is approved:
1. Create frontend implementation plan mapped to backend service contracts.
2. Create integrated verification plan (security + concurrency + load + release).
3. Begin implementation against slice sequence A -> F.

