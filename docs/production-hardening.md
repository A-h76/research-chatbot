# Production Hardening — Architecture

Scope: security and reliability gaps, re-auditing the current code the
same way `upload-architecture.md` did — not a generic enterprise
checklist. Design only, same format as the rest of the series.

**The throughline**: three of these eleven are real, concrete gaps found
by reading the code (MIME trust, unlimited rate limits on the most
abusable routes, a secret-management footgun). Several others are
*already handled* by the managed services this app already pays for
(R2/Neon) and just need confirming, not building. Flagging which is
which up front so effort goes to the three that matter.

---

## 1. MIME verification — real gap

`upload_file()` stores `mime=f.mimetype` — the `Content-Type` header the
**client** sends — and every extraction dispatch (`extract_text()`) branches
on the **filename extension**, also client-supplied. Nothing today checks
that a file claiming to be `paper.pdf` actually contains PDF bytes. Rename
any file to `.pdf` and it's routed straight into `_extract_pdf` (PyMuPDF)
regardless of what it actually is.

**Fix**: sniff the first few hundred bytes with `python-magic` (libmagic
bindings) right after the file lands on local disk, before extraction
dispatch — compare the sniffed type against the claimed extension; on
mismatch, reject with a clear error rather than silently trusting the
filename. Chosen over hand-rolled magic-byte checks because libmagic
already has the full signature database maintained; unlike the OCR
dependency question in `research-intelligence.md` §2 (where Tesseract's
Windows/managed-host friction was the reason to avoid it), libmagic is
low-friction here — it's commonly preinstalled or a one-line `apt` add on
the README's actual deploy targets (Render/Railway/Fly, all Linux), and
there's no already-configured alternative doing this job the way the
vision model was already doing OCR's job.

---

## 2. Virus scanning — new

**ClamAV**, not a third-party scanning API (VirusTotal etc.) — this app's
whole premise is private research documents staying private (the
README's own line: *"Your OpenAI API key stays on the backend — never
exposed to the browser"*); shipping a user's unpublished thesis draft to
a third-party scanning service for a virus check undercuts that. ClamAV
is free, self-hostable, and well-established — the same
no-new-paid-SaaS pattern the rest of this series has followed
(`devops-observability.md` §1 made the identical call against a hosted
APM).

**Where it runs**: same position in the pipeline as the checksum
computation already added in the storage implementation — on the local
temp file, before it's uploaded to R2 and before extraction, so an
infected file never reaches storage or the parser at all. Fails fast,
symmetric with the existing size-limit check.

---

## 3. PDF sandboxing

**Already half-solved by `processing-pipeline-architecture.md`, once it
ships.** Today, PyMuPDF/python-docx/python-pptx parse untrusted file
bytes **in the Flask request process** — a malformed file exploiting a
parser bug affects the same process serving every other user's request.
Moving extraction into `worker-import` Celery tasks (already designed)
means parsing runs in a separate OS process by construction — that's
process isolation, for free, as a side effect of the architecture
already chosen for an unrelated reason (not blocking the HTTP response).

What that alone doesn't cover — resource exhaustion (a crafted PDF that's
fine memory-safety-wise but decompresses to gigabytes, or loops for an
hour):

- `soft_time_limit` / `time_limit` per Celery task — a few lines of task
  config, no new dependency.
- `--max-memory-per-child` on the `worker-import` pool — Celery kills and
  respawns a worker process that exceeds it.

**Ceiling, stated plainly**: this is process isolation and resource caps,
not a full seccomp/gVisor sandbox. A dedicated container-level sandbox for
untrusted-file parsing is real infrastructure worth reserving for if this
app ever accepts uploads from fully untrusted (not just
allowlisted-email) users — not built now.

---

## 4. Quotas

The README already names this risk in prose, unenforced: *"With open
login + public deployment, anyone can chat on your API credit."* Quotas
are the technical enforcement of that existing warning, not a new
concern.

Two quota dimensions, both reading tables `database-design.md` already
built — no new schema:

- **Storage quota** — `storage_usage.bytes_used` (already live-updated on
  every upload/delete) checked at the top of the Upload Manager, before
  accepting a new file: `if bytes_used + incoming_size > limit: reject`.
- **AI spend quota** — `ai_usage_ledger`, summed per user over a rolling
  window (e.g. `SUM(cost_usd) WHERE user_id=... AND created_at > now() -
  interval '30 days'`), checked before an expensive call (chat, paper
  analysis) is allowed to proceed.

Both configurable per user via the same `ALLOWED_EMAILS`-style env
convention for a default, with a per-user override column reserved for
later if this ever needs to differ user-to-user — not built until a
second tier of user actually exists.

---

## 5. Rate limits

`flask_limiter` is already wired up with **7** per-route limits (export,
delete-account, support, search, compare, gaps, writing). Two things
missing, found by checking which routes *aren't* in that list:

1. **`/api/chat` has no rate limit at all** — the single most
   expensive-per-call route in the app (every message is a model call,
   potentially a long one) is currently unlimited.
2. **Every upload route is unlimited** — `/api/files`,
   `/api/uploads/presign`, `/api/uploads/confirm`,
   `/api/uploads/multipart/complete`. Unlimited `presign` calls alone
   let someone mint unbounded `UploadSession` rows without ever
   completing an upload — cheap for an attacker, real DB bloat and a
   feeder for the Quotas check in §4 to actually need to fire.

Both get a `@limiter.limit(...)` in the same style as the existing seven
— no new mechanism, just applying the one that's already there to the
two places it was missed.

The storage backend is still `memory://` — **this is the third doc in
this series to flag that** (`upload-architecture.md` §1.3,
`processing-pipeline-architecture.md` §1 puts Redis in as the Celery
broker anyway, `database-design.md` §5 already reserves the
`ratelimit:{scope}:{key}` Redis key pattern for this exact switch). Not
re-designed again here — just noting it's now genuinely overdue once
Redis exists for Celery regardless.

---

## 6. Object permissions

**Mostly already correct** — worth confirming precisely what's already
right before adding anything:

- Every presigned URL (GET via `file_raw`, PUT via `/api/uploads/presign`)
  is minted only after an ownership check (`x.user_id ==
  session["user_id"]`) — confirmed in the existing route code and in the
  storage-implementation confirm/complete routes (`us.user_id ==
  session["user_id"]`).
- Object keys are `uuid4().hex + ext` — 128 bits of randomness, not
  sequential, not practically enumerable.
- A presigned URL, once issued, is a bearer credential for its short TTL
  window — inherent to the presigned-URL pattern itself (the whole point
  is bypassing a per-request auth check), not a bug. The mitigation is
  already in place: short expiry (`UPLOAD_SESSION_TTL_SECONDS`, default
  1 hour) rather than a long-lived link.

**What to actually confirm operationally, not in code**: the R2 API
token used by `boto3` should be scoped to *only* this one bucket
(least-privilege), not a full-account token — an R2 dashboard setting,
not a code change. And the bucket itself must not have public-read
enabled — all reads already go through presigned URLs or the
authenticated `/api/files/<id>/raw` redirect, so public-read was never
needed and should be explicitly off.

---

## 7. Encryption

**Already covered by the managed services this app already uses — the
main risk is *not* re-verifying that and building something redundant.**

- **At rest**: Cloudflare R2 encrypts all stored objects by default, not
  optionally — nothing to configure. Neon Postgres encrypts at rest by
  default as a managed service. Both already true today, zero code.
- **In transit**: `boto3` talks to R2 over HTTPS by default; the app
  itself gets TLS from whatever terminates it in front of Flask (the
  hosting platform, per the README's Render/Railway/Fly deploy notes) —
  an infra/deploy config confirmation, not an application change.
- **Field-level encryption — explicitly *not* recommended.** Nothing in
  the schema warrants it: no payment data, no long-lived OAuth tokens
  persisted (Google auth is session-based via authlib, nothing durable
  stored), and email/name/picture/custom-instructions/memories are
  personal but not sensitive enough to justify the operational cost of
  envelope encryption and key rotation for a personal-scale app. Adding
  it here would be solving a threat model this app doesn't have.

---

## 8. Secret management — one real footgun found

Config is env-var-based via `.env` + `os.environ.get(...)` — the right
pattern for this app's scale (12-factor, already how the README's deploy
section expects hosts to configure it: *"set the same .env vars in the
host's environment settings"*). `.env` is correctly git-ignored (verified
in `.gitignore`). No new secret store needed — the gap is one specific
line:

```python
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(32).hex())
```

**If `FLASK_SECRET_KEY` is unset, every process restart generates a new
random secret** — silently invalidating every logged-in session, and (per
the storage implementation's `LocalProvider`) every outstanding signed
local-upload token, on every deploy. This is exactly the kind of failure
that's invisible until it happens in production and looks like a random
mass-logout bug.

**Fix**: extend the existing `IS_PRODUCTION` check (`server.py` already
has one) — refuse to start, loudly, if `IS_PRODUCTION` and
`FLASK_SECRET_KEY` is unset, instead of silently degrading to a
per-restart random value. A few lines, no new mechanism.

---

## 9. Disaster Recovery

Scoped to what this app's actual architecture needs, not a generic
multi-region playbook — Neon and R2 are both managed services already
carrying most of the durability burden this section would otherwise have
to build:

- **Neon Postgres outage** — managed service, Neon's own SLA/redundancy
  applies; the app-level plan is "redeploy is not needed, wait for Neon,"
  not a self-hosted standby.
- **R2 outage** — same reasoning; Cloudflare's durability guarantees
  apply to the objects themselves.
- **App server (Flask/Celery workers) failure** — stateless by design
  (all durable state is in Postgres/R2), so recovery is redeploy from
  git + the host's existing env config, not a snapshot-and-restore of
  the app tier at all.

Building custom active-active multi-region failover for a personal-scale
app would be solving for an availability target nobody has set — noted
as a real future upgrade, not built speculatively.

---

## 10. Backup strategy

- **Postgres**: enable/confirm Neon's built-in point-in-time recovery
  rather than a custom `pg_dump` cron — it's a managed-service feature
  already available, not something to reimplement.
- **R2 objects**: already durable by Cloudflare's own replication; the
  one thing worth turning on explicitly is **bucket versioning**, as a
  safety net against an *accidental* delete — including a bug in the
  reconciliation tooling itself (`storage/manager.py`'s `reconcile()`,
  built in the storage-implementation pass) ever misclassifying a
  still-referenced object as orphaned and removing it. Versioning is the
  undo button for exactly that failure mode.
- **The real coupling to design for**: a Postgres restore to an earlier
  point in time and the (unrestored, still-current) R2 bucket can drift
  out of sync with each other — a `files.path` row from *after* the
  restore point pointing at an object that still exists in R2, or a row
  that existed at the restore point whose object was deleted since. This
  is precisely what reconciliation (§11) is for.

---

## 11. Restore strategy

The runbook, reusing tooling this series already built rather than
inventing a separate restore-specific process:

1. Fork/restore Neon to the target point in time.
2. Point the app at the restored database.
3. Run `flask --app server reconcile-storage` (built in the storage
   implementation pass) — surfaces exactly the drift described in §10:
   objects in R2 with no matching row (orphaned by the restore) and rows
   with no matching object (deleted after the restore point, now
   dangling).
4. Run `flask --app server gc-storage` to clean up anything the restore
   left orphaned, once the reconcile report has been reviewed — not
   automatically, since a restore is exactly the moment to look at the
   report before deleting anything (`reconcile()`'s `dry_run=True`
   default, from the storage implementation, exists for this).

No new tooling in this section — the entire restore runbook is "restore
the DB, then point the existing storage-hygiene commands at the result."

---

## 12. Summary — what's actually new here

| Real gap, found in the code | Already covered, confirm don't rebuild |
|---|---|
| MIME verification (§1) | R2/Neon at-rest encryption (§7) |
| `/api/chat` + upload routes unrated-limited (§5) | Object ownership checks — already correct (§6) |
| `FLASK_SECRET_KEY` random-fallback footgun (§8) | Postgres PITR — Neon feature, not custom (§10) |
| Virus scanning (§2) — genuinely new | PDF sandboxing — mostly free once Celery ships (§3) |
| Quota enforcement (§4) — policy on top of existing tables | R2 durability — Cloudflare default (§10) |

Same close as the rest of the series: design only — say the word for the
implementation pass.
