-- Per-user quota limits on users — current usage is NOT duplicated here.
-- Storage usage already lives in storage_usage.bytes_used (0004); only
-- the per-user *limit* is new (today's check is one global env var).
-- Token usage has no existing running total anywhere (ai_usage_ledger,
-- 0006, is per-call detail, not an aggregate) — all three token columns
-- are genuinely new.
ALTER TABLE users ADD COLUMN storage_limit_bytes bigint NOT NULL DEFAULT 1000000000;
ALTER TABLE users ADD COLUMN monthly_token_used integer NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN monthly_token_limit integer NOT NULL DEFAULT 100000;
ALTER TABLE users ADD COLUMN quota_reset_at timestamptz;

-- Coarse, generic quota-consumption audit trail — see quotas/models.py
-- for how this differs from (and doesn't duplicate) ai_usage_ledger.
CREATE TABLE usage_logs (
    id         bigserial PRIMARY KEY,
    user_id    integer NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action     text NOT NULL,
    amount     integer DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ix_usage_logs_user ON usage_logs (user_id, created_at);
