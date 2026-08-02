# Dhund Target Plan (50 Days)

**Status:** Active execution plan  
**Scope:** Phase 2.1 + 2.2 with SaaS-PK readiness in parallel, then guided soft launch.  
**Principle:** Security and evidence integrity are release blockers, not post-work.

---

## 0) System Design (must be agreed before M1 implementation)

### 0.1 Architecture
- Monolithic Flask app + worker stays the deploy unit.
- New writing/evidence/reviewer capabilities are modular services inside the monolith.
- All major capabilities are feature-flagged for controlled rollout.

### 0.2 Database
- Schema changes are additive via SQL migrations.
- New domain tables must define ownership columns and index strategy up front.
- Data lineage/provenance tables are first-class, not optional.

### 0.3 Backend Modules
- `writing` module (documents, versions, autosave)
- `evidence` module (claims, links, confidence, provenance)
- `citation` module (in-editor citations, bibliography services)
- `reviewer` module (rules, findings, audit trail)
- `billing/entitlements` module (SaaS-PK caps and approvals)

### 0.4 Frontend Modules
- Writing Studio shell
- Evidence panel and claim interactions
- Citation picker and bibliography panel
- Reviewer findings panel and remediation flow
- Billing/plan UX for SaaS-PK

### 0.5 AI Services
- Prompt versioning contract and storage
- Grounded generation contract (`source refs required`)
- Evals harness and deterministic reviewer checks

### 0.6 Security
- Strict row-level ownership checks on every new route
- Input/output schema validation
- CSRF and rate limiting on writes
- Signed uploads + malware scanning + CSP hardening

### 0.7 Testing
- Unit + integration + E2E for each milestone
- Security tests (cross-user, authz, injection)
- AI eval regression suite for generation/reviewer behavior

### 0.8 DevOps
- Staging-first rollout with feature flags
- SLO/error budget tracking
- Backup + restore drill before broader beta
- Rollback runbook per milestone

---

## 1) Operating Rules (non-negotiable)

1. **Milestones ship by exit criteria, not calendar date.**
2. **No AI output may be marked research-backed without evidence refs.**
3. **Every PR must pass security gates** (authz tests, input validation, dependency scan, secret scan).
4. **Feature flags required** for each major capability.
5. **Rollback path documented** before enabling user-facing features.

---

## 2) Milestone Template (mandatory for M1–M6)

Use this exact structure for every milestone:

1. Goal  
2. Architecture Changes  
3. Database  
4. Backend  
5. Frontend  
6. AI (if applicable)  
7. Testing  
8. Security  
9. Documentation  
10. Deliverables  
11. Acceptance Criteria

---

## M1 — SaaS-PK Foundation (parallel track)

### Goal
Public-ready control plane for ~100 users in Pakistan.

### Architecture Changes
Introduce entitlements as a platform service used by uploads, compare, and AI usage routes.

### Database
- New/updated tables for plans, subscriptions, payment orders, and entitlements.
- Indexes on `user_id`, `plan_code`, `status`, `updated_at`.
- Migration rollback path documented.

### Backend
- Plans + entitlements + quota enforcement
- Manual JazzCash/EasyPaisa order/approval flow
- Plan lifecycle APIs (activate/renew/expire)
- Usage metering hooks for capped actions

### Frontend
- Plan selector + pricing/limits page
- Manual payment submission flow
- Account plan/usage visibility
- Admin approval UI (MVP)

### AI
None (except entitlements gating AI run limits).

### Testing
- Quota enforcement unit/integration tests
- Payment-order state machine tests
- Cross-user access tests for plan/payment routes
- End-to-end payment submit -> approval -> activation

### Security
- Strict ownership/authz on billing endpoints
- No trust in client plan payloads
- Signed/audited plan changes
- Rate limits on payment submission/approval

### Documentation
- ADR for billing/entitlements model
- API contract docs for billing endpoints
- Ops runbook for manual approvals

### Deliverables
- Backend: plan + entitlements APIs  
- Frontend: plan UI + payment flow  
- Database: migrations + indexes  
- Docs: ADR + API docs + runbook  
- Deployment: feature flag + rollback note

### Acceptance Criteria
- [ ] Free/Founding/Student limits enforced server-side
- [ ] Manual payment approval activates plan correctly
- [ ] Upgrade/downgrade does not bypass quotas
- [ ] Abuse controls validated (rate + cost)

---

## M2 — Writing Studio Shell (Phase 2.1)

### Goal
Reliable project-scoped writing workspace (no AI generation yet).

### Architecture Changes
`Project -> Documents -> Versions -> Autosave -> Audit Log`

### Database
- New tables: `documents`, `document_versions`, `document_activity`
- Project linkage + ownership fields
- Indexes: `project_id`, `user_id`, `updated_at`

### Backend
- Draft + version schema and migrations
- Draft CRUD + archive APIs
- Autosave endpoint (idempotent)
- Optimistic locking/version conflict handling
- Audit logging for write operations

### Frontend
- Writing Studio page and document list
- Editor baseline (markdown/rich-text)
- Autosave status + conflict states
- Rename/archive dialogs
- Version history UI

### AI
None.

### Testing
- API tests for CRUD/autosave/version restore
- Component tests for editor/list/history
- End-to-end create/edit/refresh flow
- Concurrency/conflict tests

### Security
- Row-level ownership enforcement
- CSRF protections on all writes
- Payload size + format validation
- Structured request logging

### Documentation
- ADR for document versioning strategy
- API docs for document/autosave/version endpoints
- User docs for restore/history behavior

### Deliverables
- Backend: document/version APIs  
- Frontend: Writing Studio shell  
- Database: document migrations  
- Docs: ADR + API/user docs  
- Deployment: feature flag enabled

### Acceptance Criteria
- [ ] Draft CRUD works under refresh/reconnect
- [ ] Version restore works and is auditable
- [ ] Cross-user access attempts fail (403/404)
- [ ] Autosave idempotent and race-safe

---

## M3 — Evidence Layer (Phase 2.2)

### Goal
Convert paragraphs into claim+evidence objects.

### Architecture Changes
`Claim Service -> Evidence Service -> Confidence Service -> Provenance Service`

### Database
- New tables: `claims`, `claim_evidence_links`, `evidence_provenance`
- Ownership + project scope fields
- Indexes on claim/project/user and provenance keys

### Backend
- Claim and evidence models + migrations
- Claim<->evidence link APIs
- Confidence derivation service
- Provenance storage contract (source/model/prompt/version/tokens)

### Frontend
- Claim block UI in editor
- Supporting/contradicting evidence chips
- Confidence badges
- Evidence panel/drawer

### AI
- Grounded evidence linking logic only
- No freeform “ungrounded by default” generation

### Testing
- Relationship integrity tests
- Ownership tests for evidence refs
- Pagination/performance tests for evidence lists
- End-to-end claim creation and evidence link flow

### Security
- Prevent forged evidence IDs and cross-project links
- Immutable provenance fields
- Prompt-injection-resistant context assembly
- Security logging for evidence-link failures

### Documentation
- ADR for evidence model
- Provenance contract doc
- API docs for claim/evidence endpoints

### Deliverables
- Backend: claim/evidence services  
- Frontend: evidence UX in editor  
- Database: claim/evidence migrations  
- Docs: ADR + provenance contract  
- Deployment: gated rollout via flag

### Acceptance Criteria
- [ ] Claims persist and hydrate correctly
- [ ] Evidence links enforce ownership
- [ ] Confidence derivation deterministic/documented
- [ ] Evidence-integrity tests pass

---

## M4 — Citation Layer In-Editor (Phase 2.3 core subset)

### Goal
Insert/verify citations inside writing flow.

### Architecture Changes
`Citation Service -> Formatter -> Verification -> Bibliography Generator`

### Database
- Extend citation linkage for draft spans and bibliography snapshots
- Indexes for citation lookup by draft/user/project

### Backend
- Citation insert/replace APIs for drafts
- Bibliography generation service and style adapters
- Citation verification hooks against stored metadata

### Frontend
- Citation picker and citation sidebar
- Bibliography preview
- Style selector
- Replace citation dialog

### AI
Minimal (verification/ranking only if needed); deterministic formatting first.

### Testing
- Snapshot tests (APA/IEEE/MLA baseline)
- Bibliography determinism tests
- Export-integrity tests for citation rendering
- End-to-end insert/replace/update flow

### Security
- HTML/metadata sanitization for citation fields
- Ownership checks on all citation refs
- Rate limits on citation generation paths

### Documentation
- ADR for citation architecture
- API docs for citation-in-editor endpoints
- Style support matrix

### Deliverables
- Backend: citation + bibliography APIs  
- Frontend: citation UX  
- Database: citation linkage migration  
- Docs: ADR + style matrix  
- Deployment: flag-enabled rollout

### Acceptance Criteria
- [x] Insert/replace citations without draft corruption (Writing desk picker + caret helpers)
- [x] Bibliography deterministic and reproducible (binder + export path; APA/IEEE/BibTeX manager)
- [ ] Style switch tested on real draft fixtures (residual polish; manager styles exist)

---

## M5 — Structured Research Framing Workspace

### Goal
Problem statement, gap, RQs, objectives with evidence backing.

### Architecture Changes
`Research Framing Service -> Outline Generator -> Lit Review Generator -> Provenance Recorder`

### Database
- Structured card models (problem/gap/RQ/objective)
- Generation metadata + provenance references
- Indexes for project/user card retrieval

### Backend
- Structured card models and APIs
- Outline and lit-review generation endpoints
- Grounded vs ungrounded mode controls
- Full generation provenance capture

### Frontend
- Research framing workspace UI
- Card linking to evidence refs
- Outline generator UI
- Lit-review generation controls and results panel

### AI
- Prompt version pinning
- Grounded mode default
- Source reference enforcement in outputs

### Testing
- Schema validation tests for structured outputs
- Eval tests for outline/lit-review behavior
- End-to-end card -> outline -> lit-review flow

### Security
- Strict input/output schema validation
- Context size/token budgets enforced
- Prompt metadata logging and auditability

### Documentation
- ADR for prompt versioning and provenance
- Eval rubric docs
- User docs for grounded-mode expectations

### Deliverables
- Backend: framing + generation APIs  
- Frontend: framing workspace  
- Database: framing schema migrations  
- Docs: ADR + eval rubric + user docs  
- Deployment: controlled feature enablement

### Acceptance Criteria
- [ ] Cards and links persist by project
- [ ] Lit review/outline outputs include source refs
- [ ] No unreferenced research-backed claims

---

## M6 — Reviewer Core (deterministic checks)

### Goal
Quality gate from draft to publication-ready package.

### Architecture Changes
`Rule Engine -> Issue Detector -> Evidence Checker -> Reviewer History -> Evaluation Engine`

### Database
- Reviewer runs, findings, and resolution history tables
- Indexes for run lookup and finding status filters

### Backend
- Deterministic rule engine
- Finding schema: rule -> span -> evidence -> recommendation
- Reviewer run history + issue state tracking

### Frontend
- Reviewer panel with grouped findings
- Inline span highlighting
- Resolve/dismiss workflow with rationale

### AI
- Only in tightly constrained rule checks
- Structured output required for every finding

### Testing
- Precision/recall evals on reviewer datasets
- Determinism tests for fixed inputs
- End-to-end review and remediation workflow

### Security
- Reviewer endpoints read-only by default
- No hidden auto-edits
- Abuse controls on expensive reviewer runs

### Documentation
- ADR for reviewer architecture
- Rule catalog + severity definitions
- Ops docs for reviewer quality monitoring

### Deliverables
- Backend: reviewer engine + findings APIs  
- Frontend: reviewer UX  
- Database: reviewer run/finding migrations  
- Docs: ADR + rule catalog + ops docs  
- Deployment: staged rollout with guardrails

### Acceptance Criteria
- [ ] Reviewer output deterministic for fixed input
- [ ] Precision threshold met on eval set
- [ ] Findings traceable to exact span and references

---

## 3) ADR Set (must exist before corresponding milestone release)

Create in `docs/adr/`:

- `ADR-001` Derived Research Readiness
- `ADR-002` Evidence Data Model
- `ADR-003` Citation Architecture in Editor
- `ADR-004` Prompt Versioning Policy
- `ADR-005` Generation Provenance Contract
- `ADR-006` Document Versioning Strategy

**ADR exit rule:** feature cannot ship without accepted ADR when architecture changes.

---

## 4) AI Evals (regression safety)

Create datasets under `tests/evals/`:

- `lit_review/`
- `outline/`
- `reviewer/`
- `methodology/`

Each eval case must include:
- Input context
- Expected behavior
- Minimum passing score/criteria

**Release gate:** no prompt/model change merges without eval delta review.

---

## 5) Performance Budgets (hard NFRs)

- Library load: **< 500ms**
- Compare: **< 3s**
- Citation insert: **< 300ms**
- PDF import pipeline: **< 20s**
- Lit review generation: **< 30s**
- Reviewer pass: **< 45s**

Any budget breach requires explicit waiver + remediation ticket.

---

## 6) Security Hardening Checklist (always-on)

- CSP tuned for editor and dynamic content
- Signed upload flow (no unsafe direct bucket writes)
- Malware scanning before processing uploaded docs
- Moderation guardrails for public chat/generation
- Dependency vulnerability scanning in CI
- Backup + restore drill completed and documented
- Incident response + key rotation runbook available

---

## 7) Public Beta Gate (must all be green)

- [ ] Phase 2.0 validation passed (with real researchers)
- [ ] No critical security issues open
- [ ] Evidence integrity verified
- [ ] Reviewer precision acceptable on evals
- [ ] Cost controls and kill switches validated
- [ ] Backup + restore drill passed
- [ ] SLO and error budget healthy
- [ ] Rollback paths tested for major flags

Only then expand beyond initial cohort.

---

## 8) 50-day Execution Envelope (guidance, not deadline lock)

- **Window A (Days 1–25):** M1 + M2 + M3
- **Window B (Days 26–50):** M4 + M5 + M6 + beta gate prep

If a milestone misses exit criteria, extend it; do not ship partial critical infrastructure.

---

## 9) Definition of Success

A researcher can reliably go from:

`Research papers -> Research Ready -> Compare/Gap -> RQ/Objectives -> Outline -> Lit Review -> Draft -> Evidence -> Reviewer -> Publication-ready draft`

with verifiable security, provenance, and reproducible outputs.

### Post-foundation milestone (Phase 2 — Research Intelligence) ✅

> Researchers stop thinking of Dhund as an AI writing tool and start thinking of it as **the place where my research lives.**

**RI v3.0 COMPLETE / FROZEN** — see [`docs/contracts/RI-v3.0-COMPLETE-FREEZE.md`](docs/contracts/RI-v3.0-COMPLETE-FREEZE.md).  
Roadmap: [`docs/roadmap/PHASE-2-RESEARCH-INTELLIGENCE.md`](docs/roadmap/PHASE-2-RESEARCH-INTELLIGENCE.md) (RI-001…RI-009).  

**Next investment:** Phase A — Writing Intelligence MVP + accepted-evidence gate + citation export + single evidence truth path.  
**Execution roadmap:** [`docs/roadmap/EXECUTION-DUAL-TRACK.md`](docs/roadmap/EXECUTION-DUAL-TRACK.md) (Track 1 Product + UX now; Private Alpha Success Gate before Phase B; Track 2 usage-gated).
**Do not** schedule KG v2 / Novelty / semantic retrieve until Private Alpha demand; RI remains frozen.

---

## 10) Per-Issue Execution Template (required)

Use this template for every implementation issue/PR:

```text
Feature:

Goal
- ...

Architecture Changes
- ...

Database
- Tables:
- Migrations:
- Indexes:

Backend
- ...

Frontend
- ...

AI
- ...

Testing
- Unit:
- Integration:
- E2E:
- Evals:

Security/DevOps
- Authz:
- Validation:
- Injection safety:
- Rate limits / quotas:
- Logging / monitoring:

Documentation
- ADR:
- API docs:
- User docs:

Deliverables
- Backend:
- Frontend:
- Database:
- Docs:
- Deployment:

Acceptance Criteria
- [ ] ...
- [ ] ...
```

No issue is considered complete unless all populated sections are reviewed.
