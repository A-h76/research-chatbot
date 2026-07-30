# EPIC-0001 — Architecture Foundation

| Field | Value |
|-------|-------|
| **Status** | In progress (docs exist; review pending) |
| **Priority** | P0 — **blocking** for EPIC-0002…0006 implementation streams |
| **Owner** | Architect + Developer A + Developer B (joint) |
| **Estimate** | 1–3 days calendar (review-heavy, not 100h of build) |
| **Depends on** | Codebase Phase 0 (`Now-Status/`), existing ADRs |
| **Produces** | Signed IDD, frozen contracts, ownership matrix, parallel-work readiness |

---

## North Star

At the completion of EPIC-0001, **two developers should be able to implement EPIC-0002 through EPIC-0006 entirely in parallel using only the published contracts in the IDD and `docs/contracts/`**.

No implementation discussion should be required beyond **contract clarification**.

---

## Intent

Establish the engineering foundation so two developers can work for weeks with **minimal blocking**:

- Shared vocabulary (Paper, EvidenceObject, WritingDocument, …)
- Frozen contracts (API, events, errors, versions, types)
- Clear A/B ownership
- Agreement on what *not* to rebuild

> Don’t start implementing the next 100 hours until this epic is **complete and reviewed**.

Architecture must never become “build feature X.”  
It must become **“agree how feature X will always work.”**

---

## Architecture Principles (non-negotiable)

These are immutable for the life of the IDD unless an **ADR** changes them.

1. **Evidence First** — All intelligent features consume Evidence Objects. Never raw PDFs as the knowledge source of record.
2. **Contract First** — Frontend depends only on published contracts (`docs/idd/` + `docs/contracts/`).
3. **API First** — UI never accesses storage, workers, or provider SDKs directly.
4. **Single Source of Truth** — One domain model. No duplicate root entities (no parallel `papers` / Claim tables).
5. **Explainability** — Every generated claim must have provenance (evidence ids, versions, anchors).
6. **Evolution over Rewrite** — Prefer extending existing architecture. Avoid unnecessary replacement.

These principles act as the **engineering constitution** for Dhund implementation work.

---

## Architecture Decision Rule

Any change affecting:

- database schema or entity meaning  
- API names, request/response bodies  
- events  
- published contracts  
- Evidence model  

**requires an ADR + review before implementation.**

Feature work alone **cannot** change architecture.  
PRs that alter frozen surfaces without an ADR are rejected.

---

## Deliverables (artifacts that must exist)

Completion is about **artifacts**, not “we reviewed stuff.”

```text
Architecture Assessment     →  Now-Status/
        ↓
IDD Pack                    →  docs/idd/  (Accepted)
        ↓
Ownership Matrix            →  this epic (§ Ownership)
        ↓
Migration Roadmap           →  Now-Status/05 + docs/idd/IDD-0008
        ↓
API Freeze                  →  docs/contracts/api-contracts/
        ↓
Type Freeze                 →  docs/contracts/frontend-contracts/
        (+ domain / event contracts)
```

| Artifact | Location | Owner of truth |
|----------|----------|----------------|
| Architecture Assessment | `Now-Status/01-…` | Architect |
| IDD Pack | `docs/idd/*` | A+B signed |
| Ownership Matrix | This epic | A+B |
| Migration Roadmap | `Now-Status/05`, IDD-0008 | Architect / A |
| Living API contracts | `docs/contracts/api-contracts/` | A |
| Domain contracts | `docs/contracts/domain-contracts/` | A |
| Event contracts | `docs/contracts/event-contracts/` | A |
| Frontend contracts / types | `docs/contracts/frontend-contracts/` | B |

**Document hierarchy:**

```text
ADRs
  → Architecture (Now-Status, principles)
    → IDD (interface definition pack)
      → Contracts (living, versioned slowly)
        → Implementation
```

---

## Definition of Frozen (after EPIC-0001 exit)

Once EPIC-0001 is **Accepted**, the following are **frozen**:

| Frozen surface | Examples |
|----------------|----------|
| Database entities (meaning) | `files`=Paper, `evidence_objects`, `documents` |
| API names / routes | Evidence, writing, library paths in contracts |
| Request bodies | EvidenceQuery shape, extract body |
| Response bodies | EvidenceObject, GroundedWritingResult, error envelope |
| Error format | `{ error, detail, fields? }` |
| Events | Envelope + catalog names in event contracts |
| Type names | TypeScript interfaces in frontend contracts |

**Changing any frozen item later requires an ADR** (and IDD/contracts revision)—not a drive-by rename in a feature PR.

Additive optional fields are allowed if clients must ignore unknowns (IDD-0008). Removals/renames are breaking.

---

## Success metric

EPIC-0001 is successful when:

> **Developer A can continue for one week without asking Developer B for implementation details.**  
> **Developer B can continue for one week without asking Developer A for implementation details.**  
> **Only published contracts are shared.**

That is the purpose of the IDD.

---

## Scope

### In scope

1. Review existing architecture work (Now-Status, ADRs, IDD)—not regenerate from scratch  
2. Approve IDD pack  
3. Publish / link living contracts under `docs/contracts/`  
4. Freeze surfaces listed above  
5. Ownership matrix  
6. Smoke path named  
7. Open questions filed as tickets—not silent assumptions  

### Out of scope

- Building EPIC-0002…0006 features  
- Large `server.py` rewrites  
- Celery / pgvector / teams  
- Pixel-perfect redesign (B work under later epics)  

---

## Ownership Matrix

| Responsibility | A | B |
|----------------|:-:|:-:|
| Database | ✅ | |
| APIs | ✅ | |
| AI / Prompt Engine | ✅ | |
| Search / Retrieval | ✅ | |
| Evidence Layer | ✅ | |
| Document Processing | ✅ | |
| Knowledge Graph (projections) | ✅ | |
| Auth (server) | ✅ | |
| Testing (Backend) | ✅ | |
| Design System | | ✅ |
| React Components | | ✅ |
| UX / Figma | | ✅ |
| Research Workspace UI | | ✅ |
| State Management | | ✅ |
| API Integration (client) | | ✅ |
| Testing (Frontend) | | ✅ |
| IDD / Contracts maintenance | ✅ | ✅ (FE contracts) |
| Marketing Jinja (optional) | ✅ | Out of SPA epics |

Zero ambiguity: if a task isn’t on this matrix, assign it in the epic ticket before coding.

---

## Tickets

### A+B-001 — IDD dual review workshop

**Type:** Review (not generation)  
**DoD:** Both have read IDD-0001…0010 + Now-Status summary; workshop notes in `docs/idd/REVIEW-NOTES.md`; blocking disagreements listed.

### A+B-002 — Sign-off on IDD pack

**Type:** Governance  
**DoD:** Sign-off table in `docs/idd/README.md` completed; Status → **Accepted**.

### A+B-003 — Publish living contracts tree

**Type:** Docs  
**DoD:** `docs/contracts/{api,domain,event,frontend}-contracts/` exists with README pointers to frozen IDD sections (or extracted snapshots). Version stamp `contracts_version: 1.0.0`.

### A-004 — Contract gap list (live API vs contracts)

**Owner:** A  
**DoD:** Table: endpoint × matches / alias / missing / deferred.

### B-005 — Type freeze file from frontend contracts

**Owner:** B  
**DoD:** `frontend/src/types/idd.ts` mirrors `docs/contracts/frontend-contracts/` (or imports generated types). No page rewrites required yet.

### B-006 — MSW / fixture plan

**Owner:** B  
**DoD:** Routes to mock first documented; folder `frontend/src/mocks/idd/` agreed.

### A-007 — Smoke path outline

**Owner:** A  
**DoD:** Upload/Import → Research Ready → Extract → Accept → Grounded write → Review → Export (manual steps OK).

### A+B-008 — Freeze declaration

**Type:** Governance  
**DoD:** This epic’s “Definition of Frozen” acknowledged in REVIEW-NOTES; ADR rule restated.

### A+B-009 — EPIC-0001 exit review (gate)

**DoD:** Exit checklist below all ☑; greenlight EPIC-0002/0003.

---

## Exit criteria (gate)

- [ ] IDD pack **Accepted** (signed)  
- [ ] Architecture Principles acknowledged by A and B  
- [ ] Deliverables exist (Assessment, IDD, Ownership, Migration pointer, API freeze, Type freeze)  
- [ ] Definition of Frozen published and agreed  
- [ ] ADR rule acknowledged  
- [ ] Success metric believed plausible (week of parallel work)  
- [ ] Smoke path written  
- [ ] EPIC-0002…0006 owners assigned  
- [ ] Explicit decision: **no 100h feature push** until this gate passes  

A sprint does not end because “we worked.”  
It ends because **we achieved the gate.**

---

## Risks if skipped

| Risk | Cost |
|------|------|
| Architecture drift mid-feature | Rework across both codebases |
| Constant renaming | Broken parallel work |
| FE builds chat-like bypasses | Positioning failure |
| Feature PRs change Evidence model | Trust / ADR violations |

---

## Next

On exit → start **EPIC-0002** and **EPIC-0003** in parallel (A-heavy / B-heavy), consuming **only** frozen contracts.
