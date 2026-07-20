-- How each account was first created — 'google' | 'magic' | 'dev'. The
-- DEFAULT applies to existing rows too (all of which were created via
-- Google OAuth, the only method that existed before this migration).
ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_provider varchar(20) NOT NULL DEFAULT 'google';
