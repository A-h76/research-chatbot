# EPIC-0002 — Evidence Layer

| Field | Value |
|-------|-------|
| **Status** | Ready after EPIC-0001 Accepted |
| **Priority** | P0 — foundation for Writing, Reviewer, RI |
| **Depends on** | EPIC-0001 Accepted (signed IDD + frozen contracts) |
| **IDD / Contracts** | IDD-0002/0003/0005/0006 · `docs/contracts/{domain,api,event}-contracts/` |
| **Spine** | Upload ? DU ? **Evidence Objects** ? human review |
| **Naming note** | This epic is **Evidence Layer**, not “Research Intelligence” (that is EPIC-0006). |

---

## Intent

Make Evidence Objects the durable, inspectable knowledge layer. **Harden and conform** existing pipeline/APIs to frozen contracts—do **not** greenfield a parallel Claim/Paper store.

### Non-negotiable (from ADR-0003 / contracts)

| Do | Don’t |
|----|--------|
| Paper = `files` (`/api/files/:id`) | New `/api/papers` or `papers` table |
| Claims live **on/as** EvidenceObject fields | Separate root `claims` table or `GET /claims` as SoT |
| Prefer `/api/projects/:id/evidence`, `/api/evidence/*` | Invent competing knowledge APIs |
| Extend `POST /api/evidence/writing` later (EPIC-0004) | Parallel `POST /writing/generate` without ADR |

---

## Outcomes

1. Reliable ingestion ? Research Ready (status trackable)
2. Extract job ? candidate EvidenceObjects with anchors
3. List / get / explain / accept-reject-edit
4. Retrieve/search + light ranking (`default_v0`)
5. Contract + integration tests on smoke path
6. Developer B can consume frozen APIs without A’s implementation details

---

## Priority order (within this epic)

1. Processing status + Research Ready gate
2. EvidenceObject schema conformance
3. Extraction ? candidates (worker)
4. Storage lifecycle (supersede / uniqueness)
5. Evidence APIs (list/get/review/explain)
6. Retrieve / search / filters / pagination
7. Ranking default_v0 (deep consensus ? EPIC-0006)
8. Integration tests

---

## Granular tickets (Developer A) — 1–4 hours each

| ID | Ticket | Scope | DoD |
|----|--------|-------|-----|
| **A-201** | Upload ? job status API | Harden upload/job status; pollable `JobStatus` | FE can poll `pending|running|done|failed`; ownership enforced |
| **A-202** | Import / extract-text reliability | Worker `import` text extraction path | Failures ? `failed` + clear error; retry/backoff unchanged |
| **A-203** | Metadata + Research Ready gate | Readiness enum + gate before extract | Extract returns `400 not_research_ready` |
| **A-204** | Section / reference signals for anchors | DU outputs usable as anchors | Evidence rows carry page/section provenance when available |
| **A-205** | EvidenceObject schema conformance | Align model/API with contracts | Fields match contracts; `file_id`/`paper_id` dual-read documented |
| **A-206** | Claim content on EvidenceObject | Fill `claim` / `quote` / finding fields | No separate claims table |
| **A-207** | Extraction ? candidates | Worker `evidence_extract` | `202` + `job_id`/`run_id`; candidates created |
| **A-208** | Evidence storage lifecycle | Uniqueness, supersede, status machine | accept/reject/edit?supersede |
| **A-209** | Evidence list/get APIs | `GET /api/projects/:id/evidence`, `GET /api/evidence/:id` | Envelope `{ items, total }`; pagination/filter |
| **A-210** | Review API | `POST /api/evidence/:id/reviews` | accept / reject / edit; `claim_reviews` audit |
| **A-211** | Explain API contract tests | Frozen explain | Contract tests pass |
| **A-212** | Evidence retrieve/search | `POST /api/evidence/search` / `retrieve` | EvidenceQuery validation; forbidden keys ? 400 |
| **A-213** | Ranking `default_v0` | `POST /api/evidence/rank` | Named strategy; unknown strategy ? 400 |
| **A-214** | Events / job payloads | Extract started/created/updated | Payloads match event contracts |
| **A-215** | Integration tests | Smoke path | Ready ? extract ? accept one object on Postgres CI/staging |

### Explicitly out of this epic

Grounded writing (EPIC-0004), reviewer persistence (EPIC-0005), consensus/conflict advanced work (EPIC-0006), workspace shell UI (EPIC-0003).

---

## Tickets — Developer B (consume, don’t block A)

| ID | Ticket | DoD |
|----|--------|-----|
| B-211 | Evidence list UI (project/paper) | Loading/empty/error per FE contracts |
| B-212 | Extract CTA + ResearchProgressStage | Disabled when not ready |
| B-213 | Evidence Inspector | Explain + accept/reject; citation ? panel |
| B-214 | MSW fixtures until A-215 green | Unblocks Writing epic mocks |
| B-215 | Query keys + invalidate on review | Per FE contracts |

---

## Exit criteria

- [ ] Smoke: Research Ready ? extract ? accept EvidenceObject on staging
- [ ] Inspector explain + review works
- [ ] EvidenceQuery forbidden keys enforced in tests
- [ ] No new Claim/Paper root entities
- [ ] Contracts unchanged (or ADR filed)
- [ ] B can list/review evidence without asking A for internals
- [ ] Ready for EPIC-0004 Writing Intelligence backend

---

## Success metric

Developer B integrates Evidence UI for a full week using **only** frozen API + type contracts, without needing A’s pipeline implementation details.
