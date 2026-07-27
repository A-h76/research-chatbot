-- Phase 1.5: library search indexes (title, author, doi, year, created)

CREATE INDEX IF NOT EXISTS ix_files_user_created ON files (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_files_user_year ON files (user_id, year);
CREATE INDEX IF NOT EXISTS ix_files_user_reading ON files (user_id, reading_status);
CREATE INDEX IF NOT EXISTS ix_files_user_meta ON files (user_id, meta_status);
CREATE INDEX IF NOT EXISTS ix_files_user_doi ON files (user_id, doi);
