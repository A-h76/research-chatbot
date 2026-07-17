# Architecture Audit — Reuse Map & Refactoring Plan

Governed by [`00-constitution.md`](./00-constitution.md) — every REWRITE
verdict below requires an ADR before it's actioned (Principle 1); every
KEEP/EXTRACT verdict is a vote for composition over replacement
(Principle 2). This audit produces the evidence; it doesn't pre-approve
the rewrites it names.

Scanned directly — line counts, route counts, and every specific
file:line reference below were run against the actual repository, not
estimated.

---

## 1. Repository scan

```
server.py           5,445 lines   21 SQLAlchemy models, 70 Flask routes — one file
worker.py             240 lines   queue worker (Postgres FOR UPDATE SKIP LOCKED)
storage/             ~450 lines   6 files — provider interface, R2/Local, checksum, GC, self-test
imports/             ~350 lines   9 files — Importer registry, 7 format importers, self-test
migrations/            9 files    numbered .sql, Postgres-only
run_migrations.py      24 lines   migration runner
backfill.py           220 lines   one-time seed/backfill script
frontend/             React + TypeScript SPA — not modified by any backend task so far
docs/                 11 architecture docs + this audit + 1 ADR
```

Test coverage: **2 files** (`storage/test_storage.py`,
`imports/test_imports.py`, 12 self-checks total) — `server.py`, the
5,445-line file holding all 21 models and 70 routes, has zero direct
unit tests. Every verification of `server.py`'s behavior so far has been
an ad-hoc script run once against real infrastructure, not a committed,
repeatable test.

---

## 2. Reusable modules — what's already good, and why

| Module | Why it's reusable as-is |
|---|---|
| `storage/` | Already a bounded context per Constitution Principle 3 — nothing imports it into `server.py`'s internals, it's consumed through 4 functions (`upload`, `delete`, `presigned_url`, `local_copy`) plus the newer `storage_manager` surface. Swapping R2 for another S3-compatible provider is a new `StorageProvider` implementation, not a `server.py` edit. |
| `imports/` | Same shape — `extract_text(path, mime, name) -> str` is the entire public contract. Adding a format is a new `Importer` class, zero changes to callers. |
| `worker.py`'s `HANDLERS` dispatch table | New job types register a handler function; nothing about the poll/claim/retry loop changes. Extension over replacement, already working as intended. |
| `_process_document`'s `job_id`/`on_processed` parameters | The exact mechanism that let the queue worker reuse extraction logic without duplicating it — a real example of Principle 2 already applied under pressure (two very different callers, one implementation). |
| Auth (`login_required`, Google OAuth via authlib) | Small, self-contained, no changes needed by anything in this audit. |
| `EmailService` | Provider-agnostic already (swap by env var, not by call site) — matches Principle 9's dependency-inversion goal, just for a smaller dependency than storage/queue/LLM. |

---

## 3. Technical debt catalog

Each item below is something found in the code, not inferred — file and
line given so it can be checked directly.

### 3.1 Structural

- **`server.py` is a single 5,445-line file holding all 21 models and
  all 70 routes.** No domain boundaries exist in the code's actual
  structure — only in documentation (`upload-architecture.md`,
  `research-intelligence.md`, etc.) that describes boundaries the code
  doesn't yet have. This is the literal "monolithic block" the audit
  brief asks to catalog.
- **The dual upload path is now architecturally inconsistent, not just
  duplicated.** `upload_file()` (`server.py:1865`) uses the
  transactional-outbox/queue pattern — validate, persist, enqueue,
  return. `confirm_upload()` (`server.py:2206`) still calls
  `_process_document()` inline, synchronously, in the request thread —
  the exact pattern `upload_file()` was rewritten specifically to stop
  doing. Two upload entry points now have materially different
  reliability and latency characteristics for what a user experiences as
  "the same feature."
- **`worker.py` imports `server`'s private (underscore-prefixed)
  functions directly** (`_process_document`, `_apply_metadata`,
  `_run_paper_analysis`, `_enqueue_job`, `_sha256`) — there is no public
  interface between "the queue worker" and "the business logic it
  runs," just a Python module boundary that happens to also expose
  internals. Extracting either side later means first drawing that
  interface, which doesn't exist today.

### 3.2 Error handling

- **30 bare/broad `except Exception:` blocks in `server.py`.** Several
  are deliberate and documented (e.g. `_log_ai_usage`'s "never let
  cost-tracking break the AI call it's tracking") — but the count alone
  means most exceptions in this codebase are handled by the same blunt
  pattern regardless of whether the failure is expected (a malformed
  upload) or a genuine bug (a typo in a variable name), and both get
  logged and swallowed identically.

### 3.3 Security / config (previously identified in `production-hardening.md`, still open)

- **`FLASK_SECRET_KEY` still silently falls back to
  `os.urandom(32).hex()`** (`server.py:78`) — confirmed still present.
  Every process restart in production without this env var set still
  mass-invalidates every session and every outstanding local-provider
  signed URL, silently.
- **No rate limit on `/api/files` POST, `/api/uploads/presign`, or
  `/api/chat`** — confirmed still absent (checked directly; only 7
  routes carry `@limiter.limit`, none of these three). The most
  expensive-per-call route in the app and every upload entry point are
  still unlimited.
- **No MIME/content verification anywhere** — confirmed `python-magic`
  is in neither `server.py` nor `requirements.txt`. File type is still
  entirely client-asserted.

Three items, found once, flagged once, still true five tasks later —
worth naming as a pattern, not just three isolated facts: designed fixes
that don't get scheduled as their own task tend not to happen.

### 3.4 Testing

- **`server.py` has no unit tests.** Every one of its 5,445 lines has
  only ever been exercised by one-off verification scripts run during
  this project's own tasks — real and thorough at the time, but none of
  them are committed, so none of them run again on the next change.
- **No integration test suite** — `shipping-plan.md` §2 already named
  this and proposed formalizing the ad-hoc scripts into
  `tests/integration/`; that hasn't happened yet either.

### 3.5 Incomplete adoption of already-built patterns

- **AI cost logging covers 3 of 7 `responses_text()` call sites**
  (embedding, metadata, analysis) — chat, memory extraction, title
  generation, compare, and gap-finder still don't log usage, a gap
  `research-intelligence.md` and the Task 6 summary both already named.
- **`PaperAnalysis`/`DerivedAnalysis` don't store `prompt_version_id` or
  `pipeline_hash`** — Constitution Principle 5 names this directly; it's
  the same cache-correctness gap `research-intelligence.md` §6
  identified before the constitution existed.
- **Dependency inversion is real for storage, absent for the queue and
  the LLM client** — Constitution Principle 9's table, confirmed again
  here by the same evidence: `worker.py` calls Postgres-specific
  `with_for_update(skip_locked=True)` directly, and `client =
  OpenAI(...)` is constructed once at module load with no interface
  around it.

---

## 4. Target architecture — modular monolith, four domains

Still one deployable process (Constitution Principle 3 doesn't require
microservices, only that a bounded context *could* be extracted without
a rewrite) — but `server.py`'s 21 models and 70 routes sorted into four
packages by what they actually do, not by which milestone added them:

```
ingestion/    upload_file, confirm_upload, presign/multipart/confirm routes,
              UploadBatch, UploadJob, UploadSession, ImportSession, OutboxEvent,
              imports/ (already correctly shaped), worker.py's import/
              extract_metadata/paper_analysis handlers

storage/      already exists, already correctly shaped — StorageUsage
              model moves here from server.py's model list

ai/           responses_text, embed_texts, chunk_text/chunk_document,
              _extract_meta_from_text, _run_paper_analysis,
              _run_comparison, _run_gap_finder, all prompt constants,
              ModelVersion, AIUsageLedger, PromptVersion (not yet a
              Python model — only migrated), the OpenAI client itself
              behind a new LLMProvider interface (closes the Principle 9 gap)

workspace/    User, Project, Conversation, Message, Memory, Citation,
              Note, SearchIndex, SupportRequest — chat routes, search,
              dashboard, settings, auth, export
```

`ingestion` and `ai` are the two domains today's `server.py` most
tangles together — `_process_document` (ingestion's job) directly calls
`chunk_document`/`embed_texts` (ai's job) in the same function. Drawing
the line between them is most of what makes this refactor worth doing:
once `ingestion` only knows "call the `ai` interface with text, get
chunks back," swapping the embedding provider or the chunking strategy
touches one package, not a scan of `server.py` for every call site.

---

## 5. Reuse Map

| Component | Verdict | Reason |
|---|---|---|
| `storage/` package | **KEEP** | Already the target shape — bounded, tested, provider-swappable. No work needed beyond moving `StorageUsage` in from `server.py`. |
| `imports/` package | **KEEP** | Same — already the target shape for `ingestion`'s format-handling slice. |
| `worker.py`'s poll/claim/retry loop | **KEEP (minor refactor)** | Logic is sound and verified; needs to import from the new `ingestion`/`ai` packages' public interfaces instead of `server`'s private functions once those packages exist — an interface-drawing exercise, not new logic. |
| `_process_document`'s `job_id`/`on_processed` extension pattern | **KEEP** | Directly cited in §2 as the model to repeat, not change. |
| `confirm_upload()`'s inline processing tail | **REWRITE — reason: architectural inconsistency** | Should call the queue the same way `upload_file()` does, per §3.1. Requires an ADR per Constitution Principle 1 before touching it — this is flagged, not actioned. |
| `ensure_columns()`'s ALTER-and-swallow migration pattern | **RETIRE for Postgres, KEEP for SQLite dev** | Formal numbered migrations (`migrations/*.sql`) now cover Postgres; `ensure_columns()` still owns the SQLite dev fallback that has no migration alternative. Retiring it outright would break local dev — a partial retirement, not a full one. |
| `server.py`'s 21 models, in place | **EXTRACT (phased)** | Into `ingestion/models.py`, `storage/models.py`, `ai/models.py`, `workspace/models.py` per §4 — mechanical moves, not rewrites, since SQLAlchemy models don't need their field definitions to change to change which file they live in. |
| `server.py`'s 70 routes, in place | **EXTRACT (phased)** | Into Flask blueprints per domain, same reasoning — a route's body doesn't need to change to move into a blueprint. |
| OpenAI client construction | **EXTRACT into an `LLMProvider` interface** | Closes the Constitution Principle 9 gap directly; today's direct `client.responses.create(...)` calls become one interface implementation, opening the door to a second provider without touching every call site. |
| Queue backend (`worker.py`'s Postgres implementation) | **KEEP — pending ADR-0001** | Already opened in the constitution; this audit doesn't re-litigate it, just confirms the code inventory ADR-0001 is deciding about. |
| The 4 unaddressed items from §3.3 (secret fallback, rate limits, MIME check) | **Not a reuse-map item — a scheduling problem** | Nothing to keep/rewrite/retire/extract; these are undone work that needs to be a task, not rediscovered a third time. |

No component in this codebase warrants a full **REWRITE** in the
"scrap and rebuild" sense, and none warrant **EXTRACT into a separate
service** yet — every EXTRACT verdict above is "into a package within
the same deployable," matching Constitution Principle 3's modular-monolith
default. That's a real finding, not a hedge: this codebase's actual
problem is organization, not correctness — nothing audited here is wrong
enough to justify Principle 1's rewrite bar.

---

## 6. Phased refactoring plan

Each phase leaves `server.py` fully bootable and every route serving —
Constitution Principle 8 (functional after every milestone) applies to
this plan as much as to any other.

1. **Close the three named-and-reopened gaps (§3.3)** — `FLASK_SECRET_KEY`
   startup guard, rate limits on the three unlimited routes, MIME
   verification. Independent of everything else in this plan, smallest
   possible diffs, already fully designed in `production-hardening.md`.
2. **Draw the `ai/` package boundary first**, not `ingestion/` — because
   `ingestion` depends on `ai` (chunking/embedding) but not the reverse,
   extracting the dependency first means `ingestion`'s later extraction
   has a real interface to call instead of reaching back into `server.py`.
   Move: prompt constants, `responses_text`, `embed_texts`,
   `chunk_text`/`chunk_document`, the three `_run_*`/`_extract_meta_*`
   functions, `ModelVersion`, `AIUsageLedger`. Introduce the
   `LLMProvider` interface here, closing the Principle 9 gap in the same
   pass rather than as separate work.
3. **Draw `storage/` in fully** — mechanical, since the package is
   already correctly shaped; just move `StorageUsage` and update
   `server.py`'s imports.
4. **Draw `ingestion/`** — now calls `ai/`'s interface instead of
   inline chunk/embed calls. This is also the natural point to open the
   `confirm_upload()` ADR from the Reuse Map, since unifying it with
   `upload_file()`'s queue pattern is far more contained once both live
   in the same package.
5. **`workspace/` absorbs whatever's left** — by construction, not by
   design; if this phase reveals workspace itself needs sub-boundaries
   (chat vs. citations vs. projects), that's the next audit's finding,
   not a problem to pre-solve here.
6. **Backfill unit tests alongside each extraction**, not after — a
   package that gets its own file is also a package that can finally get
   `pytest`-style tests without importing all of `server.py`'s Flask app
   setup to test one function. `storage/` and `imports/` already prove
   this works; `ai/` and `ingestion/` should follow the same pattern
   from the moment they're extracted, not as a later cleanup pass.
