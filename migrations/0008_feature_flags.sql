-- user_id NULL = global default; a per-user row overrides it.
-- Postgres treats NULL <> NULL, so a single UNIQUE(flag_name, user_id)
-- would let the same global flag be inserted twice — split into two
-- partial unique indexes instead, one per case.
CREATE TABLE IF NOT EXISTS feature_flags (
    id          bigserial PRIMARY KEY,
    flag_name   text NOT NULL,
    enabled     boolean NOT NULL DEFAULT false,
    user_id     integer REFERENCES users(id) ON DELETE CASCADE,
    rollout_pct smallint,
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_feature_flags_global
    ON feature_flags (flag_name) WHERE user_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ix_feature_flags_per_user
    ON feature_flags (flag_name, user_id) WHERE user_id IS NOT NULL;
