-- Resumable checkpoint for a long-running import. ON DELETE CASCADE here
-- (unlike upload_jobs' ON DELETE SET NULL FKs above): a session is
-- meaningless without its job — it's a checkpoint FOR that job, not an
-- independent audit record.
CREATE TABLE import_sessions (
    id            bigserial PRIMARY KEY,
    upload_job_id bigint NOT NULL UNIQUE REFERENCES upload_jobs(id) ON DELETE CASCADE,
    stage         text NOT NULL DEFAULT 'extract',
    checkpoint    jsonb NOT NULL DEFAULT '{}',
    updated_at    timestamptz NOT NULL DEFAULT now()
);
