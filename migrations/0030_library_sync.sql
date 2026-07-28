-- Phase 1b: Library incremental sync + external item identity + PDF attach support

ALTER TABLE library_connections ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ;
ALTER TABLE library_connections ADD COLUMN IF NOT EXISTS sync_cursor TEXT DEFAULT '';

ALTER TABLE files ADD COLUMN IF NOT EXISTS external_provider VARCHAR(30) DEFAULT '';
ALTER TABLE files ADD COLUMN IF NOT EXISTS external_item_id VARCHAR(120) DEFAULT '';

CREATE INDEX IF NOT EXISTS ix_files_user_external
    ON files (user_id, external_provider, external_item_id);

CREATE TABLE IF NOT EXISTS library_sync_runs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    connection_id INTEGER,
    provider VARCHAR(30) NOT NULL,
    status VARCHAR(20) DEFAULT 'running',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    created_count INTEGER DEFAULT 0,
    updated_count INTEGER DEFAULT 0,
    skipped_count INTEGER DEFAULT 0,
    conflict_count INTEGER DEFAULT 0,
    cursor_before TEXT DEFAULT '',
    cursor_after TEXT DEFAULT '',
    error_text TEXT DEFAULT '',
    detail_json TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS ix_library_sync_runs_user
    ON library_sync_runs (user_id, started_at DESC);

CREATE INDEX IF NOT EXISTS ix_library_sync_runs_connection
    ON library_sync_runs (connection_id, started_at DESC);
