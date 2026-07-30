# EPIC-0002 — Evidence Layer

| Field | Value |
|-------|-------|
| **Status** | Ready after EPIC-0001 |
| **Priority** | P0 product differentiator |
| **Depends on** | EPIC-0001 Accepted |
| **IDD** | 0002 Domain · 0003 API (§6) · 0005 DB · 0006 Events |
| **Spine** | Document Understanding → **Evidence Objects** → human review |

---

## Intent

Make Evidence Objects the durable, inspectable knowledge layer: extract, list, explain, accept/reject, bind later for writing.

---

## Outcomes

1. Research Ready paper → extract job → candidate EvidenceObjects  
2. Inspector explain + accept/reject  
3. Project-scoped evidence list with filters  
4. Events: `EvidenceExtractionStarted`, `EvidenceCreated`, `EvidenceUpdated`  
5. FE never invents evidence client-side  

---

## Tickets — Developer A

| ID | Ticket | DoD |
|----|--------|-----|
| A-201 | Harden extract job + Research Ready gate | `202` + job id; `400 not_research_ready` |
| A-202 | Evidence list/get match IDD envelope | `{ items, total }` + ownership tests |
| A-203 | Review actions accept/reject/edit→supersede | Status lifecycle + `claim_reviews` audit |
| A-204 | Frozen explain API conformance test | Contract test vs IDD / ADR |
| A-205 | Emit/document outbox or job events for extract | Payload per IDD-0006 |
| A-206 | Gap fixes from A-003 that block Evidence | Only listed gaps |

## Tickets — Developer B

| ID | Ticket | DoD |
|----|--------|-----|
| B-211 | Evidence list UI in project / paper context | Loading/empty/error per IDD-0004 |
| B-212 | Extract CTA + ResearchProgressStage | Disabled when not ready; stages copy |
| B-213 | Evidence Inspector (citation → panel) | Explain + accept/reject optimistic |
| B-214 | MSW fixtures: candidates + accepted set | Unblocks Writing epic |
| B-215 | Query keys + invalidate on review | Per IDD-0004 §4 |

## Tickets — Sync

| ID | Ticket | DoD |
|----|--------|-----|
| A+B-220 | Staging smoke: extract → accept one object | Shared checklist signed |

---

## Non-goals

- Full rank/consensus UI (EPIC-0006)  
- Grounded paragraph generation (EPIC-0004)  
- New Claim root table  

---

## Exit criteria

- [ ] At least one project can extract and accept evidence end-to-end on staging  
- [ ] Inspector works for accepted + candidate  
- [ ] Contract tests for explain + query forbidden keys  
- [ ] B mocks no longer required for Evidence happy path (optional keep for CI)
