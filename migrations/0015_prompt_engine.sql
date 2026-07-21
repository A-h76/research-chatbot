-- Prompt Engine schema — see docs/prompt-engine-architecture.md for the
-- full design this implements (§3, §5, §9, §10). Every statement here is
-- idempotent per this project's own convention: CREATE TABLE/INDEX IF NOT
-- EXISTS, ADD COLUMN IF NOT EXISTS, and DO $$ ... EXCEPTION WHEN
-- duplicate_object THEN NULL END $$ for constraints (Postgres has no ADD
-- CONSTRAINT IF NOT EXISTS — confirmed a syntax error, same finding
-- migration 0005 already made for fk_upload_jobs_pipeline_version).

-- ────────────────────────────────────────────────────────────────────────
-- Prompt Registry extension: authoring metadata on the existing
-- prompt_versions table (migration 0005).
-- ────────────────────────────────────────────────────────────────────────
ALTER TABLE prompt_versions ADD COLUMN IF NOT EXISTS description text NOT NULL DEFAULT '';
ALTER TABLE prompt_versions ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'draft';
ALTER TABLE prompt_versions ADD COLUMN IF NOT EXISTS category text NOT NULL DEFAULT '';
ALTER TABLE prompt_versions ADD COLUMN IF NOT EXISTS examples text NOT NULL DEFAULT '[]';
ALTER TABLE prompt_versions ADD COLUMN IF NOT EXISTS expected_output_type text NOT NULL DEFAULT 'text';
-- Soft FK: prompt_versions lives under backend/ai's own private Base,
-- users under server.py's — no SQLAlchemy-level ForeignKey can span the
-- two (same reason CostLedgerEntry.user_id has none), so this is a plain
-- column with the real constraint added below, same pattern as
-- ai_usage_ledger.prompt_version_id (migration 0006).
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

CREATE INDEX IF NOT EXISTS ix_prompt_versions_status ON prompt_versions (status);
CREATE INDEX IF NOT EXISTS ix_prompt_versions_category ON prompt_versions (category);

-- Data migration, not optional: existing seeded prompts (backfill.py,
-- seed.py) predate `status` and would otherwise land as
-- is_active=true, status='draft' — invalid under the new rule that only
-- status='active' rows may be is_active=true (see design doc §3.1).
-- Skipping this silently breaks every prompt this app's real
-- extraction/analysis/RAG code depends on the next time anyone calls
-- add_version() on one of them.
UPDATE prompt_versions SET status = 'active' WHERE is_active = true;

-- ────────────────────────────────────────────────────────────────────────
-- Persona Engine — new table. Deliberately no ORM class/factory wired up
-- in this change (schema only, see docs/prompt-engine-architecture.md
-- §12 build order — Python classes are a separate, later step); the
-- table needs to exist before anything can be built on top of it.
-- ────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS personas (
    id            bigserial PRIMARY KEY,
    name          text NOT NULL UNIQUE,
    description   text NOT NULL DEFAULT '',
    system_prompt text NOT NULL,
    -- Not the same constraint as prompt_versions.is_active: many personas
    -- can be is_active=true at once (it just means "selectable"), no
    -- partial-unique-per-name index here on purpose.
    is_active     boolean NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

-- ────────────────────────────────────────────────────────────────────────
-- Prompt Executions — audit trail. prompt_version_id/persona_id are real
-- FKs (both targets end up in the same private-Base MetaData once the
-- ORM classes land — see design doc §2); project_id/user_id are soft FKs
-- for the same cross-Base reason as prompt_versions.author_user_id above.
-- ────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS prompt_executions (
    id                bigserial PRIMARY KEY,
    prompt_version_id bigint REFERENCES prompt_versions(id),
    persona_id        bigint REFERENCES personas(id),
    project_id        integer,
    user_id           integer NOT NULL,
    assembled_prompt  text NOT NULL,
    output_schema     text,              -- JSON-as-text, nullable (matches
                                          -- this schema's existing
                                          -- JSON-as-Text convention:
                                          -- UserFile.tags, OutboxEvent.payload,
                                          -- ModelPreset.config)
    tokens_used       integer,
    latency_ms        integer,           -- explicit unit in the name, not
                                          -- bare `latency` — ambiguous units
                                          -- on a column more than one future
                                          -- consumer will read is a real
                                          -- footgun worth one extra word
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

CREATE INDEX IF NOT EXISTS ix_prompt_executions_created_at ON prompt_executions (created_at);
CREATE INDEX IF NOT EXISTS ix_prompt_executions_user ON prompt_executions (user_id);
CREATE INDEX IF NOT EXISTS ix_prompt_executions_project ON prompt_executions (project_id);

-- ────────────────────────────────────────────────────────────────────────
-- Cost-ledger prompt attribution — the audit's other open gap
-- (prompt-engine-audit.md §3): CostLedgerEntry (model_registry_cost_ledger)
-- has no way at all to attribute a ModelRegistry-path call to a prompt
-- version, not even a dead column like ai_usage_ledger already has. Not
-- optional per this task's own brief. Same soft-FK treatment as above —
-- model_registry_cost_ledger lives under model_registry.py's own private
-- Base, a third registry distinct from both server.py's and
-- prompt_registry.py's.
-- ────────────────────────────────────────────────────────────────────────
ALTER TABLE model_registry_cost_ledger ADD COLUMN IF NOT EXISTS prompt_version_id bigint;

DO $$ BEGIN
    ALTER TABLE model_registry_cost_ledger ADD CONSTRAINT fk_cost_ledger_prompt_version
        FOREIGN KEY (prompt_version_id) REFERENCES prompt_versions(id);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ────────────────────────────────────────────────────────────────────────
-- projects.instructions — found missing while checking this table per
-- this task's own instruction: the ORM class (server.py's Project,
-- `instructions = Column(Text, default="")`) has had this column for a
-- while and it's actively read/written throughout server.py (chat prompt
-- assembly, project CRUD routes) — but no migration anywhere ever created
-- it, and it's not in ensure_columns() either. A real, previously
-- undocumented gap: any Postgres deployment whose `projects` table was
-- first created before this column was added to the ORM class has been
-- missing it with no migration path to fix it until now.
-- ────────────────────────────────────────────────────────────────────────
ALTER TABLE projects ADD COLUMN IF NOT EXISTS instructions text;
