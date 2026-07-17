-- Transactional outbox: aggregate_id is polymorphic (aggregate_type says
-- which table it points into) — Postgres can't express a conditional FK
-- across multiple target tables, so there is deliberately no FK here.
-- Integrity is enforced by the writer (always insert in the same
-- transaction as the aggregate change it's recording), not the schema.
CREATE TABLE outbox_events (
    id             bigserial PRIMARY KEY,
    aggregate_type text NOT NULL,
    aggregate_id   bigint NOT NULL,
    event_type     text NOT NULL,
    payload        jsonb NOT NULL,
    status         text NOT NULL DEFAULT 'pending',
    dispatched_at  timestamptz,
    created_at     timestamptz NOT NULL DEFAULT now()
);

-- Relay poll query — the same FOR UPDATE SKIP LOCKED pattern as upload_jobs.
CREATE INDEX ix_outbox_events_pending
    ON outbox_events (status, created_at) WHERE status = 'pending';
