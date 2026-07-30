# Frontend Feedback to Developer A

Per the Developer B charter's communication protocol: frontend never modifies
contracts directly. This file records where the live frontend and the proposed
`docs/idd/` contract pack disagree, or where the frontend needs something the
contracts don't yet specify. Developer A / Architect decides; entries stay open
until resolved.

Full analysis behind each entry: [docs/DevB/06-API-Contract-Review.md](../DevB/06-API-Contract-Review.md)
and [docs/DevB/10-Risks-And-Questions.md](../DevB/10-Risks-And-Questions.md).

---

## 1. Writing document autosave — endpoint/field mismatch

**API:** Writing Studio autosave
**Current behavior:**
- IDD-0003 (line 314) specifies `PATCH /api/writing/documents/{id}` with body
  `{title?, body?, autosave_key?}`, `409` on `autosave_key` mismatch.
- The live frontend (`frontend/src/features/writing/api.ts`) calls a separate
  `POST /api/writing/documents/{id}/autosave` with body
  `{title, content, current_version, idempotency_key}`.
**Suggested change:** Confirm which is the real backend contract and update the
other (either the IDD or the frontend) to match. No frontend change made yet.
**Reason:** Can't write a frozen `WritingDocument`/autosave type into
`frontend/src/types/idd.ts` without knowing which endpoint/field set is real.
**Impact:** Blocks part of EPIC-0001 ticket B-005 (type freeze file) and any
Writing Studio autosave UI work in EPIC-0004.

## 2. Writing document export — route namespace mismatch

**API:** Writing Studio export
**Current behavior:**
- IDD-0003 (line 385) specifies `POST /api/writing/documents/{id}/export`.
- The live frontend calls `/api/export/notes`, `/api/export/analysis/{fileId}`,
  `/api/export/chat/{convId}` instead — a resource-scoped-by-notes/analysis/chat
  pattern that predates the Writing Studio IDD section.
**Suggested change:** Confirm whether `/api/writing/documents/{id}/export` exists on
the backend yet. If not, either implement it, or update IDD-0003 to document the
live `/api/export/*` routes as the frozen v1 export contract.
**Reason:** Same as above — can't scaffold export UI against a route that may not
exist, or against a contract that may already be obsolete.
**Impact:** EPIC-0004 export-tab work (ticket B-416/417 area).

## 3. `EvidenceObject` field shape — IDD vs. live frontend disagree

**API:** Evidence Platform (`/api/evidence/*`, `/api/projects/{id}/evidence`)
**Current behavior:** `frontend/src/features/evidence/types.ts`'s `EvidenceObjectDTO`
(used today by working code) and `docs/idd/IDD-0004-Frontend-Contracts.md` §3's
`EvidenceObject` diverge: single `page` vs. `page_start`/`page_end` range;
`study_type`/`study_quality`/`relation`/`section` (present in the live type, absent
from IDD) vs. `evidence_type`/`finding`/`pipeline_version`/`content_hash`/
`supersedes_id` (present in IDD, absent from the live type).
**Suggested change:** Confirm the actual `/api/evidence/*` response shape so
`EvidenceObject` in `frontend/src/types/idd.ts` can be written accurately.
**Reason:** This is the canonical entity per ADR-0003 — getting its type wrong
propagates into every Evidence Inspector / Reviewer surface built on top of it.
**Impact:** Blocks EPIC-0001 ticket B-005 for this type specifically (other 16 IDD
interfaces have no known discrepancy) and EPIC-0002's Evidence Inspector page.

## 4. Two routes referenced in IDD-0003 with no frontend caller

**API:** `GET /api/writing/documents/{id}` (single-document fetch),
`DELETE /api/evidence-bindings/{id}` (remove citation binding)
**Current behavior:** Neither has a caller in `frontend/src/features/writing/api.ts`
or `features/evidence/api.ts`. Unclear whether these routes exist on the backend and
the frontend simply hasn't built the feature yet, or whether they're not implemented.
**Suggested change:** Confirm both exist and are stable before frontend work depends
on them (e.g., a "remove citation" UI action, or direct-link-to-document support).
**Reason:** Avoid building UI against routes that turn out not to exist.
**Impact:** Low urgency — no current UI work depends on either yet.

---

*No entries in this file have been acted on unilaterally by Developer B. Frontend
code and the contract documents remain unchanged pending Developer A's response.*
