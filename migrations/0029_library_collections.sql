-- Phase 1.6: Library collections (folders) — many-to-many with papers

CREATE TABLE IF NOT EXISTS library_collections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    parent_id INTEGER,
    external_id VARCHAR(100) DEFAULT '',
    source VARCHAR(30) DEFAULT 'manual',
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_library_collections_user
    ON library_collections (user_id);

CREATE INDEX IF NOT EXISTS ix_library_collections_parent
    ON library_collections (user_id, parent_id);

CREATE INDEX IF NOT EXISTS ix_library_collections_external
    ON library_collections (user_id, source, external_id);

CREATE TABLE IF NOT EXISTS library_collection_papers (
    id SERIAL PRIMARY KEY,
    collection_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (collection_id, file_id)
);

CREATE INDEX IF NOT EXISTS ix_library_collection_papers_file
    ON library_collection_papers (file_id);

CREATE INDEX IF NOT EXISTS ix_library_collection_papers_collection
    ON library_collection_papers (collection_id);
