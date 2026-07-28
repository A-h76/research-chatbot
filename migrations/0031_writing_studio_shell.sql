-- Phase 2.1 (M2): Writing Studio shell foundations

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    title VARCHAR(300) DEFAULT '',
    content TEXT DEFAULT '',
    editor_kind VARCHAR(20) DEFAULT 'markdown',
    status VARCHAR(20) DEFAULT 'draft',
    current_version INTEGER DEFAULT 1,
    last_saved_hash VARCHAR(64) DEFAULT '',
    last_opened_at TIMESTAMPTZ,
    word_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_documents_user_updated
    ON documents (user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS ix_documents_project_updated
    ON documents (project_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS document_versions (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    version_no INTEGER NOT NULL,
    title VARCHAR(300) DEFAULT '',
    content TEXT DEFAULT '',
    content_hash VARCHAR(64) DEFAULT '',
    source VARCHAR(20) DEFAULT 'save',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_document_versions_doc_version
    ON document_versions (document_id, version_no DESC);

CREATE INDEX IF NOT EXISTS ix_document_versions_user_created
    ON document_versions (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS document_activity (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    action VARCHAR(30) NOT NULL,
    meta_json TEXT DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_document_activity_doc_created
    ON document_activity (document_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_document_activity_user_created
    ON document_activity (user_id, created_at DESC);
