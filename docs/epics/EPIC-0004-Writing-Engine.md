# EPIC-0004 — Writing Engine

| Field | Value |
|-------|-------|
| **Status** | Ready after EPIC-0001; **needs** EPIC-0002 extract+accept path |
| **Priority** | P0 flagship |
| **Depends on** | EPIC-0001; EPIC-0002 (accepted evidence available); EPIC-0003 shell helpful |
| **IDD** | 0003 §7–8 · 0004 Writing page · 0002 section types |

---

## Intent

Deliver the **Writing Workspace**: Outline | Manuscript | Evidence, grounded generation via EvidenceQuery (no free-prompt thesis), bindings, export snapshot.

---

## Outcomes

1. Document CRUD + autosave + versions  
2. `POST /api/evidence/writing` → ok | blocked  
3. Insert grounded text + persist bindings  
4. Research Confidence metrics (useful only)  
5. ResearchProgressStage during generate  
6. Export markdown (sync or job)  

---

## Tickets — Developer A

| ID | Ticket | DoD |
|----|--------|-----|
| A-401 | Writing documents API conformance | Autosave `409` conflict behavior documented/tested |
| A-402 | Grounded writing endpoint stable DTO | `writing_version`, citations, metrics, disclaimer |
| A-403 | Blocked path `insufficient_evidence` | Deterministic when no accepted evidence |
| A-404 | Bindings create/list/delete | Ownership + same project checks |
| A-405 | Export markdown includes provenance stamps | writing_version + evidence ids |
| A-406 | Forbid EvidenceQuery model/prompt keys | Contract tests |

## Tickets — Developer B

| ID | Ticket | DoD |
|----|--------|-----|
| B-411 | Writing desk 3-column layout | Outline · Manuscript · Evidence |
| B-412 | Grounded generate UX + stages | Progress copy; handle `blocked` as product state |
| B-413 | Citation → Inspector deep link | Uses EPIC-0002 Inspector |
| B-414 | Confidence / metrics strip | Hide non-decision metrics |
| B-415 | Autosave UX + version restore | Conflict toast |
| B-416 | Export tab | Download / copy markdown |
| B-417 | Replace remaining raw `fetch` with apiClient | 401 consistency |

## Tickets — Sync

| ID | Ticket | DoD |
|----|--------|-----|
| A+B-420 | Staging lit-review: accept 3 evidence → grounded ok → bind → export | Signed checklist |

---

## Non-goals

- Full Reviewer persistence (EPIC-0005 may start overlapping)  
- Consensus/conflict visualizations (0006)  
- DOCX/journal packs (IDD-0010)  

---

## Exit criteria

- [ ] Grounded lit-review works with accepted evidence only  
- [ ] Blocked state teaches user to extract/accept  
- [ ] Bindings survive reload  
- [ ] Export shows provenance  
- [ ] No “Thinking…” copy on generate
