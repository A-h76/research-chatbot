# Living Contracts

**Status:** v1.0.0 (proposed until EPIC-0001 Accepted)  
**Rule:** These directories are the **slowly changing** source of truth for implementation. They derive from the IDD and ADRs.

## Hierarchy

```text
ADRs
        │
        ▼
Architecture (Now-Status, principles)
        │
        ▼
IDD (docs/idd/)
        │
        ▼
Contracts (this tree)     ← living, versioned
        │
        ▼
Implementation
```

| Kind of decision | Source of truth |
|------------------|-----------------|
| Why we chose X | `docs/adr/` |
| How the system is shaped | `Now-Status/`, EPIC-0001 principles |
| Full interface definition | `docs/idd/` |
| What A/B implement against day-to-day | **`docs/contracts/`** |
| Code | repo packages |

## Layout

```text
docs/contracts/
├── README.md                          ← you are here
├── api-contracts/                     ← Developer A
├── domain-contracts/                  ← Developer A
├── event-contracts/                   ← Developer A
└── frontend-contracts/                ← Developer B
```

## Versioning

- Bump `contracts_version` in this README when any frozen field/route/type changes.
- Breaking change → ADR + IDD revision + contracts bump + EPIC-0001-style review.
- Additive optional fields → minor bump; clients ignore unknowns.

**Current:** `contracts_version: 1.0.0`

## Freeze

After EPIC-0001 exit, surfaces listed in [Definition of Frozen](../epics/EPIC-0001-Architecture-Foundation.md#definition-of-frozen-after-epic-0001-exit) may not change without ADR.
