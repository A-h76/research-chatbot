-- Groups files uploaded together in one user action.
CREATE TABLE upload_batches (
    id              bigserial PRIMARY KEY,
    user_id         integer NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id      integer REFERENCES projects(id) ON DELETE SET NULL,
    conversation_id integer REFERENCES conversations(id) ON DELETE SET NULL,
    source          text NOT NULL DEFAULT 'library',
    file_count      integer NOT NULL DEFAULT 0,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ix_upload_batches_user ON upload_batches (user_id, created_at DESC);
