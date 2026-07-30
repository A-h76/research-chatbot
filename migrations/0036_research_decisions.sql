-- Phase A.2: Research Decisions (append-only project memory)
-- User-facing labels live in application code; type column stores ACCEPT|REJECT|…

CREATE TABLE IF NOT EXISTS research_decisions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    evidence_object_id INTEGER NOT NULL,
    decision_type VARCHAR(40) NOT NULL,
    reason TEXT DEFAULT '',
    reason_code VARCHAR(120) DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_research_decisions_project_created
    ON research_decisions (project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_research_decisions_evidence
    ON research_decisions (evidence_object_id);

CREATE INDEX IF NOT EXISTS ix_research_decisions_user_project
    ON research_decisions (user_id, project_id);
