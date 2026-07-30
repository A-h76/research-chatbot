# 06 — API Contract Review

**Status:** Draft for review · **No contracts modified — this is a gap list only,
per the charter's "document, don't implement" rule for backend changes.**

Two contract sources exist and are compared against the frontend's actual API calls:
- **`docs/idd/IDD-0003-API-Contracts.md`** (new, "Proposed," 2026-07-30) — covers
  Identity, Projects, Library, Evidence Platform, Research Intelligence, Writing
  Studio, Search, Jobs, Export.
- **`docs/api-contract.md`** (older, ~2026-07-16) — covers the pre-existing CRUD/chat
  surface (`/api/files`, `/api/projects`, `/api/citations`, `/api/notes`,
  `/api/conversations`, `/api/memories`, `/api/chat`, `/api/uploads/presign`,
  `/api/analysis/compare`). Does not mention Evidence/Writing/RI at all.

Frontend call sites checked directly (not paraphrased): `features/evidence/api.ts`,
`features/writing/api.ts`, plus the api.ts files listed in
[01-Frontend-Architecture-Review.md](01-Frontend-Architecture-Review.md).

## Compatible

| Frontend call | Endpoint | IDD reference |
|---|---|---|
| `evidenceApi.list` | `GET /api/projects/{id}/evidence` | IDD-0003 §7, line 178 |
| `evidenceApi.explain` | `POST /api/evidence/explain` | IDD-0003 §7, line 210; frozen by ADR-0003/ADR-0005 |
| `evidenceApi.extract` | `POST /api/projects/{id}/evidence/extract` | IDD-0003 §7, line 188 |
| `evidenceApi.review` | `POST /api/evidence/{id}/reviews` | IDD-0003 §7, line 205 |
| `evidenceApi.createBinding` | `POST /api/documents/{id}/evidence-bindings` | IDD-0003 §8, line 325 |
| `evidenceApi.{search,retrieve,rank,consensus,conflict,reason,writing}` | `POST /api/evidence/{search,retrieve,rank,consensus,conflict,reason,writing}` | IDD-0003 §7, lines 242–263 — the full RI pipeline-stage set matches 1:1, including the forbidden-keys discipline (no `prompt`/`model`/`temperature` in any request body — confirmed absent in `evidence/api.ts`) |
| `writingApi.{listDocuments,createDocument,listVersions,restoreVersion}` | `GET/POST /api/writing/documents`, `GET .../versions`, `POST .../restore` | IDD-0003 §8, lines 302–323 |

This is the encouraging finding: the **Evidence Platform surface (the most
architecturally load-bearing part of the product, per ADR-0003) is already wired up
correctly and matches the frozen contract closely**, including the RI pipeline
stages that didn't exist in the older `docs/api-contract.md` at all.

## Needs Clarification

These are real discrepancies between what's implemented and what IDD-0003 specifies —
not assumed bugs. Per the charter, these go to Developer A rather than being resolved
unilaterally; see [docs/contracts/frontend-feedback.md](../contracts/frontend-feedback.md).

1. **Writing document autosave — different endpoint, different conflict-guard field.**
   IDD-0003 line 314 specifies autosave as `PATCH /api/writing/documents/{id}` with
   body `{title?, body?, autosave_key?}` and a `409` on `autosave_key` mismatch. The
   frontend (`writingApi.ts` lines 44–51) instead calls a **separate**
   `POST /api/writing/documents/{id}/autosave` with body
   `{title, content, current_version, idempotency_key}` — different HTTP method,
   different route, different conflict-guard field name (`current_version` vs.
   `autosave_key`), and a different field name for the document body
   (`content` vs. `body`). It's unclear whether the frontend implements an
   already-agreed variant the IDD hasn't caught up to, or the reverse. Flagged, not
   guessed at.
2. **Writing document export — entirely different route namespace.** IDD-0003 line
   385 specifies `POST /api/writing/documents/{id}/export` (`{format, citation_style?}`,
   returning either a `202` job or `200` sync content). The frontend's
   `writingApi.exportNotes/exportAnalysisUrl/exportChatUrl` instead hit
   `/api/export/notes`, `/api/export/analysis/{fileId}`, `/api/export/chat/{convId}` —
   a resource-scoped-by-notes/analysis/chat pattern, not the document-scoped pattern
   the IDD specifies. This looks like the **pre-existing export system** (built
   before the Writing Studio IDD section existed) rather than an implementation of
   the new contract — worth confirming with Developer A whether the new
   `/api/writing/documents/{id}/export` route exists yet at all, or whether the IDD
   should instead document the existing `/api/export/*` routes as the frozen contract.
3. **`GET /api/writing/documents/{id}` (single-document fetch) has no frontend
   caller.** `writingApi.ts` has `listDocuments` but no single-document getter. Could
   be intentional (the page loads the list and finds the doc client-side) or a real
   gap if `WritingPage.tsx` needs direct-link-to-document support — not established
   either way in this review.
4. **`DELETE /api/evidence-bindings/{id}` has no frontend caller.** `evidenceApi.ts`
   only implements `createBinding`; there's no "remove citation binding" call. Same
   ambiguity as #3 — may simply mean the UI feature (unbind a citation) hasn't been
   built yet, not that the contract is wrong.
5. **`file_id`/`paper_id` dual-naming transition** (IDD-0003 §1.1, rule 6: "clients
   MUST accept both `paper_id` and `file_id`"). Not verified against every response
   handler in this pass — flagged as a thing to specifically check when writing
   [07-TypeScript-Type-Plan.md](07-TypeScript-Type-Plan.md)'s interfaces, since a type
   that only declares `file_id` would silently violate this rule.

## Missing (named in IDD, not yet built anywhere in the frontend)

| IDD contract | Status |
|---|---|
| Reviewer endpoints (IDD-0003, referenced via EPIC-0005) | No `features/reviewer/` folder, no API client — matches [02-UI-Inventory.md](02-UI-Inventory.md)'s finding that the Reviewer UI doesn't exist yet. Correctly gated on EPIC-0001→EPIC-0004→EPIC-0005 sequencing, not a bug. |
| `GET /api/jobs/{job_id}` generic job-status polling (IDD-0003 §10) | The existing `pipeline/api.ts` has its own polling for pipeline-specific status; not verified whether it already satisfies this generic contract or is a parallel mechanism — needs a direct read of `pipeline/api.ts` against IDD-0003 §10 before concluding either way (not done in this pass). |
| `GET /api/export-jobs/{id}` (export job status) | No frontend caller found — consistent with #2 above (the export contract itself isn't wired up yet). |

## Deferred (explicitly out of v1 scope per the IDD itself)

- `/api/v2` versioned surface — IDD-0008 states the current surface is unversioned
  v1 by design; not a gap.
- Normalized `authors` table, `paper_sections`/`paper_figures` tables (IDD-0005
  "future tables") — backend-owned, no frontend contract dependency yet.
- WebSocket-based event delivery — IDD-0006 states v1 is polling/invalidation only,
  not WebSocket; the frontend's TanStack Query invalidation model already matches
  this, no action needed.

## Note on the older `docs/api-contract.md`

That document independently found **one real inconsistency already** —
`list_conversations` returns a bare unbounded array while `list_files` uses the
`{total,offset,limit,items}` envelope — which is still true today (not re-verified
against current code in this pass, but no evidence found that it's been fixed). This
predates the IDD pack and is a backend-contract issue, not a frontend one; recorded
here only so it isn't lost between the two contract documents. If Developer A adopts
IDD-0003 §1.4's single pagination envelope going forward, this existing exception
should either be fixed to match or explicitly listed as a legacy exception.
