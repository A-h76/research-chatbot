# WF-003 — Writing Contract

**Status:** Frozen (Workflow Contracts v1.0)  
**contracts_version:** `1.3.0`  
**Workflow step:** `Writing`  
**Source of truth:** `backend/evidence/writing/` (composer, binder, assistant routes) · RI-009 bridge  
**Freeze pack:** [../WF-v1.0-COMPLETE-FREEZE.md](../WF-v1.0-COMPLETE-FREEZE.md)  
**Related:** [../RI-v3.0-COMPLETE-FREEZE.md](../RI-v3.0-COMPLETE-FREEZE.md) · citation payload in [../evidence-contract.md](../evidence-contract.md) §3

---

## 1. Input

| Kind | Required | Notes |
|------|----------|--------|
| Project scope | yes | Writing is project-grounded |
| EvidenceObjects | yes for grounded lit | Supporting claims with ids |
| Optional RI context | optional | Themes / consensus / gaps — organize only |
| User id | yes | Authz + ledger attribution |

**Entry points (many):** WI `POST /api/evidence/writing`, writing assistant, document shell compose — **one** grounded composer path via ACR → Gateway → AI Ledger (no second “freeform lit invent” engine).

---

## 2. Output

| Artifact | Meaning |
|----------|---------|
| Draft text | Grounded paragraphs with `[#id]` markers from EvidenceObjects |
| `citations[]` | A-402 citation shape (`evidence_id`, `file_id`, quote/claim, …) |
| Provenance | execution_id / prompt_version / hashes where required (RI-009) |
| WorkflowInstance | `Writing` → `completed` |

---

## 3. Invariants

1. **No invented literature** — every factual claim in grounded mode must bind to EvidenceObject ids.
2. **One grounded compose implementation** — Gateway composer / WI path; assistant uses `invoke_prompt_llm` (ACR), not a parallel OpenAI client.
3. **Citation field names frozen** — use `evidence_id` (not `evidence_object_id`) on writing citations.
4. **LLM is last** — retrieval / ranking / RI context precede generation (RI-009).
5. **UI events are not domain events** — do not publish `ui.*` on DomainEventBus.
6. Cost / AI provenance via ledger façade (`record_acr_execution` / platform façade).

---

## 4. Events

| Domain event | When |
|--------------|------|
| `WritingGenerated` | Successful grounded compose (WI gateway composer) |
| `AIExecutionCompleted` | Ledger façade after ACR write |

| Workflow step | Transition |
|---------------|------------|
| `Writing` | → `completed` (project-scoped advance on active file journeys) |

Writing shell activity logs (`publish_writing_event`) may remain as **local** instrumentation; they are not substitutes for `WritingGenerated`.

---

## 5. Ownership

| Owns | Does not own |
|------|----------------|
| **Writing** — binder, composer, citation binding, draft artifacts | Evidence extract; Reviewer critique engine (may nest until extracted) |
| **AI Platform** — Gateway / ACR / Ledger for the call | Product wording of sections |

**PR gate:** A second “generate literature draft from evidence” stack requires ADR + retirement plan.
