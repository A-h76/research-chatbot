# Prompt Engine — Architecture Design

Builds directly on [`prompt-engine-audit.md`](./prompt-engine-audit.md) —
every "reuse as-is" / "extend" / "build from scratch" call below traces
back to a specific finding there. This doc is the design; nothing here
has been implemented yet, and every schema/signature below is a proposal
to review, not a fait accompli.

---

## 0. What this is actually adding, in one paragraph

Seven pieces were asked for; two of them turn out to need **no new
table** at all (System Prompt Manager, Memory Engine — both sit on top
of tables that already exist), one needs **no table by design** (Model
Router — config + in-memory override, matching that the spec gave it no
`Table:` line unlike every other component), and the remaining four
(Prompt Registry extension, Persona Engine, Prompt Builder's output
type, Prompt Executions) are real schema/code additions. The throughline
connecting all seven: `AssembledPrompt` (§4) carries a
`prompt_version_id` forward from the moment a prompt is resolved through
to the audit row written by Prompt Executions (§7) — closing the exact
gap the audit flagged (`AIUsageLedger.prompt_version_id` exists and is
never set; §3 of the audit).

---

## 1. Design constraints carried over from the audit (non-negotiable)

These aren't style preferences — each one is a real constraint already
proven necessary elsewhere in this codebase, and violating any of them
reproduces a bug this project has already hit and fixed once:

1. **Never `import server`.** Every new class here is constructor-injected
   (`SessionLocal`, model classes, etc.) exactly like `auth/`, `quotas/`,
   and all of `backend/`. `server.py` runs as `__main__`; anything it
   reaches into that imports it back recurses.
2. **JSON goes in `Text` columns, application-serialized** — matching
   `UserFile.tags`, `OutboxEvent.payload`, `PipelineVersion.chunking_params`,
   `ModelPreset.config`. Not `JSON`/`JSONB` SQLAlchemy types. `examples`,
   `output_schema`, and any other structured column below follow this.
3. **No FK across a private Base and `server.py`'s real Base.** Where a
   new column needs to reference `users.id`/`projects.id`, it's a plain
   `Integer`, no SQLAlchemy `ForeignKey` — the same pattern
   `CostLedgerEntry.user_id` already uses, with the real FK constraint
   added only at the raw-SQL migration level. Where two new tables both
   live under the *same* private Base, a real `ForeignKey("othertable.id")`
   works fine (SQLAlchemy resolves it within one `MetaData`) — used
   below for `prompt_executions → prompt_versions`/`personas`.
4. **`create_all(checkfirst=True)` creates tables, never columns.**
   Adding a column to an existing private-Base table needs the same
   two-sided fix `brain.md` §6 already documents for `UploadJob`/
   `AIUsageLedger`: an idempotent Postgres migration (`ADD COLUMN IF NOT
   EXISTS`) **and** an entry in `server.py`'s `ensure_columns()` for
   SQLite dev DBs that already have the table. Skipping the second half
   reproduces that exact bug on every dev machine with an existing
   `chat_dev.db`.
5. **Seeding is idempotent by name**, print `SKIP`/`OK`, never raise on
   "already exists" — matching `seed.py`'s existing convention exactly.

---

## 2. Module layout

```
backend/ai/
  models.py            existing + 2 new factories: create_persona_model,
                        create_prompt_execution_model
  prompt_registry.py    existing, extended:
                          - PromptVersion gets 6 new columns (§3)
                          - get_prompt() returns (text, PromptVersion) (§3)
                          - its _Base also now hosts Persona and
                            PromptExecution (§7) — one shared MetaData,
                            so prompt_executions' FKs resolve for real
  prompts.py            unchanged — still the hardcoded default template
                        text + ensure_default_prompts()
  seed.py                existing + extended: seed_personas(),
                        seed_system_prompt() (reuses seed_prompts()
                        machinery, see §3.2)
  system_prompt.py       NEW — SystemPromptManager (thin wrapper over
                        PromptRegistry, no new table — §3.2)
  persona_engine.py      NEW — PersonaEngine (§4)
  model_router.py        NEW — ModelRouter (§5, no new table)
  memory_engine.py        NEW — MemoryEngine (§6, no new table)
  prompt_builder.py       NEW — PromptBuilder + AssembledPrompt (§7)
  cost_ledger.py          existing, extended: + prompt_version_id column
                        on CostLedgerEntry (closes the audit's §3 gap
                        for the ModelRegistry call path)
  model_registry.py       unchanged — still the low-level "given a model
                        string, call the right provider" dispatcher;
                        ModelRouter (new) decides *which* string, this
                        decides *how* to call it. Kept as two files on
                        purpose — see §5.
migrations/
  0015_prompt_engine.sql  NEW — every DDL statement in this doc, one file
```

---

## 3. Prompt Registry extension

### 3.1 Schema

Six new columns on the existing `prompt_versions` table:

| Column | Type | Default | Notes |
|---|---|---|---|
| `description` | `text` | `''` | Free text, for an authoring/admin UI. Not currently exposed by `GET /api/ai/prompts` — that route would need to start returning it. |
| `status` | `text` | `'draft'` | `draft \| active \| archived`. **Governs what `add_version(is_active=True)` is allowed to do** — see state machine below. `CHECK (status IN ('draft','active','archived'))`, matching the `UploadJob.status` CHECK precedent (migration 0002). |
| `category` | `text` | `''` | Free-text grouping (e.g. `paper_analysis`, `literature_review`). **Decoupled from `name` on purpose** — today's 7 seeded prompts happen to have `category == name`, which is a coincidence of there being one prompt per task so far, not a rule. A future `paper_analysis_experimental` name could share `category='paper_analysis'` with the original. Not used for lookup (that's still `name`, exact match) — only for filtering/grouping in an admin UI. |
| `examples` | `text` | `'[]'` | JSON array of `{input, output}` pairs, application-serialized (constraint 2). Nothing renders these into the prompt itself — they're documentation/test fixtures for whoever authors the template, not part of `get_prompt()`'s output. |
| `expected_output_type` | `text` | `'text'` | `json \| markdown \| text \| table`. `CHECK` constraint, same pattern. Consumed by the Prompt Builder (§4) to decide whether to append a JSON-schema instruction block, and could later drive response parsing/validation at the call site — not designed here, flagged as a natural next step. |
| `author_user_id` | `integer` | `NULL` | Soft FK to `users.id` (constraint 3) — named `author_user_id`, not `author`, so the cross-Base FK is self-documenting at the column level rather than looking like an oversight. |

**State machine for `status`**: a version can only have `is_active=True`
if `status='active'`. `draft` versions can be created and iterated on
(`add_version`) without ever being served. `archived` means "no longer
eligible to be reactivated without an explicit status change back to
`active` first" — a deliberately stricter retirement than just
`is_active=False`. This is a real behavior change to `add_version()`/
`create_prompt()`, not just new columns — both need a check added:
reject (raise `ValueError`) an attempt to set `is_active=True` on a row
whose `status != 'active'`.

### 3.2 `get_prompt()` signature change

```python
def get_prompt(
    self, name: str, version: Optional[int] = None,
    variables: Optional[dict] = None,
) -> tuple[str, "PromptVersion"]:
    ...
    return rendered_text, row
```

Breaking change (return type goes from `str` to `tuple[str, PromptVersion]`)
— every current caller (`backend/upload/routes.py`, `backend/search/routes.py`)
needs its one line updated: `text = registry.get_prompt(...)` →
`text, prompt_version = registry.get_prompt(...)`. This is the
prerequisite the audit called out for ever populating
`AIUsageLedger.prompt_version_id` or a future `CostLedgerEntry.prompt_version_id`
— without it, no caller has the version id in hand at all.

### 3.3 Migration + SQLite dev parity

`migrations/0015_prompt_engine.sql` (excerpt — full file in §8):

```sql
ALTER TABLE prompt_versions ADD COLUMN IF NOT EXISTS description text NOT NULL DEFAULT '';
ALTER TABLE prompt_versions ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'draft';
ALTER TABLE prompt_versions ADD COLUMN IF NOT EXISTS category text NOT NULL DEFAULT '';
ALTER TABLE prompt_versions ADD COLUMN IF NOT EXISTS examples text NOT NULL DEFAULT '[]';
ALTER TABLE prompt_versions ADD COLUMN IF NOT EXISTS expected_output_type text NOT NULL DEFAULT 'text';
ALTER TABLE prompt_versions ADD COLUMN IF NOT EXISTS author_user_id integer;

DO $$ BEGIN
    ALTER TABLE prompt_versions ADD CONSTRAINT chk_prompt_versions_status
        CHECK (status IN ('draft', 'active', 'archived'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE prompt_versions ADD CONSTRAINT chk_prompt_versions_output_type
        CHECK (expected_output_type IN ('json', 'markdown', 'text', 'table'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE prompt_versions ADD CONSTRAINT fk_prompt_versions_author
        FOREIGN KEY (author_user_id) REFERENCES users(id);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
```

**Required companion change** — `server.py`'s `ensure_columns()` (line
~894 today) needs six more entries, one per new column, e.g.
`"ALTER TABLE prompt_versions ADD COLUMN description TEXT DEFAULT ''"`.
Without this, any developer's existing local `chat_dev.db` (which
already has `prompt_versions` from a prior `create_all()` run) never
gets these columns — `create_all(checkfirst=True)` no-ops on a table
that already exists, exactly the bug class `brain.md` §6 documents for
`UploadJob`/`AIUsageLedger`. SQLite has no `CHECK ... IF NOT EXISTS`
concept and `ensure_columns()` doesn't enforce CHECK constraints today
for any table — that's consistent with the existing pattern (SQLite dev
is intentionally looser than Postgres prod here), not a new gap.

**Existing seeded rows** (the 7 prompts from `backfill.py`/`seed.py`)
get `status='draft'` by column default after this migration, which would
make them **ineligible to stay `is_active=True`** under the new rule in
§3.1 unless something also sets `status='active'` on them. **Required
data migration**: `UPDATE prompt_versions SET status = 'active' WHERE
is_active = true;` — included in `0015_prompt_engine.sql`, not left as a
manual step, since forgetting it would silently break every prompt this
app's real extraction/analysis/RAG code depends on the next time anyone
calls `add_version()` on one of them.

---

## 4. System Prompt Manager

**Recommendation: no new table.** The spec asks for `system_prompts` (id,
content, is_active, created_at, updated_at) with `get_active_prompt()` /
`set_active_prompt()` / `list_prompts()` — structurally this is
`prompt_versions` filtered to one name, minus a `version` number the
caller never asks for. Standing up a second, parallel
versioned-content-with-one-active-row table for a single global string
is the "reinvented standard library" case ponytail's ladder exists to
catch: `PromptRegistry` already does everything this needs.

**Design**: `SystemPromptManager` in `backend/ai/system_prompt.py`,
constructor-injected with a `PromptRegistry` instance, using the fixed
name `"system_prompt"`:

```python
class SystemPromptManager:
    NAME = "system_prompt"
    DEFAULT = "You are a research assistant for a PhD student..."

    def __init__(self, registry: PromptRegistry):
        self.registry = registry

    def get_active_prompt(self) -> str:
        text, _version = self.registry.get_prompt(self.NAME)
        return text

    def set_active_prompt(self, content: str) -> None:
        if self.registry.get_active_version(self.NAME) is None:
            self.registry.create_prompt(
                self.NAME, "Global system prompt", content)
        else:
            self.registry.add_version(self.NAME, content, is_active=True)

    def list_prompts(self) -> list[str]:
        # every historical version's template text, oldest first
        rows = (self.registry.db.query(PromptVersion)
                .filter_by(name=self.NAME).order_by(PromptVersion.version).all())
        return [r.template for r in rows]
```

This gets the exact method names/signatures the spec asked for, a real
default seeded via `seed.py` (`seed_system_prompt()`, one more idempotent
entry alongside `seed_prompts()`), full version history (every
`add_version()` call is already an append, never an overwrite), and adds
**zero new schema**. `list_prompts()` differs slightly from
`PromptRegistry.list_prompts()` (which returns active-only, across all
names) — this one intentionally returns this one name's full history,
since "list the system prompts" most naturally means "show me the
history of the one thing," not "show me the one active row."

If a literal standalone table is still wanted (e.g. a future admin UI
built against a simpler REST shape that shouldn't know
`prompt_versions`/`name` exist at all), it's a straightforward
alternative — schema in the footnote below — but it duplicates
`is_active`-per-row uniqueness enforcement, a second `created_at`
seeding path, and a second thing to keep in sync with §3's status state
machine, for a benefit (hiding that this is "just another named prompt")
that a thin wrapper class already provides.

<details><summary>Alternative: standalone <code>system_prompts</code> table (not recommended)</summary>

```sql
CREATE TABLE IF NOT EXISTS system_prompts (
    id bigserial PRIMARY KEY,
    content text NOT NULL,
    is_active boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_system_prompts_active
    ON system_prompts (is_active) WHERE is_active;
```
</details>

---

## 5. Persona Engine

A real new concept — nothing like this exists today. New table,
`personas`, living under **`prompt_registry.py`'s existing private
`_Base`** (not a new one) specifically so `prompt_executions.persona_id`
(§7) can carry a real `ForeignKey` to it.

### 5.1 Schema

```sql
CREATE TABLE IF NOT EXISTS personas (
    id            bigserial PRIMARY KEY,
    name          text NOT NULL UNIQUE,
    description   text NOT NULL DEFAULT '',
    system_prompt text NOT NULL,
    is_active     boolean NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);
```

**Naming collision to flag explicitly**: `personas.is_active` means
something different from `prompt_versions.is_active`. On
`prompt_versions` it's DB-enforced to be true for exactly one row per
`name` (partial unique index — "the one version currently served").
Here, **many** personas can be `is_active=true` simultaneously — it just
means "offered as a selectable option," a soft enable/disable flag, not
an exclusivity constraint. No partial unique index on this table.
Implementers should not assume the two columns behave the same way just
because they share a name.

### 5.2 `PersonaEngine` (`backend/ai/persona_engine.py`)

```python
class PersonaEngine:
    def __init__(self, db_session, Persona):
        self.db = db_session
        self.Persona = Persona

    def list_active(self) -> list["Persona"]:
        return self.db.query(self.Persona).filter_by(is_active=True).all()

    def get(self, persona_id: int) -> Optional["Persona"]:
        return self.db.get(self.Persona, persona_id)

    def get_by_name(self, name: str) -> Optional["Persona"]:
        return self.db.query(self.Persona).filter_by(name=name).first()

    def create(self, name, description, system_prompt) -> "Persona": ...
    def update(self, persona_id, **fields) -> "Persona": ...  # bumps updated_at
    def deactivate(self, persona_id) -> None: ...              # is_active = False
```

### 5.3 Default personas — seeded via `seed_personas()`

Idempotent by `name`, same convention as `seed_prompts()`. Two fully
worked examples below; the remaining six follow the same shape (one
clear paragraph of role + tone + what NOT to do) and are placeholders to
be filled in by whoever owns prompt quality at implementation time, not
finalized here:

```python
DEFAULT_PERSONAS = {
    "Research Assistant": (
        "You are a meticulous research assistant helping a PhD student. "
        "Prioritize accuracy over confidence — flag uncertainty rather than "
        "guessing. Cite specific papers/sections when referencing evidence. "
        "Default to concise, structured answers over long prose."
    ),
    "Peer Reviewer": (
        "You are a rigorous peer reviewer for an academic venue. Identify "
        "methodological weaknesses, unsupported claims, and missing related "
        "work. Be direct and specific — 'the sample size is too small to "
        "support this conclusion' rather than 'consider strengthening this "
        "section.' Never soften a real flaw to be polite."
    ),
    "Literature Review Expert": "TODO — see Research Assistant for the target tone.",
    "Academic Editor": "TODO",
    "Methodology Advisor": "TODO",
    "Statistician": "TODO",
    "Writing Coach": "TODO",
    "Grant Proposal Advisor": "TODO",
}
```

---

## 6. Model Router

**No new table** — the spec's own component list gives every other
piece a `Table:` line except this one; that silence is a real signal,
not an oversight to fill in. `get_model_for_task`/`set_model_for_task`
map cleanly onto: read from `.env`, override in memory for the life of
the process.

```python
class ModelRouter:
    def __init__(self, default_model: str):
        self.default_model = default_model
        self._overrides: dict[str, str] = {}   # in-memory only

    def get_model_for_task(self, task_name: str) -> str:
        if task_name in self._overrides:
            return self._overrides[task_name]
        env_value = os.environ.get(f"{task_name.upper()}_MODEL")
        if env_value:
            return env_value
        return self.default_model

    def set_model_for_task(self, task_name: str, model_name: str) -> None:
        self._overrides[task_name] = model_name
```

A genuine startup-time singleton (`get_model_router()`), same category
as `CostLedger` — holds no DB session, so one shared instance across
requests is fine; `set_model_for_task` changes are process-lifetime
only, not persisted across a restart or shared across `worker.py`/
`server.py` (two separate processes, two separate in-memory dicts). If
persistence-across-restart turns out to be a real requirement later,
that's a small, separate addition (a `model_routes(task_name PK,
model_name, updated_at)` table) — not designed here because nothing in
the request implies it's needed yet.

**Relationship to the existing `ModelRegistry`** (`model_registry.py`,
unchanged): `ModelRouter` decides *which model string* a task should
use; `ModelRegistry.call(model, messages, ...)` decides *how to actually
call* whatever string it's given (provider dispatch, retries). They
compose — `registry.call(router.get_model_for_task("paper_analysis"), ...)`
— and should stay two files with one responsibility each, not merge.

**Env vars**: reuses the app's existing three-tier fallback
(`DEFAULT_MODEL`/`UTILITY_MODEL`/`EMBED_MODEL`, already seeded into
`ModelVersion` by `backfill.py`) as `ModelRouter`'s own ultimate
fallback rather than inventing a fourth. Concretely: `default_model`
passed into the constructor should be `UTILITY_MODEL` for chat/analysis
tasks and `EMBED_MODEL` for the embedding task specifically — two
`ModelRouter` instances (or one instance with a per-task default),
either works; not fully specified here since it's an implementation
detail, not an architectural one. New task-specific env vars
(`PAPER_ANALYSIS_MODEL`, `CHAT_MODEL`, `EMBEDDING_MODEL`, etc.) are
purely additive — `.env.example` gains new optional lines, nothing
existing changes meaning.

---

## 7. Memory Engine

**No new table** — `Memory` (`server.py`, `memories` table: `user_id`,
`project_id`, `fact`, `importance`, `created_at`) already has everything
this needs, including the `importance` column the spec's own ranking
criteria implicitly wants. This is a query/ranking class, not a storage
layer.

```python
class MemoryEngine:
    def __init__(self, db_session, Memory):
        self.db = db_session
        self.Memory = Memory

    def get_relevant_memories(
        self, user_id: int, query: str, project_id: Optional[int] = None,
        limit: int = 5,
    ) -> list["Memory"]:
        candidates = (
            self.db.query(self.Memory)
            .filter(self.Memory.user_id == user_id)
            .filter(or_(self.Memory.project_id == project_id,
                       self.Memory.project_id.is_(None)))
            .all()
        )
        terms = {t.lower() for t in query.split() if len(t) > 2}

        def keyword_hits(m):
            fact_words = m.fact.lower().split()
            return sum(1 for t in terms if any(t in w for w in fact_words))

        # ponytail: naive token-overlap relevance, no embeddings — good
        # enough at low memory-per-user volumes; upgrade to a Chunk-style
        # stored embedding + cosine rank (same pattern backend/search/
        # routes.py already uses) if this proves too coarse once users
        # accumulate hundreds of memories.
        ranked = sorted(
            candidates,
            key=lambda m: (keyword_hits(m), m.importance, m.created_at),
            reverse=True,
        )
        return ranked[:limit]
```

Project-scoping is inclusive (a project-scoped memory **or** a
global/no-project one), not exclusive — matches how `Memory.project_id`
is already `nullable=True` elsewhere in this schema (a global memory
should still surface inside a project's context). Sort key is a plain
tuple (keyword hits, then importance, then recency) rather than a
weighted formula — simpler to reason about and adjust than tuned
coefficients with no data yet to tune them against.

---

## 8. Prompt Builder

The orchestrator. Constructor-injected with everything else in this doc:

```python
@dataclass
class AssembledPrompt:
    system: str
    persona: str
    project_context: str
    memory: str
    rag: str
    task: str
    output_schema: str
    final: str                      # the concatenation actually sent to the model
    prompt_version_id: Optional[int]  # for Prompt Executions (§9) / cost-ledger attribution
    persona_id: Optional[int]


class PromptBuilder:
    def __init__(self, *, system_prompt_manager, persona_engine,
                memory_engine, prompt_registry, SessionLocal, Project):
        self.system_prompt_manager = system_prompt_manager
        self.persona_engine = persona_engine
        self.memory_engine = memory_engine
        self.prompt_registry = prompt_registry
        self.SessionLocal = SessionLocal
        self.Project = Project

    def build(
        self, *, user_query: str, task_name: str,
        persona: Optional[str] = None,     # persona name or id
        project_id: Optional[int] = None,
        user_id: int,
        rag_context: Optional[str] = None,
        output_schema: Optional[dict] = None,
    ) -> AssembledPrompt:
        system = self.system_prompt_manager.get_active_prompt()

        persona_row = None
        if persona is not None:
            persona_row = (self.persona_engine.get_by_name(persona)
                          if isinstance(persona, str)
                          else self.persona_engine.get(persona))
        persona_text = persona_row.system_prompt if persona_row else ""

        project_context = ""
        if project_id is not None:
            db = self.SessionLocal()
            try:
                project = db.get(self.Project, project_id)
                if project:
                    project_context = "\n".join(
                        s for s in (project.description, project.instructions) if s)
            finally:
                db.close()

        memories = self.memory_engine.get_relevant_memories(
            user_id, user_query, project_id=project_id)
        memory_text = "\n".join(f"- {m.fact}" for m in memories)

        rag_text = rag_context or ""

        task_text, prompt_version = self.prompt_registry.get_prompt(
            task_name, variables={"query": user_query, "text": user_query})

        schema_text = ""
        if output_schema:
            schema_text = ("Respond ONLY with JSON matching this schema:\n"
                          + json.dumps(output_schema, indent=2))

        sections = [
            ("System", system), ("Persona", persona_text),
            ("Project Context", project_context), ("Memory", memory_text),
            ("Retrieved Context", rag_text), ("Task", task_text),
            ("Output Format", schema_text),
        ]
        final = "\n\n".join(f"## {label}\n{body}" for label, body in sections if body)

        return AssembledPrompt(
            system=system, persona=persona_text, project_context=project_context,
            memory=memory_text, rag=rag_text, task=task_text, output_schema=schema_text,
            final=final, prompt_version_id=prompt_version.id,
            persona_id=persona_row.id if persona_row else None,
        )
```

**Where `user_query` actually goes**: the assembly order given
(System → Persona → Project Context → Memory → RAG → Task → Output
Schema) has no standalone "User Query" layer — the design decision made
here is that it's a Jinja2 variable fed into the **Task** layer's own
render call (`variables={"query": user_query, ...}`), since "what the
user is actually asking" is semantically part of "the task to perform,"
not a separate section. This means task prompt templates going forward
should reference `{{ query }}` (today's templates use inconsistent
variable names — `{{ question }}` in `semantic_search`, `{{ text }}` in
`paper_analysis`/`extract_metadata` — converging on one name is a
cleanup for whoever implements this, not required before this design is
usable: `get_prompt()`'s existing `variables` dict can pass multiple
keys, so both old and new variable names can be populated at once
without breaking existing templates).

**Empty sections are omitted** from `final`, not rendered as empty
headers — a call with no persona and no project produces a clean
`System`/`Task` prompt, not four empty section headers.

---

## 9. Prompt Executions (audit trail)

The piece that finally closes the loop the audit flagged: every
assembled prompt gets one row, carrying the exact `prompt_version_id`
`AssembledPrompt` resolved.

```sql
CREATE TABLE IF NOT EXISTS prompt_executions (
    id                bigserial PRIMARY KEY,
    prompt_version_id bigint REFERENCES prompt_versions(id),
    persona_id        bigint REFERENCES personas(id),
    project_id        integer,           -- soft FK -> projects.id, see constraint 3
    user_id           integer NOT NULL,  -- soft FK -> users.id, see constraint 3
    assembled_prompt  text NOT NULL,
    output_schema     text,              -- JSON-as-text, nullable
    tokens_used       integer,
    latency_ms        integer,           -- named _ms, not `latency` — unit ambiguity
                                          -- is a real footgun in a column read
                                          -- by more than one future consumer
    status            text NOT NULL DEFAULT 'pending',
    created_at        timestamptz NOT NULL DEFAULT now()
);

DO $$ BEGIN
    ALTER TABLE prompt_executions ADD CONSTRAINT chk_prompt_executions_status
        CHECK (status IN ('pending', 'success', 'failed'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE prompt_executions ADD CONSTRAINT fk_prompt_executions_project
        FOREIGN KEY (project_id) REFERENCES projects(id);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE prompt_executions ADD CONSTRAINT fk_prompt_executions_user
        FOREIGN KEY (user_id) REFERENCES users(id);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
```

Lives under the same shared private Base as `PromptVersion`/`Persona`
(§2) so `prompt_version_id`/`persona_id` are real, ORM-resolvable FKs —
`project_id`/`user_id` stay plain integers per constraint 3, with the
FK enforced only at the raw-SQL migration level.

**Who writes this row, and when**: not `PromptBuilder.build()` itself —
building a prompt and executing it against a model are different steps
(a caller might build one and never send it, e.g. previewing in an
admin UI). The call site that actually invokes `ModelRegistry.call()`
writes one `prompt_executions` row per call, `status='pending'` before
the call, updated to `success`/`failed` with `tokens_used`/`latency_ms`
filled in after — mirroring how `AIUsageLedger`/`CostLedgerEntry` are
already written today (after the call resolves, at the same call site,
not inside the registry classes themselves).

**Relationship to `CostLedgerEntry`/`AIUsageLedger`**: this table is
**not** a replacement for either — it's the prompt-assembly-level audit
(what was assembled, for whom, using which version), while the two cost
ledgers stay the token/dollar-cost record. The audit's §3 recommendation
(add `prompt_version_id` to `CostLedgerEntry`) is still worth doing
independently — a caller writing a `prompt_executions` row and a
`CostLedgerEntry` row for the same call should be able to join them by
`prompt_version_id`, not just by proximity in time.

---

## 10. Full migration file

`migrations/0015_prompt_engine.sql` — every DDL statement from §3.3, §5.1,
and §9 above, plus the `status` backfill, in one file:

```sql
-- §3: Prompt Registry extension
ALTER TABLE prompt_versions ADD COLUMN IF NOT EXISTS description text NOT NULL DEFAULT '';
ALTER TABLE prompt_versions ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'draft';
ALTER TABLE prompt_versions ADD COLUMN IF NOT EXISTS category text NOT NULL DEFAULT '';
ALTER TABLE prompt_versions ADD COLUMN IF NOT EXISTS examples text NOT NULL DEFAULT '[]';
ALTER TABLE prompt_versions ADD COLUMN IF NOT EXISTS expected_output_type text NOT NULL DEFAULT 'text';
ALTER TABLE prompt_versions ADD COLUMN IF NOT EXISTS author_user_id integer;

DO $$ BEGIN
    ALTER TABLE prompt_versions ADD CONSTRAINT chk_prompt_versions_status
        CHECK (status IN ('draft', 'active', 'archived'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE prompt_versions ADD CONSTRAINT chk_prompt_versions_output_type
        CHECK (expected_output_type IN ('json', 'markdown', 'text', 'table'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE prompt_versions ADD CONSTRAINT fk_prompt_versions_author
        FOREIGN KEY (author_user_id) REFERENCES users(id);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Existing seeded prompts predate `status` — without this they'd be
-- is_active=true with status='draft', which the new state machine (§3.1)
-- treats as invalid.
UPDATE prompt_versions SET status = 'active' WHERE is_active = true;

-- §5: Persona Engine
CREATE TABLE IF NOT EXISTS personas (
    id            bigserial PRIMARY KEY,
    name          text NOT NULL UNIQUE,
    description   text NOT NULL DEFAULT '',
    system_prompt text NOT NULL,
    is_active     boolean NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

-- §9: Prompt Executions
CREATE TABLE IF NOT EXISTS prompt_executions (
    id                bigserial PRIMARY KEY,
    prompt_version_id bigint REFERENCES prompt_versions(id),
    persona_id        bigint REFERENCES personas(id),
    project_id        integer,
    user_id           integer NOT NULL,
    assembled_prompt  text NOT NULL,
    output_schema     text,
    tokens_used       integer,
    latency_ms        integer,
    status            text NOT NULL DEFAULT 'pending',
    created_at        timestamptz NOT NULL DEFAULT now()
);

DO $$ BEGIN
    ALTER TABLE prompt_executions ADD CONSTRAINT chk_prompt_executions_status
        CHECK (status IN ('pending', 'success', 'failed'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE prompt_executions ADD CONSTRAINT fk_prompt_executions_project
        FOREIGN KEY (project_id) REFERENCES projects(id);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE prompt_executions ADD CONSTRAINT fk_prompt_executions_user
        FOREIGN KEY (user_id) REFERENCES users(id);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
```

Optional, separate: the audit's §3 recommendation to add
`prompt_version_id` to `model_registry_cost_ledger` — left out of
`0015` since it's an independent decision (§9), not required for
anything else in this doc to work; would be its own
`0016_cost_ledger_prompt_attribution.sql` if/when actioned.

---

## 11. Integration points — how existing callers adopt this

No flag day required; each is a small, local change:

- **`backend/upload/routes.py`'s `analyze_document()`** — today calls
  `prompt_registry.get_prompt("paper_analysis", variables=...)` directly.
  Switching to `PromptBuilder.build(task_name="paper_analysis", ...)`
  is optional, not required — the two-value return from `get_prompt()`
  (§3.2) is the one change this call site *must* make regardless of
  whether it adopts the full builder.
- **`backend/search/routes.py`'s `rag_answer()`** — the most natural
  first real caller of the full `PromptBuilder`: it already computes
  `rag_context` (the retrieved chunk text) and has `user_id`/`project_id`
  in hand; swapping its direct `prompt_registry.get_prompt("semantic_search",
  ...)` + `model_registry.call(...)` for `builder.build(task_name="semantic_search",
  rag_context=documents_text, ...)` + `model_registry.call(router.get_model_for_task("semantic_search"), ...)`
  is a same-shape replacement, not a rewrite of the route.
- **`/api/chat`** (`server.py`, the legacy path) — out of scope for this
  design. It doesn't use `PromptRegistry`/`ModelRegistry` today
  (`responses_text()` is a separate, OpenAI-only call path per the
  audit) and bringing it onto this stack is a bigger, separate migration
  that would touch the streaming response handling — not attempted here.

---

## 12. Suggested build order

Dependency order, not priority order — each step is usable on its own
once its dependencies exist:

1. §3 (Prompt Registry extension + `get_prompt()` signature change) —
   everything else reads/writes `prompt_versions` or depends on the new
   return shape.
2. §5 (Persona Engine) and §7 (Memory Engine) — independent of each
   other and of §3 beyond the shared migration file.
3. §4 (System Prompt Manager) and §6 (Model Router) — thin, no
   dependencies beyond `PromptRegistry` (already extended in step 1).
4. §8 (Prompt Builder) — depends on 1–3 all existing.
5. §9 (Prompt Executions) — depends on §8 (needs `AssembledPrompt` to
   have something to log) and can be wired into one real call site
   (`backend/search/routes.py`, per §11) as the first integration,
   proving the whole stack end-to-end before touching anything else.
