-- Closed-beta security & ops layer:
-- user lifecycle, plans, session revoke, invites, security_events,
-- system_settings (AI kill switch + daily budget), cost estimate columns.

-- ── users ──────────────────────────────────────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'active';
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS plan VARCHAR(30) DEFAULT 'beta';
ALTER TABLE users ADD COLUMN IF NOT EXISTS session_version INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS monthly_cost_used DOUBLE PRECISION DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS monthly_cost_limit DOUBLE PRECISION DEFAULT 3.0;

-- Backfill: existing Google/magic accounts are verified + active
UPDATE users
SET email_verified = TRUE,
    email_verified_at = COALESCE(email_verified_at, NOW()),
    status = COALESCE(NULLIF(status, ''), 'active')
WHERE email_verified IS DISTINCT FROM TRUE
   OR status IS NULL
   OR status = '';

-- ── system_settings (AI kill switch, daily budget, …) ─────────────────────
CREATE TABLE IF NOT EXISTS system_settings (
    key         VARCHAR(80) PRIMARY KEY,
    value       TEXT NOT NULL DEFAULT '',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by  INTEGER
);

INSERT INTO system_settings (key, value) VALUES
    ('ai_disabled', '0'),
    ('daily_ai_budget_usd', '10'),
    ('daily_ai_spend_usd', '0'),
    ('daily_ai_spend_date', '')
ON CONFLICT (key) DO NOTHING;

-- ── security_events (critical actions only) ───────────────────────────────
CREATE TABLE IF NOT EXISTS security_events (
    id          BIGSERIAL PRIMARY KEY,
    event       VARCHAR(80) NOT NULL,
    user_id     INTEGER,
    detail      TEXT NOT NULL DEFAULT '{}',
    ip          VARCHAR(64) DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_security_events_created
    ON security_events (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_security_events_event
    ON security_events (event, created_at DESC);

-- ── invite tokens (closed beta) ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS invite_tokens (
    id          SERIAL PRIMARY KEY,
    token_hash  VARCHAR(64) NOT NULL UNIQUE,
    email       VARCHAR(320) NOT NULL,
    created_by  INTEGER,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_invite_tokens_email ON invite_tokens (email);

-- ── email verification / password reset (password-auth foundations) ───────
CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    token_hash  VARCHAR(64) NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    token_hash  VARCHAR(64) NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── cost ledger: estimated vs actual ──────────────────────────────────────
ALTER TABLE model_registry_cost_ledger
    ADD COLUMN IF NOT EXISTS estimated_cost DOUBLE PRECISION;
ALTER TABLE model_registry_cost_ledger
    ADD COLUMN IF NOT EXISTS currency VARCHAR(8) DEFAULT 'USD';
