-- Append-only cost/usage record. upload_job_id is ON DELETE SET NULL, not
-- CASCADE: a financial/audit row must outlive the job (and transitively
-- the file) it was charged against — deleting either must never erase
-- the fact that the API call, and its cost, actually happened.
CREATE TABLE ai_usage_ledger (
    id                bigserial PRIMARY KEY,
    user_id           integer NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    upload_job_id     bigint REFERENCES upload_jobs(id) ON DELETE SET NULL,
    kind              text NOT NULL,
    model_version_id  bigint NOT NULL REFERENCES model_versions(id),
    prompt_version_id bigint REFERENCES prompt_versions(id),
    prompt_tokens     integer NOT NULL DEFAULT 0,
    completion_tokens integer NOT NULL DEFAULT 0,
    cost_usd          numeric(10, 6) NOT NULL DEFAULT 0,
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ix_ai_usage_ledger_user ON ai_usage_ledger (user_id, created_at DESC);
CREATE INDEX ix_ai_usage_ledger_model ON ai_usage_ledger (model_version_id);
