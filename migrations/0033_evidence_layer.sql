-- Phase 2.2 / Week 2: Evidence Layer MVP
-- Canonical EvidenceObject + reviews + writing bindings + extraction runs
-- Soft FKs to users/projects/files/documents enforced at migration level where tables exist.
-- Structured arrays/objects stored as Text JSON (application-serialized).

CREATE TABLE IF NOT EXISTS evidence_objects (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    page INTEGER,
    char_start INTEGER,
    char_end INTEGER,
    section VARCHAR(200) DEFAULT '',
    quote TEXT NOT NULL,
    claim TEXT NOT NULL,
    study_type VARCHAR(80) DEFAULT '',
    study_quality VARCHAR(40) DEFAULT '',
    supports_json TEXT DEFAULT '[]',
    contradicts_json TEXT DEFAULT '[]',
    limitations_json TEXT DEFAULT '[]',
    confidence_band VARCHAR(20) NOT NULL DEFAULT 'low',
    status VARCHAR(20) NOT NULL DEFAULT 'candidate',
    pipeline_version VARCHAR(40) NOT NULL,
    created_by VARCHAR(80) NOT NULL DEFAULT 'analysis-pipeline',
    content_hash VARCHAR(64) NOT NULL,
    supersedes_id INTEGER,
    provenance_json TEXT DEFAULT '{}',
    source_kg_node_id VARCHAR(120) DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_evidence_objects_user_project_updated
    ON evidence_objects (user_id, project_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS ix_evidence_objects_project_file_status
    ON evidence_objects (project_id, file_id, status);

CREATE INDEX IF NOT EXISTS ix_evidence_objects_project_hash_version
    ON evidence_objects (project_id, content_hash, pipeline_version);

CREATE INDEX IF NOT EXISTS ix_evidence_objects_supersedes
    ON evidence_objects (supersedes_id);

-- Active identity uniqueness (Postgres). Application layer enforces on SQLite.
CREATE UNIQUE INDEX IF NOT EXISTS uq_evidence_objects_active_identity
    ON evidence_objects (project_id, file_id, content_hash, pipeline_version)
    WHERE status NOT IN ('superseded', 'rejected');

CREATE TABLE IF NOT EXISTS claim_reviews (
    id SERIAL PRIMARY KEY,
    evidence_object_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    reason TEXT DEFAULT '',
    edited_claim TEXT,
    edited_quote TEXT,
    reviewed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_claim_reviews_evidence_reviewed
    ON claim_reviews (evidence_object_id, reviewed_at DESC);

CREATE INDEX IF NOT EXISTS ix_claim_reviews_user_project
    ON claim_reviews (user_id, project_id, reviewed_at DESC);

CREATE TABLE IF NOT EXISTS writing_sentence_bindings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    document_id INTEGER NOT NULL,
    evidence_object_id INTEGER NOT NULL,
    block_id VARCHAR(120) DEFAULT '',
    range_start INTEGER,
    range_end INTEGER,
    selected_text TEXT DEFAULT '',
    relation VARCHAR(20) NOT NULL DEFAULT 'supports',
    created_by VARCHAR(40) NOT NULL DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_writing_bindings_document_block
    ON writing_sentence_bindings (document_id, block_id);

CREATE INDEX IF NOT EXISTS ix_writing_bindings_evidence
    ON writing_sentence_bindings (evidence_object_id);

CREATE INDEX IF NOT EXISTS ix_writing_bindings_user_project
    ON writing_sentence_bindings (user_id, project_id);

CREATE TABLE IF NOT EXISTS evidence_extraction_runs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    pipeline_version VARCHAR(40) NOT NULL,
    input_content_hash VARCHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    objects_created INTEGER NOT NULL DEFAULT 0,
    error_json TEXT DEFAULT '{}',
    job_id INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_evidence_extraction_runs_identity
    ON evidence_extraction_runs (project_id, file_id, pipeline_version, input_content_hash);

CREATE INDEX IF NOT EXISTS ix_evidence_extraction_runs_project_created
    ON evidence_extraction_runs (project_id, created_at DESC);
