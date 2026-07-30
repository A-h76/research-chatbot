-- A-401 / EPIC-0005 A-503: durable Research Reviewer runs + findings
-- Soft Integer FKs (application ownership checks). TEXT JSON for structured payloads.
-- Distinct from claim_reviews (human EvidenceObject accept/reject).

CREATE TABLE IF NOT EXISTS reviewer_runs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    document_id INTEGER NOT NULL,
    document_version_no INTEGER NOT NULL DEFAULT 1,
    writing_version VARCHAR(40) NOT NULL DEFAULT '',
    reviewer_version VARCHAR(40) NOT NULL,
    binder_version VARCHAR(40) DEFAULT '',
    status VARCHAR(20) NOT NULL,
    pass_rate DOUBLE PRECISION NOT NULL DEFAULT 0,
    sections_checked INTEGER NOT NULL DEFAULT 0,
    sections_passed INTEGER NOT NULL DEFAULT 0,
    issue_count INTEGER NOT NULL DEFAULT 0,
    metrics_json TEXT NOT NULL DEFAULT '{}',
    input_snapshot_json TEXT NOT NULL DEFAULT '{}',
    model_version_id INTEGER,
    prompt_version_id INTEGER,
    prompt_meta_json TEXT DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_reviewer_runs_document_created
    ON reviewer_runs (document_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_reviewer_runs_user_project_created
    ON reviewer_runs (user_id, project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_reviewer_runs_document_version
    ON reviewer_runs (document_id, reviewer_version);

CREATE TABLE IF NOT EXISTS reviewer_findings (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL,
    code VARCHAR(80) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT NOT NULL DEFAULT '',
    section_id VARCHAR(120),
    block_id VARCHAR(120) DEFAULT '',
    range_start INTEGER,
    range_end INTEGER,
    selected_text TEXT DEFAULT '',
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    confidence_band VARCHAR(20) DEFAULT '',
    recommendation TEXT DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    resolution_rationale TEXT DEFAULT '',
    resolved_at TIMESTAMPTZ,
    resolved_by INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_reviewer_findings_run
    ON reviewer_findings (run_id);

CREATE INDEX IF NOT EXISTS ix_reviewer_findings_run_severity
    ON reviewer_findings (run_id, severity);

CREATE INDEX IF NOT EXISTS ix_reviewer_findings_status
    ON reviewer_findings (status);

-- Soft Integer FKs only (ownership checked in app). Real FK to documents/runs
-- can be added in a follow-up Postgres-only migration if desired.
