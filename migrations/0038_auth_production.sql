-- Production auth: structured onboarding + email-change tokens
ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_completed_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS research_role VARCHAR(40);
ALTER TABLE users ADD COLUMN IF NOT EXISTS research_fields TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS institution VARCHAR(200);
ALTER TABLE users ADD COLUMN IF NOT EXISTS research_goal VARCHAR(40);
ALTER TABLE users ADD COLUMN IF NOT EXISTS experience_level VARCHAR(20);

-- Legacy blob from earlier draft (safe no-op if never created)
ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_json TEXT;

CREATE TABLE IF NOT EXISTS email_change_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    new_email VARCHAR(320) NOT NULL,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_email_change_tokens_user ON email_change_tokens (user_id);
CREATE INDEX IF NOT EXISTS ix_users_research_role ON users (research_role);
CREATE INDEX IF NOT EXISTS ix_users_research_goal ON users (research_goal);
