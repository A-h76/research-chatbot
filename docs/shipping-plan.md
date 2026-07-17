# Shipping — Testing, Rollout & Release Strategy

Scope: how everything designed across this series (`upload-architecture.md`
through `upload-ux.md`) actually gets shipped — tested, rolled out, and
rolled back if it goes wrong. Design only, same format as the rest of the
series, but also the capstone: §11 sequences all nine prior docs into one
concrete order, and that order is **not** the order they were written in.

**Audit result, stated plainly**: unlike every other doc in this series,
there's almost nothing to reuse here. The entire repo has exactly one
test file (`storage/test_storage.py`, six self-checks, written during the
storage-implementation pass) and no CI pipeline at all — no
`.github/workflows`, no automated gate of any kind. Shipping today means
"run the server locally, `npm run build`, deploy." Right-sizing this
matters more than usual: a full enterprise SRE program (a chaos platform,
dedicated load-test clusters, multi-stage automated-canary rollout) would
be wildly disproportionate to a personal-scale app. Everything below is
scoped to what that scale actually needs.

---

## 1. Unit tests

`pytest`, not a hand-rolled framework — the existing
`storage/test_storage.py` self-checks (assert-based, no fixtures) already
follow the shape pytest wants; adopting it is closer to "add a config
file" than "rewrite the tests." Coverage priority, in order of what this
series flagged as highest-risk, not alphabetically by module:

1. Cache key correctness (`research-intelligence.md` §6) —
   `(content_hash, pipeline_version_id)` — the exact bug the series found
   (stale analyses never invalidating on a prompt change) is a one-line
   regression to reintroduce by accident; a unit test pins it down.
2. Step Runner checkpoint/resume logic (`processing-pipeline-architecture.md`
   §5, §10) — the retry-resumes-not-restarts guarantee is the entire
   point of checkpointing; untested, it's easy to silently break.
3. `_find_duplicate_file` and the OCR text-injection seam
   (`research-intelligence.md` §2) — both already exist in real code from
   this series' implementation passes.

---

## 2. Integration tests

The storage-implementation pass already did real integration
verification — presign → real PUT to R2 → confirm → dedup — but as
throwaway scratchpad scripts, not a committed suite. **Formalize those
scripts into `tests/integration/`**, run against a real (but disposable)
R2 test bucket and a scratch Postgres/SQLite DB, not mocks — this series
has already shown that mocked storage tests would have missed real
issues (the presigned-URL round trip, the actual R2 ETag format) a mock
can't reproduce. Run in CI (§9) on a schedule, not on every commit, since
they hit a real external service and cost real (small) money in API
calls.

---

## 3. Failure injection

Targeted, not a chaos-engineering platform: mock the OpenAI client and
`boto3` client at test time to simulate specific failure modes the Retry
Engine (`processing-pipeline-architecture.md` §6) is supposed to handle
— an OpenAI 429, a dropped R2 connection mid-multipart-upload, a
Postgres connection timeout — and assert the correct outcome
(`TransientProcessingError` retries with backoff;
`PermanentProcessingError` goes straight to the dead-letter queue,
§4 of that doc). The point isn't "does the system survive chaos," it's
"does this specific, designed error-handling path actually fire the way
it was designed to" — a handful of targeted tests, not a fault-injection
framework.

---

## 4. Load testing

Aimed at the bottlenecks this series **already identified**, not generic
broad load: `rag_retrieve`'s linear in-Python cosine scan
(`upload-architecture.md` §1.5), `list_files`'s in-Python
filter-then-slice (`api-contract.md` §5), and `embed_texts`'s batch-of-64
OpenAI calls under concurrent upload load. A lightweight open-source tool
(Locust — Python, matches the rest of the stack, free) pointed
specifically at those three, not a paid load-testing service and not an
attempt to simulate "production scale" for an app whose actual production
scale is a personal or small-team user base.

---

## 5. Rollback plan

Mostly already covered by decisions made earlier in this series, not new
design:

- **Code rollback**: revert the deploy (git). Safe by construction,
  because...
- **Schema rollback isn't needed for most of this series' migrations** —
  `database-design.md` §6's numbered SQL migrations are deliberately
  additive (new tables, new nullable columns), which is the exact same
  discipline `api-contract.md` §9 established for API versioning
  ("additive-only, never repurpose a field") applied to schema instead of
  routes. Old code ignoring a new nullable column or an unused new table
  is safe without a down-migration. This is one principle serving two
  different docs' concerns, not a coincidence.
- **The one place rollback genuinely needs a plan**: cutting over from
  `threading.Thread` to Celery (§11, Phase 3) — the feature flag in §6 is
  the rollback mechanism, not a code revert: flip it off, traffic goes
  back to the old path, no deploy needed. This is *why* that cutover
  ships behind a flag and the additive schema changes don't need one.

---

## 6. Feature flags

`database-design.md` §2.11 already designed `feature_flags` and
explicitly deferred building it until *"the first real flag is needed"*
— this series' own cutover (§11) is exactly that trigger. Build it now,
using the table already specified, applied specifically to:

- The Celery pipeline cutover (§11 Phase 3) — per-`job_type`, so `import`
  can move to Celery while `paper_analysis` still runs on the old thread
  path, independently.
- OCR / Research Insights (§11 Phase 4) — both introduce new AI spend;
  gate them so cost is opt-in per user before it's on for everyone.

`rollout_pct` (already in the schema) is what makes alpha/beta (§7, §8)
a flag setting, not a separate environment.

---

## 7. Alpha testing

Internal only — the existing `ALLOWED_EMAILS` whitelist already scopes
who can log in at all; alpha is the app owner (and anyone already on that
whitelist) with every new flag from §6 turned on. The specific things
that need real alpha exposure, because nothing but this series' own
throwaway scratchpad scripts has touched them yet: the presigned/
multipart upload flow end-to-end from the actual UI (not a test script),
the Celery pipeline under real usage, OCR against a real scanned PDF, and
the admin dashboard.

## 8. Beta testing

Same `ALLOWED_EMAILS` list, `rollout_pct` moved off 0% for a subset —
no separate beta environment or deploy, the flag setting *is* the beta
ring. Graduation criterion: the DevOps dashboards from
`devops-observability.md` §9 stay clean (error rate, AI cost, queue
depth) for the beta group over a defined window before widening.

## 9. Production rollout

`rollout_pct → 100%`, watched live against the same dashboards, not a
separate rollout-specific monitoring setup. A minimal CI gate — GitHub
Actions running `pytest` (§1) and the storage integration suite (§2) on
every push — is worth having before this point specifically because nothing
gates a deploy today; it doesn't need to be elaborate, just present.

---

## 10. Why sequencing matters here specifically

The nine prior docs were written in an order that made sense for
*designing* each layer on top of the last (audit → schema → storage →
pipeline → content → ops → hardening → contract → UX). That is **not**
the order they should *ship* in — some of that work is zero-risk and
should go out immediately regardless of anything else being ready;
some of it is high-risk and needs the observability from a
later-written doc in place *before* it ships, not after.

---

## 11. The actual ship order

| Phase | What ships | Why here |
|---|---|---|
| **0 — now, independent** | `production-hardening.md` §8's `FLASK_SECRET_KEY` fix; §5's rate limits on `/api/chat` and upload routes; `api-contract.md` §5's `list_conversations` pagination fix | Zero dependencies, all three are bug fixes already found by this series' audits, not new features — no reason to wait on anything else |
| **1 — foundation** | `database-design.md`'s additive migrations; `devops-observability.md`'s metrics/logging/correlation IDs | Observability ships **before** the risky cutover it exists to watch, not after — sequencing this after Phase 3 (its doc-writing position) would mean flying blind during the highest-risk change |
| **2 — already shipped** | `docs/upload-architecture.md`'s Storage Manager — implemented and verified live against real R2 in this series already (presign, confirm, dedup, GC, reconciliation all passing) | Not a plan, a fact — noted here so §11 isn't mistaken for "nothing exists yet" |
| **3 — flag-gated cutover** | `processing-pipeline-architecture.md`'s Celery pipeline, per-`job_type`, old `threading.Thread` kept live as fallback | Highest-risk change in the series; feature-flagged per §6, rollback is a flag flip (§5), not a deploy |
| **4 — cost-watched content features** | `research-intelligence.md`'s OCR and Research Insights | Both add new AI spend; gated behind a flag, watched specifically via the AI Cost Ledger dashboard from Phase 1 — Auto Notes/Reading Summary ship anytime, they cost nothing new |
| **5 — hardening completion** | `production-hardening.md`'s virus scanning, MIME verification, quotas | No hard dependency on anything; bundled here because the new upload paths from Phase 3 are the highest-value place to apply them, not because they're blocked until then |
| **6 — frontend** | `upload-ux.md`'s Upload Manager UI and the pages built on it | Needs Phase 2 (already true) for presign/confirm wiring and Phase 3 at least partially live for Progress/Queue/ETA to have real data to render |
| **7 — ongoing** | `api-contract.md`'s Pydantic request models, versioning discipline | Additive, incremental, no single cutover moment — applied to new routes as they're written, not a migration project |

Same close as the rest of the series: design only — say the word for the
implementation pass.
