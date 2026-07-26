-- Phase 2: persist Phase 1.1–1.7 pipeline outputs per document (UserFile).
-- Lazy migration: existing files get a row only when first analyzed.

CREATE TABLE IF NOT EXISTS analysis_pipeline_results (
    id SERIAL PRIMARY KEY,
    file_id INTEGER NOT NULL UNIQUE REFERENCES files(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    content_hash VARCHAR(64) DEFAULT '',
    status VARCHAR(20) DEFAULT 'pending',
    error TEXT DEFAULT '',
    phase_results TEXT NOT NULL DEFAULT '{}',
    pipeline_version VARCHAR(50) DEFAULT '',
    total_processing_time_ms INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_pipeline_results_user
    ON analysis_pipeline_results(user_id);

-- Allow longer job_type values (phase1_analysis)
ALTER TABLE upload_jobs ALTER COLUMN job_type TYPE VARCHAR(40);
