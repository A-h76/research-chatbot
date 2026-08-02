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
4. Persistence of review runs (**shipped A-401 / A-503**)
5. Export can include review summary  

---

## Tickets — Developer A

| ID | Ticket | DoD |
|----|--------|-----|
| A-501 | Freeze ReviewerResult schema + codes list | Documented in IDD appendix or constants file |
| A-502 | Ensure every grounded ok response includes review | Even if issues=[] |
| A-503 | Persist reviewer run (`reviewer_runs` + `reviewer_findings`) | **Done** — migration `0035`, ORM, writing path persist, GET latest/list/by-id |
| A-504 | Emit ReviewCompleted event/payload | **Done** — outbox on persist (`IDD-0006`) |
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

- [x] Users can see and act on findings before export  
- [x] Version stamped  
- [x] Persistence shipped (`reviewer_runs` / `reviewer_findings`, reconstruct APIs, `ReviewCompleted`)
- [x] Distinct copy: “Research Reviewer” vs “Evidence review”

**V1 closed 2026-08-02:** B-511–B-514 + A-505 (`reviewer_version` / `issue_count` in export metadata).
