# Research Workflow Contracts v1.0 — Complete + Freeze

**Status:** **COMPLETE / FROZEN** (workflow *contracts* — not every product surface)  
**Effective:** 2026-08-05  
**Chapter:** Library-spine Phase E · Bite 16  
**contracts_version:** `1.3.0`  
**Engine:** Research Workflow Engine v1.0 (`backend/workflow/`)  
**Companions:** [RI-v3.0-COMPLETE-FREEZE.md](./RI-v3.0-COMPLETE-FREEZE.md) · [workflow/](./workflow/)

---

## Mission

> Every research paper journey is one canonical pipeline with many entry points.
> Every business rule has one implementation with many APIs.
> Workflow contracts make that inspectable — like RI stage contracts.

```text
One Research Journey
        ↓
One Canonical Pipeline
        ↓
Many Entry Points

Import → UFTR → SUE → Evidence → Writing → Review → Publication
```

These contracts freeze **boundaries** (input / output / invariants / events / ownership).
They do **not** freeze UI chrome or require Kafka / microservices / agents.

---

## Capability map (workflow contracts)

| ID | Contract | Status | Package / SoT |
|----|----------|--------|----------------|
| WF-001 | [Import](./workflow/import-contract.md) | ✅ Frozen | `backend/library/import_service.py` · `backend/upload/upload_service.py` |
| WF-002 | [Evidence](./workflow/evidence-contract.md) | ✅ Frozen | `backend/evidence/` · [evidence-contract.md](./evidence-contract.md) (A-402) |
| WF-003 | [Writing](./workflow/writing-contract.md) | ✅ Frozen | `backend/evidence/writing/` · WI / assistant |
| WF-004 | [Review](./workflow/review-contract.md) | ✅ Frozen | Evidence review + ResearchDecision · Reviewer engine |
| WF-005 | [Publication](./workflow/publication-contract.md) | ✅ Frozen (MVP surface) | Export / share paths — extend only via this contract |

UFTR remains a **platform** contract: [uftr-contract.md](./uftr-contract.md). SUE / paper analysis remains under RI + ACR — not a separate workflow contract; it is the **SUE** step between Import and Evidence.

---

## Shared schema (every WF contract)

| Section | Meaning |
|---------|---------|
| **Input** | What must be true / present to enter the stage |
| **Output** | What the stage produces (artifacts, status) |
| **Invariants** | Rules that must not be broken |
| **Events** | Domain events + workflow step transitions |
| **Ownership** | Product domain / package that owns the rule |

---

## Feature freeze rules

**Allowed without ADR**

- Bug fixes / performance
- Additive optional fields clients may ignore
- New *entry points* that call existing ImportService / UploadService / extract / composer
- Advancing WorkflowEngine step notes without changing contract meaning

**Not allowed without ADR**

- A second Import / Evidence extract / grounded-write implementation
- Provider-specific forks after bytes are accepted (violates Golden Rule)
- Publishing UI / clickstream events on the Domain Event Bus
- Renaming frozen domain event names (`PaperImported`, …) incompatibly
- Skipping Evidence when generating grounded literature claims

**Version label:** Research Workflow Contracts **v1.0**.

---

## Doctrine (binding — Engineering Constitution)

```text
One Research Journey  →  One Canonical Pipeline  →  Many Entry Points
One Business Rule     →  One Implementation      →  Many APIs
```

Stronger than “don’t duplicate code.” See [`ENGINEERING-CONSTITUTION-v1.md`](../ENGINEERING-CONSTITUTION-v1.md) §0.5.

---

## Related

- Engine: `backend/workflow/` (Bite 15)
- Domain events: `backend/domain_events/` (Bite 14)
- Tracker: [`ENGINEERING-EVOLUTION-TRACKER.md`](../ENGINEERING-EVOLUTION-TRACKER.md)
- Health: [`ARCHITECTURE-HEALTH.md`](../ARCHITECTURE-HEALTH.md)
