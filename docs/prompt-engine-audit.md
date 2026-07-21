# Prompt Engine — Reuse Audit

Scoped to the six files/areas named in the audit request. Read directly
against the current repository (not `brain.md`, not memory) —
`class`/`def`/table names below were grepped and confirmed, not assumed.
Companion to `brain.md` §6/§6b, which covers the same code from a
"what's running and how" angle; this doc is the "what to build on top of
it" angle for prompt-engine work specifically.

---

## 1. Component inventory

### `backend/ai/prompt_registry.py` — `PromptRegistry`

The only thing in this codebase that reads/writes `prompt_versions`.

- **`get_active_version(name)`** — the one active `PromptVersion` row for
  a name, or `None`.
- **`list_prompts()`** — every name's active version (not full history).
- **`get_prompt(name, version=None, variables=None)`** — resolves a
  version (active, or a specific pinned one), Jinja2-renders it against
  `variables`, and returns **the rendered string only**. Raises
  `ValueError` if no such prompt/version exists, `TemplateError` (this
  module's own wrapper, not `jinja2`'s) on a render failure.
- **`create_prompt(name, description, template_text, default_version=1)`**
  — first version of a new name, `is_active=True`. `description` is
  accepted but **not persisted** — `prompt_versions` has no such column
  (see `models.py` below); it exists only so the method's signature
  matches an external spec.
- **`add_version(name, template_text, is_active=False)`** — next
  version number for an existing name; flips every other version's
  `is_active` to `False` first if this one is going active. Raises
  `ValueError` if the name doesn't exist yet.

Owns a **private** `declarative_base()` (module-level `_Base`), separate
from `server.py`'s own `Base`, specifically so its constructor only
takes a `Session` — not a second "which mapped class" argument. This
works because `PromptVersion` maps onto the real `prompt_versions` table
by name (`__tablename__`), not by Base identity; it does **not** create
the table itself (assumes the migration or `server.py`'s parallel
`create_all()` already has).

**Notable gap**: `get_prompt()` throws away the resolved `PromptVersion`
row (id, version number) once it renders the string. A caller that wants
to record *which version* produced a given AI call has no way to get
that back from this method — it would need a separate
`get_active_version()` call first. No current caller does this (see §7).

### `backend/ai/models.py` — table factories, no live classes

Two **factory functions**, not classes: `create_prompt_version_model(Base)`
and `create_pipeline_version_model(Base)`. Exist because migration 0005
created `prompt_versions`/`pipeline_versions` without `server.py` ever
getting ORM classes for them.

- `create_prompt_version_model` → `PromptVersion` (`prompt_versions`).
  Instantiated exactly once, by `prompt_registry.py`, against that
  module's private `_Base`. This is the only place this factory is
  called anywhere in the codebase.
- `create_pipeline_version_model` → `PipelineVersion` (`pipeline_versions`).
  **Never instantiated against any Base anywhere in the codebase.** The
  factory exists; nothing calls it. `pipeline_versions` is a real table
  (migration 0005 creates it, with real FK constraints to
  `model_versions`), seeded with one row by `backfill.py`, but there is
  no live Python class touching it. Any code that wants to read or write
  `pipeline_versions` today has to either write raw SQL or call this
  factory itself for the first time.

Deliberately does **not** redefine `ModelVersion`/`AIUsageLedger` (those
are `server.py`'s own live classes — redefining them here would fork the
same table under two disconnected class identities) and there is **no
`PromptTemplate` class anywhere in this codebase** — `prompt_versions`
is one flat table, versions of the same prompt grouped by a plain `name`
column, not a parent/child (`PromptTemplate` → `PromptVersion`) pair.
Any future design that assumes a `PromptTemplate` table exists is
assuming a schema this codebase doesn't have.

### `backend/ai/prompts.py` — hardcoded default prompt text

Not a registry, not a model — three literal Jinja2 template strings
(`EXTRACT_METADATA_PROMPT`, `PAPER_ANALYSIS_PROMPT`,
`SEMANTIC_SEARCH_PROMPT`) plus `ensure_prompt()`/`ensure_default_prompts()`,
idempotent-by-content helpers that upsert those three into
`prompt_versions` via `PromptRegistry` on demand (called from
`backend/upload/routes.py` and `backend/search/routes.py` before each
use, not once at startup).

Exists specifically because `worker.py` does `import server` and
`server.py` can't import back from anything `worker.py`-adjacent without
recursing — this module imports neither, so both `server.py`-side code
and anything wired the same way `worker.py` is can safely depend on it.
Two constants worth knowing for extension work: `META_EXCERPT_CHARS`
(3,000) and `ANALYSIS_MAX_CHARS` (12,000) — the truncation limits applied
before these templates ever see the paper text — and
`ANALYSIS_ARRAY_FIELDS`, the tuple of `paper_analysis` output keys that
get coerced to a list if the model returns a bare string instead.

**The prompt text here is a deliberate, verified rewrite** of two older
prompts that already lived elsewhere (`server.py`'s own
`_META_PROMPT`/`_ANALYSIS_PROMPT`, `str.format()`-style) and one that's a
byte-for-byte copy of `backend/ai/seed.py`'s own `"semantic_search"`
string — see the module docstring for why that copy has to stay
byte-identical (both `ensure_default_prompts()` and `seed.py`'s
`seed_prompts()` manage the same DB row independently, and
`ensure_prompt()`'s idempotency check is by content).

### `backend/ai/seed.py` — one-shot dev/ops seeding CLI

`seed_prompts()`, `seed_pipelines()`, `seed_all()`, runnable via
`python -m backend.ai.seed`. Idempotent by name (skips anything already
present under that name — logs `SKIP` vs `OK` to stdout, doesn't raise).

- `seed_prompts()` writes **7 prompts** into the real `prompt_versions`
  table via `PromptRegistry`: `paper_summary`, `paper_analysis`,
  `citation_generation`, `semantic_search`, `gap_analysis`, `comparison`,
  `literature_review`. **`paper_analysis` collides by name** with a real,
  detailed template `backfill.py` already seeds (and the app's actual
  `paper_analysis` job handler depends on) — the idempotent-by-name check
  means this module's own shorter stub is silently skipped if
  `backfill.py` ran first, never overwriting the real one. The other six
  names don't collide with anything.
- `seed_pipelines()` writes **3 named chat-call presets**
  (`gpt-4o-chat`, `gpt-4o-mini-chat`, `gpt-4o-analysis`, each a flat
  `{model, temperature, max_tokens}` dict) into `model_presets` — **not**
  `pipeline_versions`, despite the name. `_ensure_model_presets_table()`
  creates that table ad hoc (`checkfirst=True`) if migration 0012 hasn't
  run yet.
- Owns its own private `_Base` (for `ModelPreset` only) — same
  no-`import-server` reasoning as everything else in `backend/ai`.

### `server.py` — `ModelVersion` and `AIUsageLedger`

Both are live classes on `server.py`'s **own** `Base` (not `backend/ai`'s
private ones) — the two pieces of this stack that were never split out.

- **`ModelVersion`** (`model_versions`): `logical_name` +
  `provider_model_id` + `version` + `is_active`. Seeded once by
  `backfill.py` (`default_model`/`utility_model`/`embed_model`, each
  version 1, active) from whatever `.env` said at seed time — exists so
  "which model produced this row" survives a later env var change, not
  so the app re-reads it live on every call (nothing in `backend/ai`
  currently resolves a live `ModelVersion` row before calling a model;
  `ModelRegistry.call()` takes a raw provider model string directly).
- **`AIUsageLedger`** (`ai_usage_ledger`): append-only, one row per
  OpenAI call, written **only** from `responses_text()` / `embed_texts()`
  / `_log_chat_cost()` — the *legacy*, OpenAI-only call path still used
  by `/api/chat` and the original `import → embed / extract_metadata /
  paper_analysis` job handlers in `worker.py`. Has a real
  `prompt_version_id` **column** (plain `Integer`, no ORM-level FK — the
  target table lives under `backend/ai`'s private Base, so there's
  nothing to point a SQLAlchemy `ForeignKey` at; migration 0006 adds the
  real DB-level FK) — **but grepping the whole codebase, nothing ever
  sets it.** No call site populates `prompt_version_id` when it writes an
  `AIUsageLedger` row. The column is real, wired at the DB level, and
  currently dead: `get_prompt()`'s own information-loss (above) means no
  caller even has a version id in hand to pass in.

**Important distinction for prompt-engine work**: `AIUsageLedger` is
**not** what records usage for anything that goes through
`ModelRegistry`/`PromptRegistry` (the "new" path — `backend/upload`,
`backend/search`, and anything `backend/ai` itself calls). That path
writes to a **second, separate** table —
`backend/ai/cost_ledger.py`'s `CostLedgerEntry`
(`model_registry_cost_ledger`) — via `ModelRegistry.call()`/`.embed()`
internally calling `self._cost_ledger.log(...)` whenever the registry
was constructed with a `db_session`. `CostLedgerEntry` has **no**
prompt-version column at all — not even the dead one `AIUsageLedger` has.
Two AI calls made through two different code paths in this app today are
tracked in two different tables, on two different Bases, with two
different (and both incomplete) relationships to which prompt version
was used.

### `backend/search/routes.py` — RAG (`POST /api/rag`)

The one real end-to-end consumer of `PromptRegistry` + `ModelRegistry`
together outside `backend/upload`. Flow: embed the query
(`model_registry.embed`) → cosine-rank the caller's own `Chunk` rows
(plain Python, no prompt/model involved) → `ensure_default_prompts(db)`
→ `prompt_registry.get_prompt("semantic_search", variables={"documents":
..., "question": ...})` → `model_registry.call(utility_model, [...],
user_id=user_id)`. Cost for this call lands in
`model_registry_cost_ledger` (see above), tagged with `user_id` and
`model`, **not** with which prompt version answered the question — same
gap as everywhere else in this stack.

`GET /api/documents/search` (the sibling route in the same file) never
touches a prompt at all — it's pure vector similarity, no model call
beyond the query embedding.

---

## 2. Reuse without changes

Genuinely solid as-is for prompt-engine work built on top of it — no
identified defect, no missing capability that blocks reuse:

- **`prompt_versions` schema + its partial-unique-active-per-name index**
  (migration 0005). Versioning-by-name with exactly one active version
  is the right primitive; nothing about it needs to change to support
  more prompts or more callers.
- **`PromptRegistry.get_active_version` / `list_prompts` / `create_prompt`
  / `add_version`** — correct, tested (`backend/ai/test_prompt_registry.py`),
  idempotent where it claims to be. A new prompt-engine feature that just
  needs "read/write named, versioned templates" needs nothing more than
  this class, injected the same way every other caller already does.
- **`ensure_prompt()`/`ensure_default_prompts()`** (`prompts.py`) — the
  idempotent-by-content upsert pattern is exactly right for "make sure
  this default exists" without a startup-time seeding step, and it
  already solved the real `worker.py`/`server.py` import-cycle
  constraint everything else in this stack has to respect.
- **`CostLedger.estimate_cost()`** (pure function, no DB) — model-name
  prefix matching and the confident-pricing-only policy are both sound
  and reusable regardless of what calls it.
- **`ModelRegistry.call()`/`.embed()`** (not in the requested file list,
  but load-bearing for anything a prompt engine would call) — multi-provider
  routing, retry/backoff, and cost-logging are already correct and
  provider-agnostic; a prompt engine doesn't need its own model-calling
  layer.

## 3. Needs to be extended

Real capability gaps in code that otherwise works, not rewrites:

- **`PromptRegistry.get_prompt()` should return the resolved version
  alongside the rendered string** (e.g. `(text, version_row)` or an
  object), not just the string. Every caller today throws the version
  away; nothing can be built on "attribute this AI call to the exact
  prompt version that produced it" until this changes.
- **`AIUsageLedger.prompt_version_id` needs an actual writer.** The
  column and its DB-level FK already exist (migration 0006) — the gap is
  entirely on the write side: no call site populates it. Fixing
  `get_prompt()` (above) is the prerequisite; this is the second half.
- **`CostLedgerEntry` (`model_registry_cost_ledger`) needs a
  prompt-version column** to reach parity with even `AIUsageLedger`'s
  (currently dead) one — right now it's structurally impossible to
  attribute a `ModelRegistry`-path cost row to a prompt version at all,
  not just unpopulated.
- **`PromptRegistry.create_prompt()`'s `description` parameter is
  accepted and dropped.** If prompt descriptions/metadata (author,
  purpose, changelog) are in scope for the engine, `prompt_versions`
  needs a real column for it (schema change), not just wiring the
  existing parameter through — there's nowhere in the current table for
  it to go.
- **The two usage-ledger tables (`ai_usage_ledger` vs
  `model_registry_cost_ledger`) need a reconciliation decision** before
  a prompt engine reports cost/usage per prompt-version — today "total
  cost for prompt X" would have to query two tables with different
  schemas and no shared key, and even then would miss the legacy-path
  calls that predate `backend/ai` entirely.

## 4. Needs to be created from scratch

Nothing in the audited files provides these at all today:

- **A way to actually use `pipeline_versions`.** The table, the FK
  constraints, and the ORM factory (`create_pipeline_version_model`) all
  exist; no code anywhere instantiates a `PipelineVersion` or reads/writes
  the table. A prompt engine that wants "one addressable bundle of
  {chunking params, embed model version, prompt versions} that produced
  this file's output" has zero existing call sites to build on — this
  is new integration work, not extension of something partially wired.
- **Any API/UI for picking or pinning a specific prompt *version*
  (not just the active one) for a call.** `get_prompt(name, version=...)`
  already supports pinning at the Python level; nothing exposes that
  externally — `GET /api/ai/prompts` only lists active versions, and
  `POST /api/ai/test` (both `server.py`, `@login_required`) doesn't
  accept a version parameter either.
- **A/B or gradual-rollout serving of multiple active-ish versions.**
  The schema's partial unique index enforces exactly one `is_active` row
  per name by design — anything beyond "one live version at a time"
  (canarying a new version to a subset of calls, etc.) needs new schema,
  not a code change against the current one.
- **Reconciling `paper_analysis`'s name collision properly.** Today it's
  papered over by seeding order (`backfill.py` first, `seed.py` second,
  idempotent-by-name protects the real one) — there's no actual
  namespacing (e.g. a "seed source" concept) that would let two
  legitimately different `paper_analysis` templates coexist on purpose
  if that were ever needed.

## 5. Database tables that already exist

| Table | Owning Base | Created by | Live ORM class? |
|---|---|---|---|
| `prompt_versions` | `backend/ai/prompt_registry.py`'s private `_Base` | migration 0005 | Yes — `PromptVersion` |
| `pipeline_versions` | n/a (factory exists, never instantiated) | migration 0005 | **No** — see §1/§4 |
| `model_presets` | `backend/ai/seed.py`'s private `_Base` | migration 0012 (+ ad hoc `checkfirst` create in `seed.py`) | Yes — `ModelPreset` |
| `model_registry_cost_ledger` | `backend/ai/model_registry.py`'s private `_Base` | `create_all(checkfirst=True)` at `server.py` startup, no migration | Yes — `CostLedgerEntry` |
| `model_versions` | `server.py`'s own `Base` | migration 0005 | Yes — `ModelVersion` |
| `ai_usage_ledger` | `server.py`'s own `Base` | migrations 0002/0006 | Yes — `AIUsageLedger` |

All six already exist in any environment that's run
`server.py` once + `run_migrations.py` — no migration work needed to
start building on top of what's here today.

## 6. New tables potentially needed

None of the above are required just to **reuse** the existing stack —
everything in §2 works against the six tables above as they stand. The
following would only be needed if a specific new capability from §4 is
actually in scope, not as a blanket recommendation:

- **A `prompt_version_id` column on `model_registry_cost_ledger`**
  (§3) — a column addition to an existing table, not a new table, if
  cost-per-prompt-version reporting for the `ModelRegistry` path is
  wanted.
- **Some join/summary structure across `ai_usage_ledger` and
  `model_registry_cost_ledger`** — only if unifying usage reporting
  across both call paths (§3) is in scope; could as easily be a view or
  application-level merge as a new table, so this is a design decision,
  not a foregone schema change.
- **A real usage for `pipeline_versions`**, or a new, smaller table if
  its shape (rare writes, whole-bundle reads, hard FKs to
  `model_versions`) turns out to be the wrong fit once someone actually
  tries to wire it up — can't be assessed further without knowing the
  intended caller.

No table is needed to support prompt *description*/metadata unless §3's
`description` gap is prioritized — that's a column addition to
`prompt_versions`, not a new table.
