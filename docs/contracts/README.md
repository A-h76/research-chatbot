# Living Contracts

**Status:** Frozen — Evidence / RI / Reviewer / Jobs (Track 2 A-401–A-405)  
**Rule:** These directories (and the freeze files below) are the **slowly changing** source of truth for implementation. They derive from the IDD and ADRs.

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

## Freeze pack (start here)

| Doc | Purpose |
|-----|---------|
| [A-405-documentation-freeze.md](./A-405-documentation-freeze.md) | **Checklist + DoD for this freeze** |
| [RI-v3.0-COMPLETE-FREEZE.md](./RI-v3.0-COMPLETE-FREEZE.md) | **Phase 2 RI complete — feature freeze rules** |
| [WF-v1.0-COMPLETE-FREEZE.md](./WF-v1.0-COMPLETE-FREEZE.md) | **Research Workflow Contracts v1.0** — Import / Evidence / Writing / Review / Publication |
| [workflow/](./workflow/) | Per-stage WF contracts (input / output / invariants / events / ownership) |
| [uftr-contract.md](./uftr-contract.md) | **UFTR v1.0** — platform full-text resolution (`resolve_and_attach`) |
| [ai-capability-router-contract.md](./ai-capability-router-contract.md) | **AI Capability Router v1.0** — Job → Profile → Policy → Router → Prompt/Model Registry → Ledger |
| [research-scope-contract.md](./research-scope-contract.md) | **Research Scope / Prompt Gateway** — ALLOW \| CLARIFY \| REDIRECT before the LLM |
| [api-contracts.md](./api-contracts.md) | Public Evidence/RI/bindings/reviewer routes + RI envelope |
| [evidence-contract.md](./evidence-contract.md) | EvidenceObject, citations, stage payloads, ReviewerRun |
| [error-contract.md](./error-contract.md) | `{ error, detail }` + status matrix |
| [versioning-policy.md](./versioning-policy.md) | When to bump / ADR / `/api/v2` |
| [frontend-compatibility.md](./frontend-compatibility.md) | Developer B do/don’t |
| [job-observability.md](./job-observability.md) | A-404 job status enrichment |

## Layout

```text
docs/contracts/
├── README.md
├── A-405-documentation-freeze.md
├── RI-v3.0-COMPLETE-FREEZE.md
├── WF-v1.0-COMPLETE-FREEZE.md
├── workflow/                 # Bite 16 — Import / Evidence / Writing / Review / Publication
├── api-contracts.md
├── evidence-contract.md
├── error-contract.md
├── versioning-policy.md
├── frontend-compatibility.md
├── job-observability.md
├── api-contracts/
├── domain-contracts/
├── event-contracts/
└── frontend-contracts/
```

## Versioning

- Bump `contracts_version` in this README when any frozen field/route/type changes.
- Breaking change → ADR + IDD revision + contracts bump + notify Developer B.
- Additive optional fields → minor bump; clients ignore unknowns.

**Current:** `contracts_version: 1.3.0` (Bite 16 Research Workflow Contracts v1.0; prior 1.2.0 = A-403–A-405)

## Freeze

Surfaces listed in the freeze pack may not change incompatibly without ADR. See [versioning-policy.md](./versioning-policy.md).
