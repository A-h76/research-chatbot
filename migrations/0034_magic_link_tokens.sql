-- Phase 3: single-use magic-link tokens (jti hash store)
CREATE TABLE IF NOT EXISTS magic_link_tokens (
    id SERIAL PRIMARY KEY,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(320) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_magic_link_tokens_email ON magic_link_tokens (email);
