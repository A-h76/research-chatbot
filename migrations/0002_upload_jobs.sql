-- One row per pipeline stage per file (import | extract_metadata |
-- paper_analysis | ...). file_id and upload_batch_id are ON DELETE SET
-- NULL, not CASCADE: a job row is an audit/history record — deleting the
-- file or batch it belonged to must not erase that history, only its
-- link to it.
CREATE TABLE upload_jobs (
    id                  bigserial PRIMARY KEY,
    upload_batch_id     bigint REFERENCES upload_batches(id) ON DELETE SET NULL,
    file_id             integer REFERENCES files(id) ON DELETE SET NULL,
    -- Unlike file_id/upload_batch_id above, user_id is this row's OWNER,
    -- not a cross-reference to another entity — it cascades on user
    -- delete (purge with the account) the same way ai_usage_ledger.user_id
    -- does in 0006, rather than surviving with a nulled owner.
    user_id             integer NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_type            text NOT NULL,
    status              text NOT NULL DEFAULT 'pending',
    attempts            integer NOT NULL DEFAULT 0,
    run_after           timestamptz NOT NULL DEFAULT now(),
    locked_by           text,
    locked_at           timestamptz,
    last_error          text,
    -- References pipeline_versions(id), created in 0005 — added as a
    -- plain column here and given its FK constraint at the end of 0005
    -- once that table exists, rather than reordering these migrations.
    pipeline_version_id bigint,
    started_at          timestamptz,
    finished_at         timestamptz,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chk_upload_jobs_status
        CHECK (status IN ('pending', 'running', 'done', 'failed'))
);

-- Worker poll query (FOR UPDATE SKIP LOCKED) — the single most important
-- index on this table.
CREATE INDEX ix_upload_jobs_pending
    ON upload_jobs (status, run_after) WHERE status = 'pending';
CREATE INDEX ix_upload_jobs_file ON upload_jobs (file_id);
CREATE INDEX ix_upload_jobs_batch ON upload_jobs (upload_batch_id);
CREATE INDEX ix_upload_jobs_user_status ON upload_jobs (user_id, status);
