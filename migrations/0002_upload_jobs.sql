-- One row per pipeline stage per file (import | extract_metadata |
-- paper_analysis | ...). file_id and upload_batch_id are ON DELETE SET
-- NULL, not CASCADE: a job row is an audit/history record — deleting the
-- file or batch it belonged to must not erase that history, only its
-- link to it.
CREATE TABLE IF NOT EXISTS upload_jobs (
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

-- Backfill for the case where server.py's own Base.metadata.create_all()
-- created this table first, from an UploadJob ORM class that (until
-- fixed alongside this) didn't declare locked_by/locked_at/
-- pipeline_version_id or the status CHECK — CREATE TABLE IF NOT EXISTS
-- above is then a no-op and can't add what's missing from an
-- already-existing table. Verified for real: this is exactly the second
-- failure run_migrations.py hit once the "already exists" errors were
-- fixed, not a hypothetical.
ALTER TABLE upload_jobs ADD COLUMN IF NOT EXISTS locked_by text;
ALTER TABLE upload_jobs ADD COLUMN IF NOT EXISTS locked_at timestamptz;
ALTER TABLE upload_jobs ADD COLUMN IF NOT EXISTS pipeline_version_id bigint;

DO $$ BEGIN
    ALTER TABLE upload_jobs ADD CONSTRAINT chk_upload_jobs_status
        CHECK (status IN ('pending', 'running', 'done', 'failed'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Worker poll query (FOR UPDATE SKIP LOCKED) — the single most important
-- index on this table.
CREATE INDEX IF NOT EXISTS ix_upload_jobs_pending
    ON upload_jobs (status, run_after) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS ix_upload_jobs_file ON upload_jobs (file_id);
CREATE INDEX IF NOT EXISTS ix_upload_jobs_batch ON upload_jobs (upload_batch_id);
CREATE INDEX IF NOT EXISTS ix_upload_jobs_user_status ON upload_jobs (user_id, status);
