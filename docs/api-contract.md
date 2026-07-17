# API Contract — Architecture

Scope: formalizing the HTTP surface across everything designed so far.
Design only, same format as the rest of the series.

**The throughline, and it's better news than the other docs**: re-auditing
the actual 50+ routes in `server.py` found the API is already
~80% consistent — a real serializer convention, a real error shape, a
real pagination envelope, a real SSE contract, and a **clean 27-for-27
record on ownership checks**. The work here is formalizing what's already
right, fixing the one inconsistency that audit found, and closing two
real gaps (request validation, a versioning discipline) — not inventing
a contract from nothing.

---

## 1. REST APIs

The surface is a **deliberate hybrid**, and that's correct, not
accidental-and-in-need-of-fixing: `/api/files`, `/api/projects`,
`/api/citations`, `/api/notes`, `/api/conversations`, `/api/memories` all
follow plain resource CRUD (`GET` list, `POST` create, `GET
/<id>`, `PATCH`, `DELETE`). Alongside them, action-shaped routes —
`/api/uploads/presign`, `/api/analysis/compare`, `/api/chat` — exist
because "compare these papers" or "stream a chat reply" isn't a resource
you CRUD, it's a verb. Forcing every operation into a resource noun would
produce worse routes than the ones already there
(`POST /api/comparisons` with the comparison's actual behavior hidden
behind generic CRUD semantics is a worse API than a route named for what
it does). The fix is documenting this as the house convention, not
picking one style and forcing the other's routes to conform.

---

## 2. Request models — real gap

Every route parses input by hand: `request.get_json(force=True,
silent=True) or {}` followed by `.get(...)` calls, or
`request.form.get("project_id", type=int)`. No schema library, no
validation layer — confirmed nowhere in `requirements.txt`. Errors from
malformed input are whatever exception happens to surface, not a
consistent `400` with a useful message.

**Fix: Pydantic request models** — one of the few places in this whole
series where adding a new dependency is the right call rather than
reuse-first, because hand-rolling type coercion + validation + error
messages for 50+ routes is genuinely more code than one well-established
library that already does exactly this:

```python
class PresignUploadRequest(BaseModel):
    filename: str
    mime: str = "application/octet-stream"
    size: PositiveInt
    checksum_sha256: str | None = None
    project_id: int | None = None
    conversation_id: int | None = None
```

**Scope this as additive, not a rewrite**: apply to new routes going
forward (the presign/confirm routes from the storage pass, anything from
the pipeline/research-intelligence docs once built) and retrofit existing
routes opportunistically — not a big-bang rewrite of 50 working routes,
matching how every other doc in this series has introduced change.

---

## 3. Response models — mostly already exists

The `_file_to_dict` / `_citation_to_dict` / `_analysis_to_dict` /
`_derived_to_dict` / `_note_to_dict` convention **is** a response-model
layer already — just as plain functions instead of a schema class. Wrap
these in the same Pydantic models from §2 (dual-purpose: one library,
request and response both) for two concrete benefits, not for their own
sake:

1. **OpenAPI generation** — a documented schema instead of reading route
   source to know a response shape.
2. **Frontend type drift becomes a build-time error, not a runtime
   surprise** — `frontend/src/types/api.ts` today hand-mirrors these
   dicts by convention with no enforcement that they stay in sync; a
   generated OpenAPI schema paired with `openapi-typescript` removes the
   manual-sync step entirely. Noted as a follow-on this unlocks, not a
   requirement of this phase.

---

## 4. Error codes — already a consistent convention, formalize it

Every error response already follows one shape:
`{"error": "<snake_case_code>"[, "detail": "<human string>"]}` with an
appropriate status — `no_file`/400, `not_found`/404,
`storage_unavailable`/502, `csrf_origin_mismatch`/403,
`not_authenticated`/401, and so on, consistently across dozens of routes.

**Formalize, don't replace**: one helper function removes the last bit of
repetition —

```python
def api_error(code: str, detail: str | None = None, status: int = 400):
    body = {"error": code}
    if detail:
        body["detail"] = detail
    return jsonify(body), status
```

— and a single markdown table cataloguing every code in use today
becomes the reference for what a client should switch on, instead of
grepping route source for `"error":` literals.

---

## 5. Pagination — one real inconsistency found

`list_files` already does this well:
`{"total": n, "offset": o, "limit": l, "items": [...]}`, bounds-checked
(`limit` capped at 500). **`list_conversations` returns a bare, unbounded
JSON array** — no envelope, no limit, fetches every conversation the user
has ever had on every call. Two list endpoints, two different response
shapes. Fix: apply the same envelope to `list_conversations` (and confirm
`list_notes`/`list_citations` match it too) rather than inventing a
second pagination style.

Worth flagging alongside the fix, not as a blocker to it:
`list_files`' pagination slices an **in-memory Python list** after
loading every matching row, not a SQL `LIMIT`/`OFFSET` — the same
"compute in Python instead of pushing to SQL" shape
`upload-architecture.md` §1.5 already flagged in `rag_retrieve`. Fine at
personal-library scale, a real ceiling if a library ever grows past a
few thousand files — same recurring theme across this whole audit
series, not a new finding.

---

## 6. Polling — already a good pattern, needs one documented contract

`meta_status` / `PaperAnalysis.status` / `DerivedAnalysis` are already
polled from the frontend via `refetchInterval`, each hook inventing its
own interval independently. Formalize as one contract instead of N ad-hoc
ones:

- Every pollable resource exposes `{"status": "pending"|"running"|
  "done"|"failed", "updated_at": <ISO timestamp>}` — already true of
  every status field in the schema, just not documented as a shared rule.
- **One recommended client policy**: poll every 3s while
  `status in (pending, running)`, stop entirely once `done`/`failed` —
  replacing each hook's own guess with one documented number.
- Once the Celery/`UploadJob` system (`processing-pipeline-architecture.md`)
  ships, `database-design.md` §5's `job:{id}:status` Redis cache becomes
  the fast read path behind this same contract — the contract doesn't
  change, only what serves it gets faster.

---

## 7. SSE-ready payloads — already implemented, formalize + extend

`/api/chat` already streams real Server-Sent Events via a two-line
helper (`sse(event, data)` → `f"event: {event}\ndata:
{json.dumps(data)}\n\n"`), with exactly four event types in production
use today: `status`, `delta`, `done`, `error`. This is already a clean,
minimal contract — document it as the house SSE shape rather than
inventing a new one per feature:

```
event: status   {"text": "Reading your documents…"}
event: delta    {"text": "<token>"}
event: done     {...final message payload...}
event: error    {"text": "<error message>"}
```

**Extension, not a new mechanism**: a long-running Step Runner job (the
pipeline doc's checkpoint writes) can push over this exact same
`status`/`done`/`error` shape as an alternative to polling — the same
checkpoint data that already updates `UploadJob.checkpoint` for polling
(§6) is also what an SSE subscriber would receive, just pushed instead of
pulled. One data shape, two delivery mechanisms, not two contracts.

---

## 8. Ownership checks — audited, zero gaps found

Every one of the 27 routes taking an `<int:id>` path parameter was
checked. **All 27 enforce ownership** — no missing check found. Two
valid styles are both in use, though:

- **Fetch, then compare** (24 routes): `if not x or x.user_id !=
  session["user_id"]: return 404`.
- **Filter in the query itself** (`export_chat`, and a few others):
  `.where(Conversation.id == cid, Conversation.user_id == uid)`.

The second style is structurally safer — it's not possible to forget the
check because it's part of the query, not a separate `if` a future edit
could drop. **Recommend it as the house style for new routes** going
forward; the 24 existing fetch-then-compare routes are correct as-is and
don't need rewriting just to change style.

---

## 9. Versioning

No versioning scheme exists today (no `/v1/` prefix anywhere) — and full
URL versioning would be solving a problem this app doesn't have yet: one
consumer (its own frontend), always built and deployed together, never
independently out of sync with the API it calls.

**Recommendation: discipline over infrastructure.**

- Keep unprefixed `/api/...` — no `/v1/` prefix until there's a second,
  independently-evolving consumer to actually version *for*.
- Default to **additive-only** changes: new optional request fields, new
  response fields, new endpoints — never repurpose an existing field's
  meaning or remove one a client might read.
- Reserve a real `/api/v2/` prefix for the rare genuine breaking change,
  not routine growth.
- One `GET /api/version` route returning `{"version": "<date or
  semver>"}` — trivial, and gives any future third-party integration (or
  a deploy-skew check) something to read, without committing to a
  versioning scheme before there's a reason to.

---

## 10. Summary

| Already right — formalize, don't rebuild | Real gap — new work | Real gap — fix found by audit |
|---|---|---|
| REST/RPC hybrid (§1) | Request validation via Pydantic (§2) | `list_conversations` missing pagination envelope (§5) |
| `_x_to_dict` response shape (§3) | Versioning discipline (§9) | — |
| `{error, detail}` error shape (§4) | | |
| SSE contract at `/api/chat` (§7) | | |
| Ownership checks — 27/27 correct (§8) | | |

Same close as the rest of the series: design only — say the word for the
implementation pass.
