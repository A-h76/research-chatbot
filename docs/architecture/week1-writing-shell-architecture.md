# Week 1 Writing Studio Shell Architecture (Production Blueprint)

Status: Proposed  
Scope: Week 1 foundation for Writing Studio Shell (non-AI writing)  
Audience: Backend, frontend, platform, security, and QA leads

---

## 1) High-Level System Architecture

The Writing Shell is a project-scoped document system designed as the base for evidence, citation, and reviewer capabilities.

### Component topology

```text
Web Client (SPA)
  -> API Gateway (Flask routes, auth/session, CSRF, rate limits)
      -> Document Domain Module
          -> Document Service
          -> Version Service
          -> Autosave Coordinator
          -> Permission Guard
          -> Activity/Audit Publisher
      -> Postgres (source of truth)
      -> Redis (optional: autosave retry state, cache)
      -> Object Storage (future: large snapshots/exports)
      -> Observability (logs, metrics, traces)
```

### Service boundary recommendation

- Keep Week 1 as a modular monolith inside current Flask runtime.
- Extract internal services as clear module boundaries first; avoid network microservices now.

### Trade-offs

- Modular monolith pros: faster delivery, lower ops overhead, easier transactional consistency.
- Microservice-first cons: premature distributed complexity, higher failure surface, harder debugging.

### Recommendation

Use modular monolith now with strict interfaces and domain seams to allow future extraction.

### Repository architecture (target structure)

```text
backend/
  api/
  services/
  models/
  repositories/
  auth/
  validation/
  events/
  jobs/
  migrations/
  tests/
  config/

frontend/
  pages/
  features/
  components/
  hooks/
  services/
  store/
  types/
  tests/
```

This structure prevents route/controller sprawl and keeps domain logic out of transport layers.

---

## 2) Domain Model

### Bounded contexts (DDD)

```text
Research Domain
  Library
  Compare
  Writing
  Evidence
  Citation
  Reviewer
  Export
  Billing
```

Each bounded context owns its models, validation, services, events, and tests.

### Core entities

- `Project`: ownership root for all research assets.
- `Document`: active writing artifact, always owned by one user and one project.
- `DocumentVersion`: immutable historical snapshot for restore/audit.
- `DocumentActivity`: append-only timeline for user/system actions.
- `User`: identity and authorization principal.

### Extended entities (future-compatible)

- `DocumentBlock`: structured block container.
- `BlockCitationLink`: citation anchors per block.
- `BlockEvidenceLink`: evidence anchors per claim block.
- `CommentThread`: collaboration comments.
- `ChangeProposal`: track-changes style edits.

### Lifecycle

```text
draft -> active -> archived -> deleted -> purged
```

- `deleted` is soft-delete and recoverable.
- `purged` is privileged cleanup path after retention window.

### State machine (allowed transitions)

```text
draft -> active
active -> archived
archived -> active
archived -> deleted
deleted -> active (restore)
deleted -> purged
```

Any non-listed transition fails validation with a state-transition error.

### Ownership model

- User owns project.
- Project owns document scope.
- Document/version/activity must match owner and project tenancy.

---

## 3) Database Architecture

### Logical schema strategy

- Normalized base tables:
  - documents
  - document_versions
  - document_activity
- Referential constraints enforce document-parent relationships.
- Tenant keys (`user_id`, `project_id`) present on hot-path tables for fast authorization checks.

### Indexing strategy

- Composite indexes for:
  - listing by project and recency
  - listing by user and status
  - version fetch by document and descending version number
  - activity timeline by document and recency

### Version storage strategy

- Week 1: full immutable snapshots per logical save event.
- Future: hybrid snapshot+delta for long documents.

### Archival/deletion strategy

- Archive: hidden from active views, fully restorable.
- Soft delete: removed from default views, restorable during retention.
- Purge: privileged hard-delete with safety checks and audit trail.

### Migration strategy

- Additive forward migrations only.
- Backfill scripts for derived fields.
- Rollback-by-forward-fix rather than destructive rollback in production.

### Normalization vs denormalization

- Normalize authoritative write model.
- Denormalize only computed projections (search, dashboard stats) when needed.

---

## 4) Backend Architecture

### Document Service

- Handles lifecycle transitions, metadata updates, and ownership-scoped access.

### Version Service

- Appends immutable versions, restores historical states as new head versions.

### Autosave Coordinator

- Applies debounce-aware saves, idempotency checks, conflict detection.

### Permission Guard

- Central ownership validation on project and document boundaries.

### Activity Service

- Records append-only action events with minimal non-sensitive metadata.

### Validation Service

- Enforces payload shape, content limits, status transitions, and text safety policy.

### Search Hook (future)

- Emits lightweight update events to search indexing pipeline.

### Event architecture

Domain events are first-class outputs of domain actions:

```text
DocumentCreated
DocumentUpdated
VersionCreated
DocumentArchived
DocumentRestored
DocumentDeleted
CitationInserted (future)
EvidenceAttached (future)
ReviewCompleted (future)
```

Consumers (analytics, indexing, notifications, AI triggers) subscribe without coupling to write paths.

### Background jobs architecture

```text
Request -> synchronous domain commit -> response
                          -> enqueue async jobs:
                               activity fan-out
                               metrics aggregation
                               search indexing
                               downstream AI triggers (future)
```

Use queue-backed workers for non-critical post-commit workloads to protect p95 API latency.

### Dependency direction

```text
API Layer -> Permission Guard -> Domain Services -> Persistence
                       \-> Validation -> Activity
```

---

## 5) API Design Philosophy

Design around user actions, not endpoint count.

### Action-first model

- Create draft
- Open document
- Save/autosave
- Rename
- Archive/restore
- Delete/undelete
- View history

### Request lifecycle

1. Authenticate session.
2. Validate input contract.
3. Authorize tenancy and ownership.
4. Enforce optimistic lock/version condition.
5. Apply domain action atomically.
6. Append activity/audit events.
7. Return canonical state object.

### Error handling philosophy

- Deterministic, typed error categories:
  - validation
  - authz
  - conflict
  - rate-limit
  - transient platform error

### Idempotency

- Autosave and restore actions should accept idempotency keys for retry safety.

### REST vs RPC trade-off

- REST resources fit core document CRUD/history.
- Action-oriented RPC-style endpoints acceptable for workflow actions (restore, archive) if semantics are explicit.

### Recommendation

Use REST-first with explicit action routes where state machine transitions are clearer than raw patch semantics.

### API versioning policy

- Current: `v1` namespace.
- Future: additive changes in `v1`; breaking changes require `v2`.
- Deprecation: announce window + compatibility adapter period.
- Change control: explicit ADR and migration plan for breaking behavior.

---

## 6) Frontend Architecture

### Page hierarchy

```text
Project Workspace
  -> Writing Home
      -> Active Documents List
      -> Archived/Trash Views
      -> Document Editor View
      -> Version History Panel
```

### State architecture

- Server state: query cache layer (documents, versions, activity slices).
- Client state: editor transient state, autosave queue state, conflict banners.
- UI state: panel visibility, selection, filters.

### Separation of concerns

- Presentation components: pure rendering.
- Feature controllers/hooks: action orchestration and retry/conflict behavior.
- API client layer: transport and serialization concerns only.

### UX requirements

- Fast document switching.
- Explicit save status badge.
- Conflict prompt with safe refresh/reload flow.
- Archive/trash affordances with restore path.

### Offline behavior

- Week 1: limited offline queue with best-effort replay.
- Future: full local-first CRDT or operational transform strategy.

---

## 7) Editor Architecture

### Why structured blocks

Plain text/HTML cannot reliably support evidence attribution, citation integrity, reviewer checks, and export fidelity.

### Block model recommendation

- Base block envelope:
  - block_id
  - type
  - content payload
  - metadata
  - references (citation/evidence IDs)

### Initial block types

- heading
- paragraph
- list
- quote
- figure-placeholder
- table-placeholder
- citation-inline anchor
- evidence-note anchor

### Future block types

- claim block
- contradiction block
- AI suggestion block
- review annotation block

### Compatibility mapping

- Evidence Layer: claim/evidence links attach to block IDs.
- Citation Layer: citation anchors and bibliography generation map from block refs.
- Reviewer: rule engine runs at block and section granularity.
- Export: block-to-format transformation with deterministic mapping.

---

## 8) Autosave Architecture

### Save cadence

- Debounce window: 2-5 seconds idle.
- Immediate save triggers on explicit user actions (switch/close/manual save).

### Queueing model

- Single in-flight request per document.
- Coalesce pending local edits while in-flight.
- Replay latest state after ack.

### Retry strategy

- Exponential backoff for transient failures.
- Max retry bound with clear user-visible error state.

### Conflict handling

- Compare client version token with server version token.
- On mismatch: reject write, preserve local buffer, prompt controlled refresh/merge workflow.

### Network interruption

- Persist unsent local edits in temporary local cache.
- On reconnect, revalidate head version then replay if safe.

### Trade-offs

- Aggressive frequency improves freshness but increases DB pressure.
- Slower cadence lowers load but increases potential unsaved delta.

### Recommendation

2-3 second idle debounce with coalesced writes and strict optimistic locking.

---

## 9) Versioning Architecture

### Options

- Snapshot-only
- Delta-only
- Hybrid snapshot+delta

### Trade-off summary

- Snapshot-only: simple restore/debug, higher storage usage.
- Delta-only: storage-efficient, expensive reconstruction, complex corruption handling.
- Hybrid: balanced at scale, highest implementation complexity.

### Recommendation

Use snapshot-only for Week 1, with retention policy and future hybrid migration path.

### Restore semantics

- Restoring a version creates a new latest version.
- Historical chain remains immutable and auditable.

---

## 10) Security Architecture

### Authentication

- Session-based auth with secure cookie policy.

### Authorization and tenancy

- Enforce user->project->document ownership on every read/write path.
- Never trust client-provided user/project/document linkage.

### Input validation

- Strict payload schema.
- Content length and metadata bounds.
- Lifecycle transition guardrails.

### CSRF and XSS

- CSRF checks on all mutating endpoints.
- Server-side sanitization policy for rich text.
- Output escaping/default-safe rendering.

### Security headers baseline

- CSP
- HSTS
- X-Frame-Options
- Referrer-Policy
- Permissions-Policy

### Session security

- Idle and absolute session expiry.
- Session ID rotation on privilege changes and login.
- Logout invalidation with server-side version checks.

### Upload security baseline (cross-phase)

- Signed upload URLs only.
- MIME + magic-byte allowlist enforcement.
- Malware scanning before processing.
- Quarantine path for failed scans.

### Rate limits

- Endpoint-class-specific limits:
  - create/update/autosave
  - restore/archive/delete

### Tenant isolation

- Negative tests for cross-user and cross-project access.
- Ownership checks before loading mutable entities.

### Audit logging

- Log security-relevant actions and denials.
- Exclude sensitive content bodies from security logs.

### Threat model highlights

- IDOR attempts
- CSRF against write endpoints
- malicious payload injection in rich text
- replay/duplicate mutation requests
- noisy autosave abuse

### Mitigations

- centralized guard layer, strict validation, rate limits, typed conflicts, immutable history.

---

## 11) Audit and Observability

### Audit logs (business/security)

- created, renamed, edited, archived, restored, deleted, conflict_denied, authz_denied

### Application logs

- request IDs, latency buckets, error class, retry count
- never log full document content by default

### Metrics

- autosave success rate
- autosave latency percentiles
- conflict rate
- restore frequency
- archive/delete/undelete rates

### Tracing

- Span chain: request -> authz -> validation -> write -> version append -> activity append

### Alerts

- elevated conflict spikes
- autosave error rate over threshold
- p95 latency budget breach

### Logging and privacy policy

- Never log full draft bodies, tokens, secrets, or session identifiers.
- Log structural metadata only (IDs, status, timing, error class).

---

## 12) Performance Architecture

### Targets

- Document open p95 under 500ms for normal size docs.
- Autosave ack p95 under 300ms for non-degraded path.

### Techniques

- Server pagination for document lists and history.
- Indexed project/status/version queries.
- Lazy load history/activity side panels.
- Client virtualization for long history lists.
- Avoid heavyweight editor re-renders by block-level updates.

### Scalability posture

- Week 1 supports single-tenant to small multi-tenant scale.
- Future horizontal scaling with stateless web workers and shared DB/Redis.

### Cache strategy

Cache candidates:
- project metadata
- document list summaries
- recent version headers
- permission snapshots with short TTL
- citation style metadata (future)

Never cache:
- authoritative draft content
- ownership/authz final decisions
- security event outcomes

Invalidate caches on state-changing writes and ownership boundary changes.

---

## 13) Failure Recovery

### Failure scenarios and behavior

- DB unavailable: fail fast with clear retriable error, preserve local buffer.
- Autosave failure: keep dirty state, queue retry, user-visible warning.
- Version conflict: reject with head version info, keep local changes intact.
- Browser refresh: restore unsent local state and fetch latest server head.
- Network disconnect: move autosave queue offline, replay on reconnect.
- Duplicate request: idempotency key prevents duplicate writes.
- Partial write attempt: transactional boundary ensures all-or-nothing.

### Disaster recovery architecture

```text
scheduled backups
  -> point-in-time recovery capability
  -> routine restore drills
  -> version-chain integrity verification
  -> incident runbook execution
```

Operational SLO: recovery procedures are tested, not only documented.

---

## 14) Future Compatibility

### Evidence Layer

- Claim/evidence links attach to block IDs and version lineage.

### Citation Layer

- Inline citation anchors are first-class references in block metadata.

### AI Reviewer

- Reviewer runs on structured sections/blocks with deterministic references.

### Literature Review generation

- Generation context can be constrained by project scope and block provenance.

### Collaboration and comments

- Activity/events model and immutable versions are prerequisites.

### Journal export

- Block model enables deterministic mapping to DOCX/PDF/LaTeX pipelines.

### Team workspace

- Add org/workspace ownership layer above projects without rewriting document core.

---

## 15) Engineering Decisions (ADR-style)

### ADR-WS-001: Project-scoped documents only

- Problem: standalone docs break research context consistency.
- Alternatives: allow unscoped docs; optional project links.
- Chosen: required project scope.
- Implication: stronger context integrity and simpler future evidence/citation joins.

### ADR-WS-002: Snapshot versioning for Week 1

- Problem: need reliable restore and audit quickly.
- Alternatives: delta-only; hybrid now.
- Chosen: snapshot-only now.
- Implication: larger storage, lower complexity; can evolve later.

### ADR-WS-003: Optimistic locking

- Problem: concurrent saves may overwrite user work.
- Alternatives: last-write-wins; pessimistic lock.
- Chosen: optimistic version checks.
- Implication: conflict UX required, data loss risk reduced.

### ADR-WS-004: Modular monolith boundary

- Problem: need fast delivery with clean domain seams.
- Alternatives: microservices first.
- Chosen: modular monolith.
- Implication: easier Week 1 execution, future extraction path retained.

### ADR-WS-005: Structured block-ready editor model

- Problem: plain text limits evidence/citation/reviewer capabilities.
- Alternatives: plain markdown-only.
- Chosen: block-oriented internal model (with markdown-compatible surface).
- Implication: higher upfront design effort, major downstream feature leverage.

---

## 16) Risks and Mitigations

### Technical risk

- Risk: editor-state complexity grows quickly.
- Mitigation: strict boundaries, typed state machine, narrow Week 1 block set.

### Scalability risk

- Risk: snapshot growth.
- Mitigation: retention policies, compression, later hybrid version strategy.

### Security risk

- Risk: cross-tenant access bugs.
- Mitigation: centralized authz guard + automated IDOR suites.

### Maintainability risk

- Risk: route handlers accumulate business logic.
- Mitigation: service-layer extraction and ADR discipline.

### Performance risk

- Risk: high autosave write volume.
- Mitigation: debounce, coalescing, rate controls, targeted indexing.

### Operational risk

- Risk: poor incident visibility.
- Mitigation: actionable metrics/alerts and runbooks.

---

## 17) Testing Strategy

### Testing pyramid target

- 70% unit tests
- 20% integration tests
- 8% end-to-end tests
- 2% manual exploratory and chaos checks

### Unit tests

- state transition rules
- validation constraints
- version token logic

### Integration tests

- ownership checks across project/document/version paths
- autosave idempotency and retry behavior
- restore and history consistency

### End-to-end tests

- create -> edit -> autosave -> refresh -> restore
- archive -> list filtering -> restore

### Concurrency tests

- dual-client update conflict scenarios

### Security tests

- IDOR probes
- CSRF mutation rejection
- payload abuse boundaries

### Load tests

- autosave throughput under concurrent user simulation

### Regression tests

- fixed bug replay suites for conflict and ownership edge cases

### Coverage and quality gates

- Service-layer coverage target at or above 90% for write-path modules.
- Mandatory concurrency and IDOR suites for merge eligibility.

---

## 18) Acceptance Criteria

### Functional

- Document creation, editing, listing, archiving, restoring, deleting works within project scope.
- Version history is visible and restorable with immutable lineage.

### Security

- Cross-user and cross-project document access is blocked and logged.
- Mutating routes enforce CSRF and validation policy.

### Reliability

- Autosave handles transient failures with recoverable behavior.
- Refresh/reconnect does not silently lose unsaved content.

### Performance

- Open and autosave latency budgets meet p95 targets in baseline environment.

### Maintainability

- Clear service boundaries and ADR records exist for major decisions.

### Scalability

- Query/index profile supports expected early multi-tenant usage.

### Developer Experience

- Error taxonomy is consistent and testable.
- Local debugging of autosave/version conflicts is straightforward.

### Operational Readiness

- Metrics, logs, tracing, and alert rules defined for Week 1 write path.

### Measurable success metrics

- Autosave success rate: >= 99.9% (non-degraded path).
- Autosave p95 latency: < 300ms.
- Critical security issues: 0 open.
- Unhandled write-path exceptions: 0 in release candidate soak.
- Data-loss incidents from refresh/reconnect: 0 accepted.

---

## 19) Configuration Architecture

Environment tiers:

```text
development -> testing -> staging -> production
```

Policy:
- Hierarchical config with safe defaults.
- Secrets only from secure secret stores.
- Feature flags for risky or expensive capabilities.
- Per-environment override boundaries documented and audited.

---

## 20) Deployment Architecture

```text
Browser
  -> CDN / edge proxy
  -> reverse proxy
  -> Flask web service (stateless replicas)
  -> Redis (cache + coordination)
  -> Postgres (primary data store)
  -> object storage
  -> observability stack
```

Deployment requirements:
- health checks
- controlled migration step
- rollback playbook
- staged rollout path

---

## 21) Coding Standards and Module Governance

Mandatory standards:
- explicit module boundaries and dependency direction
- typed contracts at service boundaries
- centralized error taxonomy
- structured logging conventions
- dependency injection for testability
- ADR-required changes for cross-domain coupling

---

## 22) Future Evolution Roadmap

```text
Week 1 Writing Shell
  -> Evidence Layer
  -> Citation Layer
  -> Research Framing
  -> AI Reviewer
  -> Export Maturity
  -> Collaboration (comments/track changes)
  -> Publication Workflows
  -> Enterprise/Team Workspaces
```

Architecture choices in Week 1 are intentionally optimized for this sequence.

---

## 23) Recommended Next Stage Prompts

1. Backend implementation plan prompt based on this architecture.
2. Frontend implementation plan prompt based on this architecture.
3. Security and testing implementation prompt based on this architecture.

This keeps architecture and implementation intentionally separated.
