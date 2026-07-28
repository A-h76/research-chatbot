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

-- Widen job_type for phase1_analysis. processing_metrics_daily (0009) depends
-- on upload_jobs.job_type, so drop the matview first, alter, then recreate.
DROP MATERIALIZED VIEW IF EXISTS processing_metrics_daily CASCADE;

ALTER TABLE upload_jobs ALTER COLUMN job_type TYPE VARCHAR(40);

CREATE MATERIALIZED VIEW IF NOT EXISTS processing_metrics_daily AS
SELECT
    date_trunc('day', created_at)                      AS bucket_date,
    job_type,
    count(*)                                           AS jobs_count,
    count(*) FILTER (WHERE status = 'done')             AS success_count,
    count(*) FILTER (WHERE status = 'failed')            AS failure_count,
    avg(extract(epoch FROM (finished_at - started_at)) * 1000)
        FILTER (WHERE finished_at IS NOT NULL)          AS avg_duration_ms
FROM upload_jobs
GROUP BY 1, 2;

CREATE UNIQUE INDEX IF NOT EXISTS ix_processing_metrics_daily
    ON processing_metrics_daily (bucket_date, job_type);
