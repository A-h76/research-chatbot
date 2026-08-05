# WF-004 — Review Contract

**Status:** Frozen (Workflow Contracts v1.0)  
**contracts_version:** `1.3.0`  
**Workflow step:** `Review`  
**Source of truth:** Evidence review routes · `ResearchDecision` · Reviewer engine (`execute_reviewer`)  
**Freeze pack:** [../WF-v1.0-COMPLETE-FREEZE.md](../WF-v1.0-COMPLETE-FREEZE.md)

Covers **researcher decisions on evidence** and **manuscript-vs-evidence critique**. Both are “Review” in the journey; ownership stays explicit below.

---

## 1. Input

### A. Evidence review (human decision)

| Kind | Required | Notes |
|------|----------|--------|
| `evidence_id` | yes | Owned EvidenceObject |
| Review payload | yes | `accepted` \| `rejected` \| `edited` + reason |
| User authz | yes | Owner |

### B. Writing Reviewer (critique)

| Kind | Required | Notes |
|------|----------|--------|
| Draft / section text | yes | Under review |
| Evidence bindings / ids | yes | Critique is Evidence-first |
| Project scope | yes | |

**Entry points (many):** Evidence review API, Reviewer run API/UI — **one** decision persistence model; **one** `execute_reviewer` for automated critique.

---

## 2. Output

| Artifact | Meaning |
|----------|---------|
| `ClaimReview` + status transition | Object → accepted / rejected / superseded chain |
| `ResearchDecision` row | Append-only researcher decision trail |
| `ReviewerRun` (when critique) | Persisted critique + ledger parent link |
| WorkflowInstance | `Review` → `completed` on decision recorded |

---

## 3. Invariants

1. **Decisions are append-only** — ResearchDecision / review history is not silently rewritten.
2. **Edited evidence supersedes** — do not overwrite quote/claim in place without supersession (A-402).
3. **One Reviewer execution path** — `execute_reviewer` + ACR/ledger; no parallel “score this draft” SDK island.
4. **Evidence-first critique** — Reviewer must not invent supporting papers.
5. Workflow instrumentation (`evidence_accepted` / `decision_recorded` breadcrumbs) must not become a second decision store.
6. Domain Event Bus handlers for Review must be idempotent (`event_id`).

---

## 4. Events

| Domain event | When |
|--------------|------|
| `EvidenceAccepted` | Accept / edit-accept after successful commit |
| `ResearchDecisionRecorded` | ResearchDecision persisted |
| `AIExecutionCompleted` | Automated Reviewer ACR completion |

| Workflow step | Transition |
|---------------|------------|
| `Evidence` | may → `completed` on accept |
| `Review` | → `completed` on `ResearchDecisionRecorded` |

---

## 5. Ownership

| Owns | Does not own |
|------|----------------|
| **Evidence** — human review mutations + ResearchDecision | Import / UFTR |
| **Reviewer** (product) — manuscript critique engine | Freeform chat that is not evidence-grounded |
| **Workflow** engine — step state only | Authoritative decision rows |

**PR gate:** A second “record researcher accept/reject” or “run reviewer” implementation requires ADR + retirement plan.
