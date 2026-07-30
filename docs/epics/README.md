# Dhund Epic Roadmap

**Current chapter:** [Phase 2 — Research Intelligence](../roadmap/PHASE-2-RESEARCH-INTELLIGENCE.md)  
**Platform freeze:** [A-405](../contracts/A-405-documentation-freeze.md) (`contracts_version` 1.2.0)

## North star

> Dhund becomes irreplaceable when researchers stop thinking of it as an AI writing tool and start thinking of it as **the place where my research lives.**

## Capability map (organize here, not by FE/BE)

| Capability | Focus now |
|------------|-----------|
| Knowledge Acquisition | Maintain |
| Evidence Intelligence | Harden |
| **Research Intelligence** | **60% — Phase 2** |
| Writing Intelligence | 10% — after RI depth |
| Research Workspace | 20% |
| Publication Intelligence | Later |

## Document hierarchy

```text
ADRs
  ? Architecture (Now-Status)
    ? IDD (docs/idd/)
      ? Contracts (docs/contracts/)  ? frozen for Evidence/RI
        ? Phase 2 roadmap (capability tickets RI-001…009)
          ? Implementation
```

## Epic map

| Epic | Title | Gate |
|------|-------|------|
| [EPIC-0001](./EPIC-0001-Architecture-Foundation.md) | Architecture Foundation | Complete for Track-2 start |
| [EPIC-0002](./EPIC-0002-Evidence-Layer.md) | Evidence Layer | Substrate shipped |
| [EPIC-0003](./EPIC-0003-Research-Workspace.md) | Research Workspace | 20% allocation |
| [EPIC-0004](./EPIC-0004-Writing-Engine.md) | Writing Engine | 10% — RI-009 later |
| [EPIC-0005](./EPIC-0005-Reviewer.md) | Reviewer | Persistence shipped; FE open |
| [EPIC-0006](./EPIC-0006-Research-Intelligence.md) | **Research Intelligence** | **Active Phase 2** |

```text
Foundation (contracts freeze)
        ?
Phase 2 — Research Intelligence (RI-001…009)
        ?
Writing v2 + Workspace polish (supporting)
```

**Developer A priority:** RI-003/004 product APIs ? Matrix ? Themes ? Gaps/KG ? Timeline/Methodology ? Writing v2.  
**Developer B priority:** Compare/WHY UI, matrix, theme/gap panels, types from contracts.

## Ownership (summary)

| | Developer A | Developer B |
|--|:-----------:|:-----------:|
| DB, APIs, AI, Evidence, RI engines, Backend tests | ? | |
| Design system, React, UX, Workspace UI, FE tests | | ? |

Architecture refactors only when a Phase 2 capability cannot ship without them (ADR).
