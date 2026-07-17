# Testing Guide — Storage/Queue/Worker Changes

Covers everything built across the storage foundation, Import Engine,
presigned uploads, transactional outbox, queue worker, and Redis/AI-ledger
passes. Organized in tiers — start at Tier 1, only go further if you need to.

---

## Tier 1 — Self-checks (30 seconds, no setup)

No database, no network, no Docker. Run these first — if either fails,
nothing downstream will work either.

```bash
cd "d:/chatbot (v1)"
python -m storage.test_storage      # 6 tests — providers, checksums, GC, reconcile
python -m imports.test_imports      # 6 tests — registry priority, zip recursion, notes
```

Expect `N passed` from both. These need no `.env` values at all.

---

## Tier 2 — The app as it runs today (SQLite, no worker)

This is "does the app still work" — the same thing `python server.py` has
always done. The transactional-outbox change means uploads now queue
instead of processing inline, so **expect files to sit at `pending`
forever in this tier** — there's no worker running yet (worker.py requires
Postgres, Tier 3 below). That's expected, not broken.

```bash
python server.py
# open http://localhost:5000, log in, upload a file
```

Check:
- Upload succeeds, response has a `job_id`.
- `GET /api/jobs/<job_id>/status` returns `{"status": "pending", ...}` —
  and stays `pending` (no worker to pick it up in this tier).
- The Knowledge Library page still loads, existing chats still work —
  confirms nothing outside the upload path regressed.

---

## Tier 3 — The full pipeline (Postgres + worker.py + Redis)

This is the real test — everything built across the last six tasks working
together: presigned/direct upload → transactional outbox → queue worker →
metadata/analysis chaining → Redis status cache → AI cost ledger.

### 3.1 One-time environment setup

**Postgres** (worker.py's `FOR UPDATE SKIP LOCKED` does not exist in
SQLite — it will refuse to start against it):

```bash
# using the Postgres already on this machine
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -p 5432 -d postgres -c "CREATE DATABASE personalai_test;"
```

(No local Postgres? `docker run -d --name pg-test -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:16` works identically.)

**Redis** (optional — status caching, everything degrades gracefully
without it):

```bash
docker run -d --name redis-test -p 6379:6379 redis:7-alpine
```

**Point the app at both**, either by editing `.env` or exporting for the
session:

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/personalai_test"
export REDIS_URL="redis://localhost:6379/0"
```

### 3.2 Bootstrap the schema — order matters

`run_migrations.py`'s files assume `users`/`projects`/`conversations`/
`files` already exist (they FK into them) — those four are created by
`server.py`'s own model definitions, not by any migration. Boot order:

```bash
# 1. Start the app once against the fresh DB — creates users/projects/
#    conversations/files/chunks/etc. AND (today) the newer tables too,
#    via the simpler create_all()-derived schema.
python server.py &
sleep 2 && kill %1        # just needed it to boot once and create tables

# 2. Now layer the formal migrations on top. Tables create_all() already
#    made will make 0001-0009 fail with "relation already exists" if you
#    run this against the SAME already-booted DB — this is a real,
#    known gap (see docs/testing-guide.md's "Known gaps" section below).
#    For a genuinely fresh DB, migrations must run BEFORE the app's
#    first boot, which then needs users/projects/conversations/files
#    pre-created some other way. Simplest reliable path for testing:
python run_migrations.py    # against a DB where only the 4 core tables exist
python backfill.py
```

If you hit `relation "users" does not exist` — that confirms you're
running migrations before the core tables exist; if you hit `relation
"upload_jobs" already exists` — that confirms `server.py` booted first
and already created it. Only one of the two orderings works today; see
"Known gaps" below for why.

Verify the bootstrap:

```bash
psql -U postgres -d personalai_test -c "SELECT filename FROM schema_migrations ORDER BY filename;"
# expect all 9: 0001_... through 0009_...

psql -U postgres -d personalai_test -c "SELECT name, version, is_active FROM prompt_versions;"
psql -U postgres -d personalai_test -c "SELECT logical_name, provider_model_id, is_active FROM model_versions;"
# expect 5 prompt rows, 3 model rows, all is_active = true
```

### 3.3 Start the app and the worker (two terminals)

```bash
# terminal 1
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/personalai_test"
python server.py

# terminal 2
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/personalai_test"
export REDIS_URL="redis://localhost:6379/0"
python worker.py
```

`worker.py`'s log should show `worker starting — poll every 2s, batch
size 10, max attempts 5` and then sit idle (nothing queued yet).

### 3.4 Upload a real file and watch it move through the pipeline

Open http://localhost:5000, log in, upload a PDF (or any document).

In **terminal 2** (the worker), you should see, within a few seconds:

```
job N (import) done
job N+1 (extract_metadata) done
job N+2 (paper_analysis) done
```

Check the database directly:

```bash
psql -U postgres -d personalai_test -c "
SELECT job_type, status, attempts FROM upload_jobs ORDER BY id DESC LIMIT 5;"
# expect three rows: import/extract_metadata/paper_analysis, all 'done'

psql -U postgres -d personalai_test -c "
SELECT status, dispatched_at IS NOT NULL AS dispatched FROM outbox_events ORDER BY id DESC LIMIT 5;"
# expect status='dispatched' on all three

psql -U postgres -d personalai_test -c "
SELECT kind, prompt_tokens, completion_tokens, cost_usd FROM ai_usage_ledger ORDER BY id DESC LIMIT 5;"
# expect embedding / metadata / analysis rows with real (non-zero) token counts
```

In the UI: the uploaded file's title/authors should populate (from
`extract_metadata`) and its Paper Analysis tab should fill in (from
`paper_analysis`) within roughly 10-20 seconds of the upload.

### 3.5 Status polling + Redis cache

```bash
# replace 7 with a real job id from step 3.4
curl -s http://localhost:5000/api/jobs/7/status   # (needs your session cookie — easier to check via browser devtools Network tab while the page polls)
```

Or check Redis directly:

```bash
docker exec redis-test redis-cli HGETALL job:7:status
# expect: status, progress, updated_at, user_id fields, matching Postgres
docker exec redis-test redis-cli TTL job:7:status
# expect a number close to 3600 (1 hour), counting down
```

### 3.6 Retry / backoff / dead-letter (optional, deliberately break something)

To see the retry path without waiting for a real failure:

```bash
psql -U postgres -d personalai_test -c "
INSERT INTO upload_jobs (user_id, job_type, status)
VALUES (1, 'not_a_real_type', 'pending');"
```

Watch `worker.py`'s log — it should show `attempt 1/5`, `2/5`, ... with
`run_after` pushed further out each time (60s, 120s, 180s...), then
`failed permanently after 5 attempts` on the log line once exhausted.
Confirm it's genuinely terminal:

```bash
psql -U postgres -d personalai_test -c "
SELECT status, attempts, last_error FROM upload_jobs WHERE job_type='not_a_real_type';"
# status should be 'failed' and stay that way — it will not be picked
# up again no matter how long you wait
```

Clean up the test row afterward:
`DELETE FROM upload_jobs WHERE job_type='not_a_real_type';`

---

## Known gaps to expect (not bugs in what you're testing — already flagged)

- **Migration bootstrap ordering**: `run_migrations.py` needs
  `users`/`projects`/`conversations`/`files` to already exist; nothing
  currently automates creating just those four before migrations run.
  Pick one ordering per 3.2 above, don't try to do both against the same DB.
- **`confirm_upload()` (the presigned-upload route) still processes
  inline**, not through the queue — only the direct `/api/files` upload
  path was moved to the transactional-outbox/worker flow. Both work, they
  just behave differently today.
- **Only 3 of 7 `responses_text()` call sites log to `ai_usage_ledger`**
  (embedding, metadata, analysis) — chat, memory extraction, title
  generation, compare, and gap-finder don't yet.
- **Redis is fully optional** — every code path checks for it and falls
  back to Postgres if `REDIS_URL` is unset or unreachable. Skipping Tier
  3's Redis container entirely still lets everything else in Tier 3 work,
  just without the cache layer.

---

## Cleanup

```bash
# stop worker.py / server.py with Ctrl+C in their terminals
docker stop redis-test && docker rm redis-test     # if you started one
psql -U postgres -d postgres -c "DROP DATABASE personalai_test;"   # if you're done testing
```
