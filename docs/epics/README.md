# Dhund Epic Roadmap

**Rule:** Do not start large implementation streams (EPICs 0002–0006) until **EPIC-0001** is complete and **Accepted**.

## North Star (EPIC-0001)

Two developers implement 0002–0006 **in parallel** using only published IDD + [`docs/contracts/`](../contracts/README.md). Implementation talk beyond contract clarification should be unnecessary.

## Document hierarchy

```text
ADRs
  ? Architecture (Now-Status, EPIC-0001 principles)
    ? IDD (docs/idd/)
      ? Contracts (docs/contracts/)  ? living, frozen after 0001
        ? Implementation
```

## Epic map

| Epic | Title | Gate |
|------|-------|------|
| [EPIC-0001](./EPIC-0001-Architecture-Foundation.md) | Architecture Foundation | **Must complete first** |
| [EPIC-0002](./EPIC-0002-Evidence-Layer.md) | Evidence Layer (granular A-201…A-215) | After 0001 Accepted |
| [EPIC-0003](./EPIC-0003-Research-Workspace.md) | Research Workspace | After 0001 |
| [EPIC-0004](./EPIC-0004-Writing-Engine.md) | Writing Engine | After 0001 + usable evidence |
| [EPIC-0005](./EPIC-0005-Reviewer.md) | Reviewer | After grounded writing |
| [EPIC-0006](./EPIC-0006-Research-Intelligence.md) | Research Intelligence | After evidence list/search |

```text
EPIC-0001 ? Architecture Approved ? only then ? EPIC-0002+
```

**Developer A priority:** Evidence Layer (**EPIC-0002**, tickets A-201…A-215) ? Evidence APIs/search ? Writing intelligence (**EPIC-0004**, `/api/evidence/writing`) ? Reviewer (**0005**) ? Consensus/RI (**0006**).

Do not rename EPIC-0002 to “Research Intelligence”—that name is reserved for **EPIC-0006**.

## Ownership (summary)

| | Developer A | Developer B |
|--|:-----------:|:-----------:|
| DB, APIs, AI, Evidence, Search, DU, KG, Backend tests | ? | |
| Design system, React, UX, Workspace UI, state, FE tests | | ? |

Full matrix: [EPIC-0001 § Ownership](./EPIC-0001-Architecture-Foundation.md#ownership-matrix).
