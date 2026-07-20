# ADR-0001: Queue backend — Postgres worker vs. Celery

Status: accepted (Postgres worker)
Date: 2026-07-17
Resolved: 2026-07-20 — see Decision below.

## Context

`00-constitution.md` Principle 6 names Celery specifically for async/
task-queue work. What's built and verified (`worker.py`) is a
Postgres-backed queue using `FOR UPDATE SKIP LOCKED`: workers claim
`upload_jobs` rows, process them, retry with linear backoff up to
`MAX_ATTEMPTS`, and mark permanently-failed jobs `status='failed'` as a
dead-letter state. It requires no infrastructure beyond the Postgres
database the app already needs, and has been verified end-to-end
(real upload → import → extract_metadata → paper_analysis chain, retry/
backoff, dead-letter) against a real Postgres instance.

`processing-pipeline-architecture.md`'s original case for Celery was
built on four requirements a plain job table doesn't provide on its own:
priority queues, cooperative cancellation, worker heartbeats, and a
dead-letter workflow. `worker.py` has since implemented retry-with-
backoff and dead-letter itself, directly on Postgres. Priority queues,
cancellation, and heartbeats remain undone in either design.

## Decision

**Keep the Postgres worker. Do not migrate to Celery.**

Made here, explicitly, rather than left open indefinitely: every concern
this ADR originally raised against the Postgres worker has since been
addressed directly on top of it, without a broker —

- *Retry/backoff, dead-letter*: already had this when the ADR was
  opened (linear backoff, `MAX_ATTEMPTS`, `status='failed'` as the
  dead-letter state).
- *Observability* (the strongest point in Celery/Flower's favor below):
  `worker.py` now has structured JSON logs with a per-job correlation
  id, Prometheus metrics (`ai_calls_total`, `ai_tokens_total`, its own
  `/metrics` exposition endpoint), and a heartbeat-based liveness check
  (`GET /api/worker/health`) — see §12. This was the one gap Celery+
  Flower would have closed "for free"; it's closed now regardless.
- *Process supervision*: `Procfile` + `deploy/systemd/*.service` — see
  §5. Neither requires Celery specifically.

Priority queues and cooperative cancellation remain unimplemented in
both designs — genuinely still open, but neither is a demonstrated
near-term requirement (no caller has asked to cancel a running job or
jump a job ahead of the queue), so building either preemptively would
be exactly the kind of infrastructure-ahead-of-requirement this
project's own docs have repeatedly declined to do. Revisit if either
becomes a real, named requirement — at that point it's a scoped
addition to `worker.py`, not by itself a reason to also take on a
Redis/broker dependency for everything else.

## Alternatives considered

- **Keep the Postgres worker, add priority/cancellation/heartbeats to
  it directly.** Zero new infrastructure; more code to write and
  maintain in `worker.py` itself; doesn't get Celery's ecosystem
  (Flower, established retry/rate-limit primitives) for free.
- **Migrate to Celery**, per Principle 6 literally. Gets priority queues,
  `revoke()`-based cancellation, and Flower's worker monitoring UI
  largely for free; requires Redis (or another broker) as new
  infrastructure, and — per Principle 1 — an explicit justification for
  replacing `worker.py`'s already-working, already-tested
  implementation rather than extending it.
- **Do nothing further; leave `worker.py` as the queue, revisit only if
  priority/cancellation/heartbeats become an actual near-term need.**
  Consistent with this project's established pattern of not building
  infrastructure ahead of a demonstrated requirement
  (`upload-architecture.md` §2 made the identical call about Redis/Celery
  before `processing-pipeline-architecture.md` later reversed it once
  concrete requirements emerged).

## Consequences

- `00-constitution.md` Principle 6 (names Celery) is superseded for this
  specific decision by this ADR, per the constitution's own framing of
  ADRs as the mechanism for exactly this.
- No Redis/broker requirement is added to this app's infrastructure on
  account of the job queue (Redis remains optional, used only for the
  job-status cache, which no-ops when unset — see §5).
- Priority queues and cancellation stay explicitly out of scope until a
  real caller needs them; don't re-open this ADR speculatively.

## Cost / Security / Observability / Extensibility

- **Cost**: Celery migration adds a Redis (or broker) instance to run
  and pay for continuously; the Postgres worker adds none.
- **Security**: no material difference — both run inside the existing
  trust boundary; a broker adds one more network-reachable service to
  secure if self-hosted.
- **Observability**: Celery + Flower gives worker-level monitoring for
  free (`devops-observability.md` §7 already recommended this over
  building a custom worker dashboard); the Postgres worker's
  observability is currently log lines and direct SQL queries only.
- **Extensibility**: Celery's task-routing/priority-queue primitives are
  more extensible for future job types than hand-rolling the same in
  `worker.py`; the Postgres worker is more extensible in the sense that
  it has no new dependency's API surface to work within.
