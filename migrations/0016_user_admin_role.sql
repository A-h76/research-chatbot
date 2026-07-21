-- Admin role for the Prompt Engine's create/update routes
-- (docs/prompt-engine-architecture.md; backend/prompts/routes.py). Plain
-- boolean, default false — no existing user starts as an admin; the
-- first one is set manually (UPDATE users SET is_admin = true WHERE
-- email = '...'), same bootstrap pattern most systems use for the very
-- first admin account. No self-service "become admin" path exists
-- anywhere, by design.
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin boolean NOT NULL DEFAULT false;
