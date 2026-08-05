# WF-002 — Evidence Contract (Workflow)

**Status:** Frozen (Workflow Contracts v1.0)  
**contracts_version:** `1.3.0`  
**Workflow step:** `Evidence` (after `SUE`)  
**DTO / RI freeze:** [../evidence-contract.md](../evidence-contract.md) (A-402/A-403) — **payload SoT**  
**Source of truth (pipeline):** `backend/evidence/services/extract_engine.py` · worker `evidence_extract`  
**Freeze pack:** [../WF-v1.0-COMPLETE-FREEZE.md](../WF-v1.0-COMPLETE-FREEZE.md)

This document freezes the **workflow boundary**. Field-level EvidenceObject / RI stage shapes remain in A-402.

---

## 1. Input

| Kind | Required | Notes |
|------|----------|--------|
| Owned `file_id` + `project_id` | yes | Extract is project-scoped |
| Text / parsed content | yes | From prior Import → worker import / phase1 |
| Pipeline version | yes | Extract pipeline semver on runs |
| User authz | yes | Owner of project + file |

**Entry points (many):** worker `evidence_extract`, sync extract API, auto-enqueue after SUE — **one** `execute_evidence_extraction` (or documented successor).

SUE / `paper_analysis` / `phase1_analysis` are **upstream** (step `SUE`), not alternative evidence roots.

---

## 2. Output

| Artifact | Meaning |
|----------|---------|
| `EvidenceObject` rows | Candidate claims with quote/span/provenance (A-402 DTO) |
| Extraction run record | Idempotency / pipeline version |
| RI stage inputs | Objects feed themes, matrix, consensus, writing |
| WorkflowInstance | `Evidence` → `completed` (or `running` until accept) |

Downstream writing **must** cite EvidenceObject ids — never invent literature.

---

## 3. Invariants

1. **Evidence First** — grounded research claims require EvidenceObjects; no parallel “AI said so” corpus.
2. **One extract implementation** — new extract paths call the canonical engine; do not reimplement claim/span logic in a connector.
3. **Status vocabulary frozen** — `candidate` \| `accepted` \| `rejected` \| `superseded` (A-402).
4. **Append-only edits** — user edits supersede; do not silently mutate quote/claim identity without supersession.
5. **Contract outbox events** (durable) remain complementary to domain events — do not replace A-402 emit sites with Kafka.
6. RI stages consume EvidenceObjects; they do not invent papers.

---

## 4. Events

| Domain event | When |
|--------------|------|
| `EvidenceAccepted` | Human review accepts / edit-accepts an object |
| `AIExecutionCompleted` | Extract / ACR path records via ledger façade (when applicable) |

| Workflow step | Transition |
|---------------|------------|
| `Evidence` | → `running` after SUE job done; → `completed` on accept or successful extract note |
| Durable | `EvidenceUpdated` (outbox / contract emit) on review mutations |

---

## 5. Ownership

| Owns | Does not own |
|------|----------------|
| **Evidence** domain — objects, extract, review mutations, RI stages | Library identity / UFTR / storage keys |
| **Research Intelligence** — themes/matrix/… over Evidence | Second evidence store |

**PR gate:** A second EvidenceObject write path or extract algorithm requires ADR + retirement plan.
