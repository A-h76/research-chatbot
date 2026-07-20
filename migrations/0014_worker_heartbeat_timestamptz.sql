-- Fixes worker_heartbeats.last_seen_at's actual column type on any
-- database where it was already created by server.py's own
-- Base.metadata.create_all() before this fix — that bootstrap ran the
-- ORM's old Column(DateTime) (no timezone=True), producing a real
-- Postgres "timestamp without time zone" column even though
-- 0013_worker_heartbeat.sql's own CREATE TABLE IF NOT EXISTS always
-- declared timestamptz (create_all runs first per the FK-ordering
-- constraint documented throughout this project, so its type wins on a
-- table this new — 0013 was a no-op against an already-created table).
--
-- Verified live: a naive TIMESTAMP column silently shifts a UTC-aware
-- write to the Postgres session's timezone before storing it (Asia/
-- Karachi, UTC+5, on the box this was found on), then GET
-- /api/worker/health re-reads that shifted wall-clock value and treats
-- it as UTC again — a consistent 5-hour skew, surfaced as a negative
-- age_seconds. USING ... AT TIME ZONE 'UTC' reinterprets the existing
-- (already-wrong, about to be overwritten within one poll interval
-- anyway) value as UTC rather than the session zone, since the
-- alternative — an implicit cast — would repeat the exact same mistake
-- this migration exists to fix.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'worker_heartbeats'
          AND column_name = 'last_seen_at'
          AND data_type = 'timestamp without time zone'
    ) THEN
        ALTER TABLE worker_heartbeats
            ALTER COLUMN last_seen_at TYPE timestamptz
            USING last_seen_at AT TIME ZONE 'UTC';
    END IF;
END $$;
