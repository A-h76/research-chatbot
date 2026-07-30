# Research Intelligence v3.0 — Complete + Feature Freeze

**Status:** **COMPLETE / FROZEN**  
**Effective:** 2026-07-30  
**Chapter:** Phase 2 — Research Intelligence  
**Contracts:** `writing_version` `2.0.0` · RI stages under `docs/contracts/`

---

## Mission (achieved)

> Dhund can now ingest literature, transform it into structured evidence, synthesize
> knowledge across papers, explain its reasoning, identify gaps and methodological
> patterns, and provide a grounded foundation for academic writing.

Research Intelligence is **no longer the roadmap** — it is the **foundation** that
every writing and review feature builds upon.

---

## Capability map (shipped)

| ID | Capability | Status |
|----|------------|--------|
| RI-001 | Theme Discovery | ✅ |
| RI-002 | Evidence Matrix | ✅ |
| RI-003 | Consensus (product) | ✅ |
| RI-004 | Contradiction WHY | ✅ |
| RI-005 | Knowledge Graph (project) | ✅ |
| RI-006 | Research Gap Engine | ✅ |
| RI-007 | Timeline Intelligence | ✅ |
| RI-008 | Methodology Intelligence | ✅ |
| RI-009 | Writing Intelligence v2 — **Research → Writing bridge** | ✅ |

> Note: Product prose sometimes labels earlier paper/evidence layers as RI-001/002;
> ticket IDs in EPIC-0006 / this freeze pack are authoritative for engineering.

---

## RI-009 is a bridge — not another engine

```text
Evidence → Themes → Consensus/Conflict → Gaps → Methods → Timeline
        → Writing Context Builder → Outline → LLM (last) → Draft
        → Citation binding → Reviewer (Evidence-first)
```

Delivered under `POST /api/evidence/writing`:

1. **Outline** — theme-aware section slots (`outline[]`)
2. **Evidence-backed paragraphs** — `[#id]` markers only from EvidenceObjects
3. **Citation binding** — sentence → evidence → paper
4. **Section context** — structured RI depth (not a paper dump)
5. **Draft metadata** — `evidence_ids`, `theme_ids`, versions, `reproducibility_hash`

---

## Feature freeze rules

**Allowed without ADR**

- Bug fixes
- Performance / cost
- Quality improvements to existing RI stages
- Additive optional fields that clients may ignore (A-402 policy)

**Not allowed without user research + ADR**

- New RI capability tickets (RI-010+)
- Parallel knowledge roots (e.g. Neo4j) 
- Rewriting RI as a freeform “AI writing engine”
- Inventing EvidenceObjects / literature in any stage

**Version label:** Research Intelligence **v3.0** (product).  
Stage code versions remain per-module (`themes_version`, `matrix_version`, …, `writing_version`).

---

## Next chapter (product focus)

```text
RI v3.0 ✅  →  Phase A Writing MVP (approved)  →  Phase B E2E validation
           →  Private Alpha / researcher feedback
           →  Track 2 platform (Memory / KG v2 / Novelty) only if usage demands
```

**Execution plan:** [`docs/roadmap/EXECUTION-DUAL-TRACK.md`](../roadmap/EXECUTION-DUAL-TRACK.md)  
Sequence: Phase A → Private Alpha Success Gate → Phase B → Track 2 only if usage demands.

Primary investment is **Track 1 Product** (write / review / revise / export), not architecture % completion.

---

## Related

- Roadmap: [PHASE-2-RESEARCH-INTELLIGENCE.md](../roadmap/PHASE-2-RESEARCH-INTELLIGENCE.md)
- Epic: [EPIC-0006](../epics/EPIC-0006-Research-Intelligence.md)
- Contracts: [docs/contracts/](./README.md)
- Writing epic: [EPIC-0004](../epics/EPIC-0004-Writing-Engine.md)
