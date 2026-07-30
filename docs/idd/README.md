# Dhund IDD Pack — Index

**Product:** Dhund Research Operating System  
**Purpose:** Single source of truth for parallel Frontend / Backend engineering  
**Status:** Proposed — requires Developer A + Developer B sign-off  

## Documents

| ID | Document | Contents |
|----|----------|----------|
| 0001 | [System Architecture](./IDD-0001-System-Architecture.md) | Executive summary, principles, modules, boundaries, naming |
| 0002 | [Domain Model](./IDD-0002-Domain-Model.md) | Entities, lifecycles, shared constants |
| 0003 | [API Contracts](./IDD-0003-API-Contracts.md) | REST endpoints, EvidenceQuery stages, errors |
| 0004 | [Frontend Contracts](./IDD-0004-Frontend-Contracts.md) | Per-page APIs, UX states, TypeScript interfaces |
| 0005 | [Database Schema](./IDD-0005-Database-Schema.md) | Tables, keys, indexes, cascades |
| 0006 | [Events](./IDD-0006-Events.md) | Event catalog, producers/consumers, retry |
| 0007 | [Auth](./IDD-0007-Auth.md) | Roles, permissions, error model |
| 0008 | [Versioning](./IDD-0008-Versioning.md) | API/DB/deprecation policy |
| 0009 | [Development Workflow](./IDD-0009-Development-Workflow.md) | Contract-first, mocks, DoD |
| 0010 | [Future Extensions](./IDD-0010-Future-Extensions.md) | Consensus, KG, publication, … |

## Spine (non-negotiable)

```text
PDF → Document Understanding → Evidence Objects → Retrieval → Ranking
    → Reasoning → Writing Workspace → Reviewer → Export
```

## Related existing authority

- `docs/00-constitution.md`
- `docs/adr/0001` … `0007`
- `Now-Status/` (Phase 0 assessment)
- [`docs/epics/`](../epics/README.md) — EPIC-0001 gate before implementation streams
- [`docs/contracts/`](../contracts/README.md) — living API / domain / event / frontend contracts

## Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer A (Backend/AI) | | | ☐ |
| Developer B (Frontend/Design) | | | ☐ |
| Architect / Product | | | ☐ |
