# A-405 — Documentation & IDD Freeze Checklist

**Status:** Complete (2026-07-30)  
**contracts_version:** `1.2.0`  
**Scope:** Lock Track 2 (A-401 → A-404) into IDD + living contracts so Developer B and future backend work treat published docs as compatibility commitments.

## Compatibility commitment

After A-405:

1. **Day-to-day SoT for Evidence / RI / reviewer / job status** → [`docs/contracts/`](./README.md)  
2. **Full interface pack** → [`docs/idd/`](../idd/README.md) (Active for Track-2 surfaces)  
3. **Why** → [`docs/adr/`](../adr/)  
4. Legacy [`docs/api-contract.md`](../api-contract.md) is **historical** for hybrid chat/upload notes — not the Evidence freeze.

Breaking changes require ADR + contracts bump + IDD revision (see [versioning-policy.md](./versioning-policy.md)).

## Track 2 → doc map

| Ticket | Shipped | Freeze / docs |
|--------|---------|----------------|
| A-401 Reviewer Persistence | `reviewer_runs` / `reviewer_findings`, GET runs, `ReviewCompleted` | [evidence-contract.md](./evidence-contract.md) §5 · IDD-0005 · IDD-0006 |
| A-402 Evidence API Stabilization | RI envelope, EvidenceObject, errors | [api-contracts.md](./api-contracts.md) · [error-contract.md](./error-contract.md) |
| A-403 Ranking & Consensus | Strategy registry, consensus/conflict metrics | [api-contracts.md](./api-contracts.md) §11 · [evidence-contract.md](./evidence-contract.md) |
| A-404 Job Observability | lifecycle / retry / timings / metrics | [job-observability.md](./job-observability.md) · IDD-0003 §10 |
| A-405 Doc freeze | This checklist + IDD/ADR/Now-Status alignment | You are here |

## Freeze checklist (DoD)

- [x] Every public Evidence/RI endpoint documented in contracts + IDD-0003  
- [x] EvidenceObject + RI envelope frozen  
- [x] Error body `{ error, detail }` documented  
- [x] Reviewer persistence tables + reconstruct APIs documented  
- [x] Ranking strategies + additive metrics documented  
- [x] Job status observability documented  
- [x] `contracts_version` consistent at **1.2.0**  
- [x] Legacy `docs/api-contract.md` banners to contracts  
- [x] ADRs 0005 / 0007 / 0012 point at living contracts / Track 2 done  
- [x] Now-Status no longer claims reviewer “not durable”

## Explicitly not frozen by A-405

- Chat `/api/chat` orchestration (ADR-0012 design; implementation deferred)  
- Account / export / support route extractions from `server.py`  
- Frontend TypeScript IDD mirror (`frontend/src/types`) — B follow-up  
- Ideal path renames (`/api/evidence-objects`, `/api/papers`)
