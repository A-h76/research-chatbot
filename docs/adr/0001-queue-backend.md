# ADR-0001: Queue backend — Postgres worker vs. Celery

Status: proposed
Date: 2026-07-17

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

*Not made here.* This ADR is opened by the constitution, not resolved by
it — the call belongs to whoever owns this codebase, informed by the
alternatives below, not decided as a side effect of writing the document
that raised the question.

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

Unresolved pending a decision above — to be filled in once one is made.

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
