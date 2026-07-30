# EPIC-0005 — Reviewer

| Field | Value |
|-------|-------|
| **Status** | Ready after grounded writing path (EPIC-0004) |
| **Priority** | P1 trust |
| **Depends on** | EPIC-0004 (`GroundedWritingResult.review`) |
| **IDD** | 0002 ReviewerFinding · 0003 writing review · 0004 Reviewer UI · 0006 ReviewCompleted |

---

## Intent

Make the **Research Reviewer** a first-class, trustworthy surface: findings with severity, version stamps, and (Phase 2) durable runs—not a hidden JSON blob.

---

## Outcomes

1. Reviewer accordion / panel in Writing  
2. Stable finding codes + severities  
3. `reviewer_version` visible  
4. Optional persistence of review runs  
5. Export can include review summary  

---

## Tickets — Developer A

| ID | Ticket | DoD |
|----|--------|-----|
| A-501 | Freeze ReviewerResult schema + codes list | Documented in IDD appendix or constants file |
| A-502 | Ensure every grounded ok response includes review | Even if issues=[] |
| A-503 | Persist reviewer run (document_activity or reviewer_runs) | Migration + API get latest |
| A-504 | Emit ReviewCompleted event/payload | IDD-0006 |
| A-505 | Export includes reviewer_version + issue count | Provenance |

## Tickets — Developer B

| ID | Ticket | DoD |
|----|--------|-----|
| B-511 | Reviewer UI accordion by severity | Empty = “No issues” |
| B-512 | Click finding → scroll/highlight section if ids exist | Degrade if no section_id |
| B-513 | Show reviewer_version + grounding metrics together | Calm, not gamified |
| B-514 | Pre-export checklist using review errors | Block or warn on `severity=error` |

## Tickets — Sync

| ID | Ticket | DoD |
|----|--------|-----|
| A+B-520 | Staging: draft with intentional weak grounding shows findings | Checklist |

---

## Non-goals

- Replacing human evidence accept/reject (`claim_reviews`)  
- Auto-fixing manuscript without user action  

---

## Exit criteria

- [ ] Users can see and act on findings before export  
- [ ] Version stamped  
- [ ] Persistence either shipped or explicitly deferred with date  
- [ ] Distinct copy: “Research Reviewer” vs “Evidence review”
