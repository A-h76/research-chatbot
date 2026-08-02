-- Entitlement usage ledger enrichment (#13 Quotas)
ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS operation VARCHAR(60) DEFAULT '';
ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS project_id INTEGER;
ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS detail_json TEXT DEFAULT '{}';

CREATE INDEX IF NOT EXISTS ix_usage_logs_operation
    ON usage_logs (operation, created_at);
