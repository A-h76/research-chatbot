# EPIC-0006 — Research Intelligence

| Field | Value |
|-------|-------|
| **Status** | **COMPLETE / FROZEN** (RI v3.0) — Writing MVP is next |
| **Priority** | Was P0 Phase 2; now foundation for Writing Intelligence |
| **Depends on** | Foundation Track 2 freeze (A-401–A-405); Evidence layer |
| **Roadmap** | [PHASE-2-RESEARCH-INTELLIGENCE.md](../roadmap/PHASE-2-RESEARCH-INTELLIGENCE.md) |
| **Freeze** | [RI-v3.0-COMPLETE-FREEZE.md](../contracts/RI-v3.0-COMPLETE-FREEZE.md) |
| **IDD** | 0003 §7 · 0010 · contracts 1.2.0 |

---

## Intent

Make Dhund **smarter** — theme discovery, evidence matrices, consensus/contradiction depth, gaps, graph, timeline, methodology support — always over Evidence Objects.

```text
EvidenceQuery → Retrieve → Rank → Consensus → Conflict → Reason
        ↓
Themes · Matrix · Gaps · KG · Timeline · Methodology → Writing v2
```

---

## Milestone

> Researchers treat Dhund as **the place where my research lives** — not an AI writing tool.

---

## Outcomes

1. Product surfaces for consensus / contradiction **WHY** (not just API JSON)  
2. Evidence matrix export from project EvidenceObjects  
3. Theme discovery over multi-paper corpora  
4. Gap engine + optional project KG / timeline  
5. Writing Intelligence v2 consumes RI outputs  

---

## Substrate already shipped (do not rebuild)

| Ticket | Status |
|--------|--------|
| A-601 Retrieve/search | Partial / continue |
| A-602 Rank strategies | **Done (A-403)** |
| A-603 Consensus metrics | **Done (A-403)** |
| A-604 Conflict mediators | **Done (A-403)** |
| A-605 Reason schema | Open |
| Contracts freeze | **Done (A-402/A-405)** |

---

## Phase 2 tickets — Research Intelligence (capability-led)

| ID | Capability | DoD (summary) | Status |
|----|------------|---------------|--------|
| **RI-001** | Theme Discovery | Themes A–N from project evidence; reconstructable run | **Done** |
| **RI-002** | Evidence Matrix | Paper × Method × Dataset × Findings × Limitations; exportable | **Done** |
| **RI-003** | Consensus Engine (product) | Agree / Disagree / Mixed / Weak evidence UX over API | **Done** |
| **RI-004** | Contradiction Engine (product) | WHY mediators (sample, method, outcome, stats) | **Done** |
| **RI-005** | Knowledge Graph | Project graph over Evidence — no parallel root without ADR | **Done** |
| **RI-006** | Research Gap Engine | Coverage gaps with evidence density | **Done** |
| **RI-007** | Research Timeline | Topic evolution by year | **Done** |
| **RI-008** | Methodology Intelligence | Advisory study-design support (not commands) | **Done** |
| **RI-009** | Writing Intelligence v2 | Drafts consume themes/matrix/gaps/consensus | **Done** |

Suggested order: **RI-003/004 → RI-002 → RI-001 → RI-006 (+ RI-005) → RI-007/008 → RI-009**.  
Detail: [Phase 2 roadmap](../roadmap/PHASE-2-RESEARCH-INTELLIGENCE.md).

---

## Tickets — Developer B (workspace surfaces)

| ID | Ticket | DoD | Status |
|----|--------|-----|--------|
| B-611 | Compare / consensus+conflict WHY UI | Empty/loading/error | **Done** (RI strip on Compare) |
| B-612 | Evidence coverage / matrix view | Project-scoped | **Done** (Matrix tab on `/research/compare`) |
| B-613 | Types for RI DTOs in `idd.ts` | From contracts | Planned |
| B-614 | Feature flags for experimental RI panels | Default off if unstable | Planned |
| B-615 | Theme / gap panels | Calm academic UX | **Done** (Themes + Gaps + Graph tabs) |

---

## Tickets — Sync

| ID | Ticket | DoD |
|----|--------|-----|
| A+B-620 | Staging fixture: retrieve→rank→consensus→conflict | Shared project |
| A+B-621 | Matrix + theme on 50–200 paper corpus | Perf + quality note |

---

## Non-goals

- Large architecture refactor “for cleanliness”  
- ChatGPT-home Research Assistant  
- Inventing EvidenceObjects / literature  
- New vector DB without ADR  

---

## Exit criteria

- [x] RI-003 + RI-004 usable in product UI  
- [x] RI-002 matrix exportable  
- [x] RI-001 or RI-006 ships on real corpus  
- [ ] No stage accepts forbidden EvidenceQuery keys  
- [x] Writing v2 gated on RI depth (RI-009)  
- [x] Ready for Publication Intelligence without breaking v1 contracts
