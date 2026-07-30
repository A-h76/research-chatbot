# EPIC-0006 — Research Intelligence

| Field | Value |
|-------|-------|
| **Status** | Ready after Evidence list/search stable (EPIC-0002) |
| **Priority** | P1 differentiation / P2 polish sequencing |
| **Depends on** | EPIC-0001; EPIC-0002; Writing may consume stages earlier |
| **IDD** | 0003 §7 RI stages · 0010 extensions |

---

## Intent

Harden and productize the **RI pipeline stages** beyond writing:

```text
EvidenceQuery → Retrieve → Rank → Consensus → Conflict → Reason
```

…as APIs + selective UI, always over Evidence Objects—never raw PDFs.

---

## Outcomes

1. Contract tests for each stage  
2. Ranking strategy named (`default_v0`) + documented  
3. Consensus/conflict DTOs usable by Compare workspace  
4. Reason output inspectable  
5. FE surfaces: Compare workbench consumes consensus/conflict where valuable  

---

## Tickets — Developer A

| ID | Ticket | DoD |
|----|--------|-----|
| A-601 | Retrieve/search parity + pagination | IDD envelope |
| A-602 | Rank strategy registry + tests | Unknown strategy → 400 |
| A-603 | Consensus aggregate schema freeze | Version field on aggregate |
| A-604 | Conflict mediators catalog | Stable codes |
| A-605 | Reason stage output schema | No prompt leakage |
| A-606 | Performance budget note for project-scale evidence | Doc only if slow |

## Tickets — Developer B

| ID | Ticket | DoD |
|----|--------|-----|
| B-611 | Compare workspace wired to consensus/conflict | Empty/loading/error |
| B-612 | Optional “Evidence coverage” view using retrieve/rank | Project-scoped |
| B-613 | Types for RI DTOs in `idd.ts` | From A schemas |
| B-614 | Feature flag UI for experimental RI panels | Default off if unstable |

## Tickets — Sync

| ID | Ticket | DoD |
|----|--------|-----|
| A+B-620 | Staging: same EvidenceQuery through retrieve→rank→consensus | Shared fixture project |

---

## Non-goals

- Knowledge Graph product chrome without Evidence projection (later)  
- Research Assistant as ChatGPT home  
- New vector DB (needs ADR)  

---

## Exit criteria

- [ ] Each RI endpoint has contract tests  
- [ ] Compare or coverage UI uses ≥1 stage beyond raw list  
- [ ] No stage accepts forbidden EvidenceQuery keys  
- [ ] Ready for IDD-0010 extensions (citation intel, gaps) without breaking v1
