# Dhund IDD Pack — Index

**Product:** Dhund Research Operating System  
**Purpose:** Single source of truth for parallel Frontend / Backend engineering  
**Status:** Active for Evidence / RI / Reviewer / Jobs (Track 2 A-401–A-405) — remaining sections still need dual-team sign-off  

## Documents

| ID | Document | Contents | Track-2 status |
|----|----------|----------|----------------|
| 0001 | [System Architecture](./IDD-0001-System-Architecture.md) | Executive summary, principles, modules, boundaries, naming | Proposed |
| 0002 | [Domain Model](./IDD-0002-Domain-Model.md) | Entities, lifecycles, shared constants | Active (Evidence + ReviewerRun) |
| 0003 | [API Contracts](./IDD-0003-API-Contracts.md) | REST endpoints, EvidenceQuery stages, errors | **Active** (`contracts_version` 1.2.0) |
| 0004 | [Frontend Contracts](./IDD-0004-Frontend-Contracts.md) | Per-page APIs, UX states, TypeScript interfaces | Proposed (B mirror TBD) |
| 0005 | [Database Schema](./IDD-0005-Database-Schema.md) | Tables, keys, indexes, cascades | **Active** (incl. reviewer_runs) |
| 0006 | [Events](./IDD-0006-Events.md) | Event catalog, producers/consumers, retry | Active (`ReviewCompleted`) |
| 0007 | [Auth](./IDD-0007-Auth.md) | Roles, permissions, error model | Proposed |
| 0008 | [Versioning](./IDD-0008-Versioning.md) | API/DB/deprecation policy | **Active** |
| 0009 | [Development Workflow](./IDD-0009-Development-Workflow.md) | Contract-first, mocks, DoD | Proposed |
| 0010 | [Future Extensions](./IDD-0010-Future-Extensions.md) | Product/UI extensions beyond shipped APIs | Proposed |

## Spine (non-negotiable)

```text
PDF → Document Understanding → Evidence Objects → Retrieval → Ranking
    → Consensus → Conflict → Reasoning → Writing Workspace → Reviewer → Export
```

## Living contracts (day-to-day freeze)

**Prefer** [`docs/contracts/`](../contracts/README.md) (`contracts_version: 1.2.0`) for Evidence/RI/jobs.  
See [A-405 documentation freeze](../contracts/A-405-documentation-freeze.md).

## Related existing authority

- `docs/00-constitution.md`
- `docs/adr/0001` … `0007`, **`0012`** (chat orchestration — accepted, implementation deferred)
- `Now-Status/` (Phase 0 assessment; Track-2 items updated)
- [`docs/epics/`](../epics/README.md) — EPIC-0001 gate before implementation streams

## Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer A (Backend/AI) | | | ☐ |
| Developer B (Frontend/Design) | | | ☐ |
| Architect / Product | | | ☐ |
