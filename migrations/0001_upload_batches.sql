-- Groups files uploaded together in one user action.
--
-- IF NOT EXISTS on every statement in this file (and every other
-- migration): server.py's own Base.metadata.create_all(), which runs
-- unconditionally on every startup, already creates this exact table
-- (UploadBatch is a real ORM class) — in the only order this schema's FK
-- dependencies actually allow (server.py must run at least once before
-- users/projects/conversations exist for any migration to reference),
-- server.py always gets here first in practice. Without IF NOT EXISTS,
-- run_migrations.py fails outright on "relation already exists" — this
-- was verified for real against a live Postgres instance, not assumed.
CREATE TABLE IF NOT EXISTS upload_batches (
    id              bigserial PRIMARY KEY,
    user_id         integer NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id      integer REFERENCES projects(id) ON DELETE SET NULL,
    conversation_id integer REFERENCES conversations(id) ON DELETE SET NULL,
    source          text NOT NULL DEFAULT 'library',
    file_count      integer NOT NULL DEFAULT 0,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_upload_batches_user ON upload_batches (user_id, created_at DESC);
