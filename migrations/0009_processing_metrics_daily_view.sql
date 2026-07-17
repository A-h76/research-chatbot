-- Rollup over upload_jobs — a materialized view, not a hand-maintained
-- table, because every field it needs already exists on upload_jobs; a
-- separate table would just be a second write path that can drift from
-- the source. Refresh with:
--   REFRESH MATERIALIZED VIEW CONCURRENTLY processing_metrics_daily;
-- (CONCURRENTLY requires the unique index below.)
CREATE MATERIALIZED VIEW processing_metrics_daily AS
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

CREATE UNIQUE INDEX ix_processing_metrics_daily
    ON processing_metrics_daily (bucket_date, job_type);
