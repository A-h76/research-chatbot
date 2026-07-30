# EPIC-0004 — Writing Engine

| Field | Value |
|-------|-------|
| **Status** | Ready after EPIC-0001; **needs** EPIC-0002 extract+accept path |
| **Priority** | P0 flagship |
| **Depends on** | EPIC-0001; EPIC-0002 (accepted evidence available); EPIC-0003 shell helpful |
| **IDD / Contracts** | IDD-0003 §7–8 · IDD-0004 Writing · domain section types · api-contracts |
| **Split** | **A** = writing intelligence services/APIs · **B** = Writing Workspace UI |

---

## Intent

Backend: Evidence ? reasoning/outline support ? **grounded paragraph** with evidence mapping.
Frontend: Outline | Manuscript | Evidence desk (EPIC-0003 shell).

**Contract route (frozen):** `POST /api/evidence/writing`

Do **not** add a parallel `POST /writing/generate` without ADR.

---

## Backend pipeline (Developer A)

Accepted EvidenceObjects
? EvidenceQuery (intent + section_type + scope)
? Retrieve / Rank (from EPIC-0002)
? Writing intelligence (plan ? draft ? bind citations)
? GroundedWritingResult { text, citations, metrics, review?, writing_version }

Every generated paragraph must link back to evidence ids.

---

## Outcomes

1. Document CRUD + autosave + versions
2. `POST /api/evidence/writing` ? `ok` | `blocked`
3. Insert grounded text + persist bindings
4. Research Confidence metrics (decision-useful only)
5. Export markdown with provenance
6. B consumes stable DTO without A’s internals

---

## Granular tickets — Developer A

| ID | Ticket | DoD |
|----|--------|-----|
| **A-401** | Writing documents API conformance | Autosave `409` documented/tested |
| **A-402** | Grounded writing API (`/api/evidence/writing`) | Stable `GroundedWritingResult`; `writing_version`; citations[] |
| **A-403** | Input via EvidenceQuery + optional document_id | Reject forbidden keys (`model`, `prompt`, …) |
| **A-404** | Blocked path `insufficient_evidence` | Deterministic when no accepted evidence |
| **A-405** | Evidence mapping on output | Every citation ? `evidence_object_id` |
| **A-406** | Bindings create/list/delete | Same project + ownership |
| **A-407** | Export markdown + provenance | `writing_version` + evidence ids in export meta |
| **A-408** | Contract tests for writing DTO | ok + blocked fixtures |
| **A-409** | Citation style formatting (APA/MLA/IEEE/BibTeX) | Deferred until bindings+export stable; optional late ticket |

## Tickets — Developer B

| ID | Ticket | DoD |
|----|--------|-----|
| B-411 | Writing desk 3-column layout | Outline · Manuscript · Evidence |
| B-412 | Grounded generate UX + ResearchProgressStage | `blocked` as product state, not transport error |
| B-413 | Citation ? Inspector | Uses EPIC-0002 Inspector |
| B-414 | Confidence / metrics strip | Hide vanity metrics |
| B-415 | Autosave UX + version restore | Conflict toast |
| B-416 | Export tab | Download / copy markdown |
| B-417 | apiClient only (no raw fetch) | 401 consistency |

## Sync

| ID | Ticket | DoD |
|----|--------|-----|
| A+B-420 | Staging lit-review: accept 3 evidence ? grounded ok ? bind ? export | Signed checklist |

---

## Non-goals

- Full Reviewer persistence (EPIC-0005)
- Consensus/conflict UI (EPIC-0006)
- DOCX / journal packs (IDD-0010)
- Parallel generate endpoint

---

## Exit criteria

- [ ] Grounded lit-review works with **accepted** evidence only
- [ ] Blocked state teaches extract/accept
- [ ] Bindings survive reload
- [ ] Export shows provenance
- [ ] No “Thinking…” / free-prompt generate path
- [ ] A-409 citation styles explicitly deferred or done—documented either way
