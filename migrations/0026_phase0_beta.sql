-- Phase 0: closed-beta validation metrics (returning users)

ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;
