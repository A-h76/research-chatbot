# 10 — Risks and Questions

**Status:** Draft for review · For Developer A / Architect. Nothing here has been
resolved unilaterally — where a question implies a contract question, it's mirrored
in [docs/contracts/frontend-feedback.md](../contracts/frontend-feedback.md).

## Contract questions (need Developer A / Architect answer)

1. **Writing document autosave** — is `PATCH /api/writing/documents/{id}` (per
   IDD-0003 line 314, with `autosave_key` conflict guard) or
   `POST /api/writing/documents/{id}/autosave` (per the live frontend, with
   `current_version`/`idempotency_key`) the actual/intended endpoint? See
   [06-API-Contract-Review.md](06-API-Contract-Review.md) item 1.
2. **Writing document export route** — does `POST /api/writing/documents/{id}/export`
   (IDD-0003 line 385) exist on the backend yet, or should the IDD instead document
   the live `/api/export/{notes,analysis,chat}` routes as the frozen v1 contract?
   See [06-API-Contract-Review.md](06-API-Contract-Review.md) item 2.
3. **`EvidenceObjectDTO` vs. IDD-0004 `EvidenceObject`** — which fields are actually
   returned by the live `/api/evidence/*` endpoints today: `page` (single) or
   `page_start`/`page_end` (range)? `study_type`/`study_quality`/`relation`/`section`
   or `evidence_type`/`finding`/`pipeline_version`/`content_hash`? Both can't be
   exactly right if `idd.ts` is meant to be the frozen mirror. See
   [07-TypeScript-Type-Plan.md](07-TypeScript-Type-Plan.md).
4. **`file_id`/`paper_id` dual-acceptance rule (IDD-0003 §1.1, rule 6)** — is this
   already true of every live response, or only intended going forward? Affects
   whether `idd.ts` types should mark both fields optional-but-required-one-of, or
   just `file_id` deprecated as currently written.
5. **`GET /api/writing/documents/{id}` and `DELETE /api/evidence-bindings/{id}`** —
   do these exist on the backend? No frontend caller was found for either; unclear
   whether that's a frontend gap or these routes aren't implemented yet.

## Process questions (need Architect / both developers)

6. **EPIC-0001 sign-off status** — its own status field says "In progress (docs
   exist; review pending)." Per `docs/epics/README.md`'s own rule, EPIC-0002 onward
   (and by extension most of Sprint 1 in
   [05-Frontend-Roadmap.md](05-Frontend-Roadmap.md)) shouldn't start until this
   exits. Who owns closing it out, and is there a target date?
7. **Two non-superseding API-contract documents coexist**: `docs/api-contract.md`
   (older, CRUD/chat-era, doesn't mention Evidence/Writing/RI at all) and
   `docs/idd/IDD-0003-API-Contracts.md` (new, broader). Should the older document be
   marked superseded/archived, or does it remain the reference for the routes it
   already covers (files/projects/citations/notes/conversations/memories/chat) while
   IDD-0003 only adds the newer surface? Affects which document Developer B should
   treat as authoritative when they overlap.
8. **`docs/processing-pipeline-architecture.md`'s Celery proposal was reversed by
   ADR-0001** (which keeps the Postgres worker) but the original document itself
   isn't marked superseded. Not a frontend concern directly, but flagged since a
   future reader could be misled — recorded here rather than silently ignored.

## Frontend-internal open questions (no backend dependency, but worth deciding before Sprint 1)

9. **Component-test environment convention.** `vite.config.ts`'s inline Vitest config
   uses `environment: "node"` with a comment that this suffices because tests target
   "plain fetch-wrapping functions, not React components" — but 7 existing `.tsx`
   test files exist (`AiSections`, `AnalysisOutput`, `DomainSelector`,
   `MetadataInput`, `PaperRelatedTab`, `PaperOverviewPage`, `LibraryUploadZone`) and
   `@testing-library/react`/`jsdom` are dependencies. Is there a per-file environment
   override convention already in use, or should `chat/` test coverage (currently
   zero — see [01-Frontend-Architecture-Review.md](01-Frontend-Architecture-Review.md))
   follow a documented pattern rather than each new test file guessing?
10. **Shared `Panel` primitive** — is extracting one from the 6 `Project*Panel` +
    5 other Panel components (see [03-Component-Inventory.md](03-Component-Inventory.md))
    worth doing before EPIC-0002/0004 add more panels, or is the current
    per-feature-independent pattern intentional and should stay that way? Low-risk
    either way, but worth an explicit decision rather than defaulting silently.
11. **`DESIGN-SYSTEM-v2.md` cross-read** — `frontend/src/index.css`'s `--primary`
    token comment references "DESIGN-SYSTEM-v2 §8" as the source of the teal-vs-violet
    brand decision. This review didn't fully cross-read `docs/DESIGN-SYSTEM-v2.md`
    against the live CSS token-by-token — worth doing before any future design-system
    change, to confirm the CSS hasn't drifted from that doc.

## Non-blocking observations (recorded, not action items)

- Root `README.md` describes an older, chat-first product framing with no mention of
  Evidence/RI/Writing — stale relative to the current product direction. Product
  documentation, not frontend architecture; noted, not owned by this workspace.
- `.cursor/mcp.json` contains what looks like a live API key for a Google "stitch"
  MCP endpoint, committed to an untracked-but-present file. Flagged as a factual
  observation from the review pass, not a frontend concern — worth someone checking
  whether that key should be rotated/removed before `.cursor/` is ever committed.
