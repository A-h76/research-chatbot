-- model_presets: named chat-call parameter presets (model + temperature +
-- max_tokens), e.g. "gpt-4o-chat" -> {"model": "gpt-4o", "temperature": 0.7,
-- "max_tokens": 2000}. Seeded by backend/ai/seed.py's seed_pipelines().
--
-- Deliberately NOT prompt_templates/model_pipelines (the names originally
-- requested for this migration): prompt_templates was checked against the
-- real schema and doesn't exist anywhere in this codebase by design — 0005
-- already defines prompt_versions as one flat table (rows grouped by a
-- plain `name` column, not a parent/child pair) — and "model_pipelines" is
-- already covered by 0005's model_versions + pipeline_versions, under
-- names chosen deliberately there. This table is a different, genuinely
-- new concept: a named preset of raw call parameters, not a versioned
-- model/prompt/pipeline registry entry. It had no migration until now —
-- backend/ai/seed.py's own _ensure_model_presets_table() created it
-- ad hoc (checkfirst) for local SQLite dev; this is the real, tracked
-- migration for Postgres/production.
--
-- config stored as text (JSON, application-serialized), not jsonb —
-- matching backend/ai/seed.py's ModelPreset ORM column type exactly
-- (Text, not JSON/JSONB), the same "JSON-as-text" convention already used
-- for UserFile.tags/OutboxEvent.payload/ImportSession.checkpoint. Using
-- jsonb here while the ORM declares Text would be a real migration/ORM
-- type mismatch, not just a style inconsistency.
-- UNIQUE (name) already creates its own index in Postgres — no separate
-- CREATE INDEX on the same single column, that would just be a second,
-- redundant index doing nothing the constraint's own doesn't already do.
--
-- IF NOT EXISTS, unlike every other migration in this folder (plain
-- CREATE TABLE) — deliberate, not copy-paste drift: tested for real
-- against a live Postgres instance and found that server.py's own
-- Base.metadata.create_all(engine) (line 750, runs unconditionally on
-- every startup) already creates several tables migrations 0001, 0002,
-- 0004, 0005, and 0006 also try to create with a bare CREATE TABLE — so
-- run_migrations.py currently fails on the very first migration in the
-- only order this schema's own FK dependencies allow (server.py must
-- run before run_migrations.py can, since 0001 needs users/projects/
-- conversations, which only server.py's bootstrap creates — but by then
-- server.py has already created upload_batches itself). model_presets
-- has no such FK dependency and backend/ai/seed.py can independently
-- pre-create it (its own checkfirst-based _ensure_model_presets_table)
-- — IF NOT EXISTS is what keeps THIS migration safe against that same
-- collision class, verified by applying it twice in a row.
CREATE TABLE IF NOT EXISTS model_presets (
    id         bigserial PRIMARY KEY,
    name       text NOT NULL,
    config     text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (name)
);
