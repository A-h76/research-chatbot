-- Live per-user storage total. user_id is the primary key (one row per
-- user) — updated in the same transaction as every upload/delete, not a
-- periodic rollup, because quota enforcement needs a synchronous answer
-- before accepting a new file, not yesterday's number.
CREATE TABLE storage_usage (
    user_id    integer PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    bytes_used bigint NOT NULL DEFAULT 0,
    file_count integer NOT NULL DEFAULT 0,
    updated_at timestamptz NOT NULL DEFAULT now()
);
