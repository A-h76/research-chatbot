-- Per-user quota limits on users — current usage is NOT duplicated here.
-- Storage usage already lives in storage_usage.bytes_used (0004); only
-- the per-user *limit* is new (today's check is one global env var).
-- Token usage has no existing running total anywhere (ai_usage_ledger,
-- 0006, is per-call detail, not an aggregate) — all three token columns
-- are genuinely new.
ALTER TABLE users ADD COLUMN IF NOT EXISTS storage_limit_bytes bigint NOT NULL DEFAULT 1000000000;
ALTER TABLE users ADD COLUMN IF NOT EXISTS monthly_token_used integer NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS monthly_token_limit integer NOT NULL DEFAULT 100000;
ALTER TABLE users ADD COLUMN IF NOT EXISTS quota_reset_at timestamptz;

-- Coarse, generic quota-consumption audit trail — see quotas/models.py
-- for how this differs from (and doesn't duplicate) ai_usage_ledger.
-- server.py registers UsageLog via quotas.create_usage_log_model(Base),
-- so this table (like the others in this file) is also created by
-- Base.metadata.create_all() before this migration ever gets a chance to.
CREATE TABLE IF NOT EXISTS usage_logs (
    id         bigserial PRIMARY KEY,
    user_id    integer NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action     text NOT NULL,
    amount     integer DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_usage_logs_user ON usage_logs (user_id, created_at);
