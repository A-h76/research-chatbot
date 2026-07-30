# 07 — TypeScript Type Plan

**Status:** Draft for review · **Rule: interfaces come from the IDD verbatim. No
invented properties, no guessed backend behavior.**

## Plan

1. Create `frontend/src/types/idd.ts` containing the 17 interfaces from
   `docs/idd/IDD-0004-Frontend-Contracts.md` §3 **verbatim, unmodified**:
   `ConfidenceBand`, `EvidenceStatus`, `ResearchReadiness`, `User`, `Project`,
   `AuthorRef`, `Paper`, `EvidenceObject`, `EvidenceQuery`, `WritingSectionType`,
   `WritingDocument`, `ReviewerFinding`, `GroundedWritingResult`, `CitationBinding`,
   `SearchResult`, `JobStatus`, `ExportJob`, `ApiErrorBody`, `Paginated<T>`. This is
   exactly what `docs/contracts/frontend-contracts/README.md` names as the "frozen
   type names" this file is supposed to hold, and it currently doesn't exist.
2. **Do not delete or rewrite `frontend/src/types/api.ts` or feature-local types
   (`features/evidence/types.ts`, `features/pipeline/types.ts`,
   `features/writing/types/writing.ts`) to force-fit them into `idd.ts`.** Several of
   them diverge from the IDD interfaces in ways that look like real, load-bearing
   differences from actual backend responses, not staleness — see "Reconciliation
   needed" below. Migrating call sites onto `idd.ts` types is a per-feature decision
   for Sprint work, not a Phase-1 rename.
3. New code (EPIC-0002+ features — Evidence Inspector page, Reviewer UI, Writing
   Studio expansion) should import from `idd.ts` first, and only add a feature-local
   type when the IDD genuinely doesn't cover the shape.

## Reconciliation needed — concrete example found in this review

`features/evidence/types.ts`'s `EvidenceObjectDTO` (used today by
`evidenceApi.explain`/`list`/etc., see [06-API-Contract-Review.md](06-API-Contract-Review.md))
and IDD-0004 §3's `EvidenceObject` are **not the same shape**, despite both
representing "an Evidence Object":

| Field | `EvidenceObjectDTO` (current, live) | `EvidenceObject` (IDD-0004 §3) |
|---|---|---|
| `claim` / `quote` | `string` (non-nullable) | `string \| null` |
| Page range | `page: number \| null` (single) | `page_start`/`page_end: number \| null` (range) |
| `project_id`, `paper_id` | absent | present |
| `evidence_type`, `finding`, `pipeline_version`, `content_hash`, `supersedes_id`, `created_at` | absent | present |
| `section`, `file_title`, `relation`, `study_type`, `study_quality` | present | absent |

Both `ConfidenceBand` and `EvidenceStatus` are independently redefined identically in
both places (harmless duplication, but exactly the kind of drift `idd.ts` is meant to
prevent going forward).

**I am not resolving this by picking one shape.** It's plausible the live backend
response really does return `page`/`section`/`relation`/`study_type`/`study_quality`
(i.e., `EvidenceObjectDTO` reflects reality and IDD-0004 §3 hasn't caught up), or that
the IDD is the target shape and the frontend type is reading a subset. Either way this
needs Developer A / Architect input, not a frontend guess — recorded as a question in
[10-Risks-And-Questions.md](10-Risks-And-Questions.md) and
[docs/contracts/frontend-feedback.md](../contracts/frontend-feedback.md).

## Other type-plan notes

- `features/pipeline/types.ts` already follows the exact discipline this plan wants
  everywhere: an explicit "mirror backend contracts, do not invent fields" comment,
  with pointers to the actual backend source (`routes.py`,
  `models.AnalysisResult.to_api_dict()`). Use it as the house style for any new
  feature-local contract-mirroring type file.
- IDD-0004 §4's query-key list (`["me"]`, `["projects"]`, `["evidence", projectId, filters]`,
  etc.) is a **naming convention**, not identical to the existing
  `frontend/src/lib/queryKeys.ts` factory functions today (that file uses named
  factory functions, e.g. `queryKeys.evidence(projectId, filters)`, rather than
  inline array literals — a stylistic difference, not a contract violation, since the
  actual key *values* produced need to match, not the code shape used to produce
  them). Worth a direct diff of produced key arrays before assuming alignment —
  not done in this pass.
- `Paper.file_id` in IDD-0004 §3 is marked `@deprecated` in favor of `id`/paper
  semantics, consistent with IDD-0003 §1.1's "accept both `paper_id` and `file_id`"
  transition rule noted in [06-API-Contract-Review.md](06-API-Contract-Review.md).
  Any new code consuming `Paper` should prefer `id` and treat `file_id` as legacy.

## Explicitly not doing

- Not generating types from OpenAPI/codegen — no OpenAPI spec exists yet (IDD-0004 §3
  says "hand-maintained **or** generated from OpenAPI"; today there's nothing to
  generate from).
- Not touching `frontend/src/types/api.ts`'s existing 556 lines — it's serving
  working features today and isn't in scope for this pass.
