-- Library Bridge: Connect Library OAuth tokens (Zotero / Mendeley)

CREATE TABLE IF NOT EXISTS library_connections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    provider VARCHAR(30) NOT NULL,
    external_user_id VARCHAR(100) DEFAULT '',
    access_token TEXT DEFAULT '',
    access_secret TEXT DEFAULT '',
    refresh_token TEXT DEFAULT '',
    meta_json TEXT DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_library_connections_user_provider
    ON library_connections (user_id, provider);

CREATE INDEX IF NOT EXISTS ix_library_connections_user_id
    ON library_connections (user_id);
