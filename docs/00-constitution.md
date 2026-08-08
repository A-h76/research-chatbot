# Master Architecture Constitution

**Status**: binding. Every prompt, task, or change after this one is
evaluated against the ten principles below before it's evaluated against
anything else — including its own stated goal. If a change satisfies its
goal but violates a principle here, the principle wins; open an ADR
instead of proceeding.

**Companion (2026-08-05):** [`ENGINEERING-CONSTITUTION-v1.md`](ENGINEERING-CONSTITUTION-v1.md) —
Platform Layers vs Product Domains, “don’t clean for aesthetics,” thin `server.py`
endgame, AI Gateway discipline, and the 80/20 debt model. Living pictures:
[`ENGINEERING-EVOLUTION-TRACKER.md`](ENGINEERING-EVOLUTION-TRACKER.md) (Current → Target)
and [`ARCHITECTURE-HEALTH.md`](ARCHITECTURE-HEALTH.md) (scored KPIs). These do **not**
replace this document; they direct *how* we renovate without rewriting.

**Companion (2026-08-08):** [`PRODUCT-CONSTITUTION-v1.md`](PRODUCT-CONSTITUTION-v1.md) —
Researcher First, Invisible Intelligence, workflow-over-features, one purpose per screen.
Binding for UI/product; does **not** replace engineering principles here.

**Frozen research-OS doctrines** (Engineering Constitution §0.5 — Bite 16):

```text
One Research Journey  →  One Canonical Pipeline  →  Many Entry Points
One Business Rule     →  One Implementation      →  Many APIs
```

**Assistant vs execution (ADR-0018):**

```text
Assistant Engine decides *what* help the researcher needs.
Capability Router decides *how* to execute that help.

LLMs generate language.  Dhund generates decisions.
Research State is computed from system signals — never guessed by an LLM.
Frontend decides how Dhund looks.  Backend decides how Dhund thinks.

The system may know everything.  The UI shows only what helps the current task.
Research State is internal.  Pages get one status + one recommendation + one context — not a dashboard.
```

Contract: [`docs/contracts/assistant-engine-contract.md`](contracts/assistant-engine-contract.md).  
Workflow contracts: [`docs/contracts/WF-v1.0-COMPLETE-FREEZE.md`](contracts/WF-v1.0-COMPLETE-FREEZE.md).

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

### 8.5 Product workflow first — thin vertical slices over feature collections

Roadmap items start from a researcher problem and end as one complete,
measurable workflow. Architecture should remain stable and serve workflow
outcomes, not drive breadth-first feature exposure.

Ship one polished workflow at a time (for example, Evidence-backed
Literature Review), then measure and improve before opening the next
workflow surface.

### 8.6 Platform freeze discipline

Once foundational platform layers are accepted for a release window, no
new platform subsystem work should start unless it either (a) directly
unblocks the active validated workflow, or (b) fixes a demonstrated
production limitation. Prefer workflow completion over architecture
expansion.

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

### 11. Evidence First — AI features consume the Evidence Layer

**Binding (accepted ADR-0003).** All knowledge shown to users as research
fact must originate from stored evidence objects. LLMs may organise,
summarise, compare, and explain; they may never invent evidence. Every
generated research statement must be reproducible from stored
`EvidenceObject` rows (or an explicit “insufficient evidence” state).

**Every new AI feature must consume the Evidence Layer rather than bypass
it.** Literature review generation, peer-review assistance, gap analysis,
research Q&A, and Writing Studio AI surfaces retrieve structured evidence
first, then optionally use an LLM to organise or explain. Features that
call a model with only raw PDF text / chat history and no evidence-object
contract violate this principle and require an ADR that explicitly
waives it.

**Today:** Writing Shell (`v0.1.0`) and Phase 1.5/1.7 produce inputs, but
the Evidence Layer MVP (objects, bindings, Inspector, explain API) is
the Week 2 / Phase 2.2 work that closes the **platform** gap. Until that
layer ships, new AI writing features that claim research backing are out
of scope (see Phase 2.4 sequencing in `docs/phase-2-writing-roadmap.md`).

**Research Intelligence (ADD-0005 / ADR-0004 / ADR-0006):** After the Evidence
Layer exists, intelligent features follow one staged pipeline over Evidence
Queries — Retrieval → Ranking → Consensus → Conflict → Reasoning →
Presentation. RI never owns knowledge; it only computes over EvidenceObjects.
See `docs/architecture/phase-2.3-research-intelligence-pipeline.md`.

**Evidence Layer contracts (ADR-0005):** EvidenceObject, Explain API,
sentence bindings, review workflow, provenance, and confidence bands are
frozen platform contracts as of `v0.2.0-rc1`. Breaking changes require a
new ADR. See `docs/architecture/week2-evidence-layer-platform-contracts.md`.

---

## 12. What this document is not

Not a mandate to retrofit every existing module to satisfy every
principle immediately. Principle 1 already governs how gaps named here
get closed: with an ADR, deliberately, one at a time — not as a
side-effect of the next unrelated task.

## 13. Where ADRs live

`docs/adr/NNNN-title.md`, numbered sequentially, never renumbered or
deleted once merged — a reversed decision gets a new ADR that supersedes
the old one, which stays in place as the historical record of what was
tried and why it changed.

## 14. ADR template

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
