# Master Architecture Constitution

**Status**: binding. Every prompt, task, or change after this one is
evaluated against the ten principles below before it's evaluated against
anything else — including its own stated goal. If a change satisfies its
goal but violates a principle here, the principle wins; open an ADR
instead of proceeding.

This document is truthful about where the codebase stands *today*
against each principle, not just what the principle says — a constitution
that doesn't admit its own violations gets silently ignored by the next
piece of work. Where today's code falls short, that's named directly, not
smoothed over.

---

## The ten principles

### 1. Never rewrite without justification — document it in an ADR

A rewrite is: replacing a working module's implementation wholesale
rather than extending it. Any prompt proposing one must first produce an
Architecture Decision Record (template: §13) stating what exists, why
it's insufficient, what alternatives were considered, and what the
rewrite costs in risk and time. No ADR, no rewrite — extend instead, even
if the extension is less elegant.

### 2. Prefer extension over replacement

Composition, plugins, interfaces. A new capability should be a new class
implementing an existing interface (`Importer`, `StorageProvider`), a new
handler registered in an existing dispatch table (`worker.py`'s
`HANDLERS`), or a new optional parameter on an existing function
(`_process_document(..., job_id=None)`) — not a parallel implementation
of something that already works.

### 3. Every subsystem independently deployable

Modular monolith with clear bounded contexts, not necessarily
microservices — a bounded context is independently deployable the moment
it can be extracted into its own service without a rewrite, which is a
property of its *interfaces*, not of how many processes it runs in today.
`storage/` and `imports/` already qualify: neither imports from
`server.py`, both are consumed through a narrow public API
(`storage.upload()`, `imports.extract_text()`). `server.py` itself does
not yet qualify — it is one 5,000+ line module with routes, models, and
business logic sharing a namespace.

### 4. Cloud-native & horizontally scalable

Stateless services, queues, object storage, CDN. `worker.py` already
satisfies this for the job-processing tier: `FOR UPDATE SKIP LOCKED`
means N worker processes can run against the same Postgres queue with no
coordination beyond the database itself, and nothing in it holds
process-local state across requests. `server.py`'s Flask processes are
already stateless (session is a signed cookie, not server memory).
Object storage (R2) is already behind a swappable provider interface.

### 5. AI output versioning

Every generated result stores `model_id`, `prompt_version`,
`pipeline_hash`, `input_hash`. **Partially satisfied today**:
`PaperAnalysis` stores `model` (= model_id) and `content_hash` (=
input_hash) already. It does **not** yet store `prompt_version` or
`pipeline_hash` — `ai_usage_ledger` captures `prompt_version_id` per
*call*, but the generated *row* (`PaperAnalysis`, `DerivedAnalysis`)
doesn't reference it, which is exactly the cache-correctness gap
`research-intelligence.md` §6 already named: a prompt edit today doesn't
invalidate old cached analyses, because nothing on the row records which
prompt version produced it. Closing this is the natural next piece of
work this principle creates, not a new problem it discovers.

### 6. Async-first for long tasks — task queue for all I/O and AI operations

**Named tension, not silently resolved**: this principle names Celery
specifically. What's built (`worker.py`) is a Postgres-backed queue
(`FOR UPDATE SKIP LOCKED`), not Celery — and it already provides retry
with backoff, a dead-letter state, and horizontal scaling across worker
processes, which is the *functional* bar `processing-pipeline-
architecture.md` originally used to justify recommending Celery. Every
long-running operation already *does* go through a queue; the queue
implementation just isn't the one this principle names.

Per Principle 1, replacing a working, tested queue to satisfy a framework
preference alone requires an ADR, not a silent swap — **Draft ADR-001**
is opened by this document (§13) to make that call explicitly, with
whoever owns this codebase deciding it, not a future prompt assuming it.

### 7. Cost, Security, Observability, Extensibility

Every design decision names its position on all four, even when the
answer is "not yet addressed." Precedent already exists:
`devops-observability.md` (cost/observability), `production-hardening.md`
(security), and the `Importer`/`StorageProvider` interfaces
(extensibility) — this principle formalizes doing that every time, not
just when a dedicated doc happens to cover it.

### 8. Functional after every milestone — incremental delivery, no long-lived branches

Already the operating pattern across every task so far: each one shipped
as a working, verified state before the next began (storage foundation →
Import Engine → transactional outbox → queue worker → Redis/cost ledger,
each independently tested against real infrastructure before moving on).
Continue it — no task should leave `server.py` unable to boot or a route
unable to serve a request when it's done.

### 9. Dependency Inversion — interfaces for LLM providers, storage, queues, databases

**Uneven today, named plainly**:

| Dependency | Status |
|---|---|
| Storage backends | **Satisfied** — `StorageProvider` interface, `R2Provider`/`LocalProvider`, chosen by `STORAGE_PROVIDER` env var |
| Databases | **Partially satisfied** — SQLAlchemy already abstracts SQLite/Postgres; no ORM-bypassing raw SQL outside `run_migrations.py`/`backfill.py`, which are migration tooling, not application code |
| Queues | **Not satisfied** — `worker.py` calls Postgres-specific `with_for_update(skip_locked=True)` directly; no interface a queue implementation sits behind, so swapping backends means editing `worker.py` itself |
| LLM providers | **Not satisfied** — `client = OpenAI(api_key=...)` is constructed once at module load in `server.py` and called directly from a dozen+ functions; no interface a second provider could implement |

Configuration should decide the concrete implementation for all four;
today only storage actually works that way.

### 10. Testability

Every component unit-testable with mocks; integration tests run against
containers. Already the practice for what's been built —
`storage/test_storage.py` and `imports/test_imports.py` are pure,
dependency-free unit tests; every task's verification ran against real
containers (Postgres, Redis) or real external services (R2, OpenAI)
rather than mocks standing in for them, specifically because mocked
storage/queue tests were shown early in this project to miss real
integration bugs (the presigned-URL round trip, real Postgres FK
ordering, Redis's byte-vs-string key encoding) that a mock would have
hidden. Keep both halves: fast unit tests for logic, real containers for
integration — neither replaces the other.

---

## 11. What this document is not

Not a mandate to retrofit every existing module to satisfy every
principle immediately. Principle 1 already governs how gaps named here
get closed: with an ADR, deliberately, one at a time — not as a
side-effect of the next unrelated task.

## 12. Where ADRs live

`docs/adr/NNNN-title.md`, numbered sequentially, never renumbered or
deleted once merged — a reversed decision gets a new ADR that supersedes
the old one, which stays in place as the historical record of what was
tried and why it changed.

## 13. ADR template

```markdown
# ADR-NNNN: <title>

Status: proposed | accepted | superseded by ADR-XXXX
Date: YYYY-MM-DD

## Context
What exists today, and what problem or requirement makes it insufficient.

## Decision
What's changing, stated as a single clear sentence.

## Alternatives considered
Each option genuinely weighed, including "do nothing" — with why it was
or wasn't chosen. A one-option ADR is a rationalization, not a decision.

## Consequences
What gets easier, what gets harder, what this forecloses. Named for both
directions — a decision with no downside named is a decision under-examined.

## Cost / Security / Observability / Extensibility
Principle 7, applied to this specific decision — one line each, even if
the line is "not affected."
```

**Draft ADR-001** (opened, not resolved, by this document): *Queue
backend — keep the Postgres `FOR UPDATE SKIP LOCKED` worker, or migrate
to Celery per Principle 6.* Context and the functional-parity argument
are in §6 above; the alternatives-considered and final decision are
deliberately left for whoever owns this call to write, not decided here
as a side effect of writing the constitution that raised the question.
