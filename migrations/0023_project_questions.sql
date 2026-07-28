-- Migration 0023: project research questions (Sprint A).
-- User-authored open questions for a research project workspace.
-- Distinct from notes (freeform) and memories (AI-curated).

CREATE TABLE IF NOT EXISTS project_questions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    source VARCHAR(20) NOT NULL DEFAULT 'manual',
    linked_insight_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_project_questions_project
    ON project_questions (project_id);

CREATE INDEX IF NOT EXISTS ix_project_questions_user_project_status
    ON project_questions (user_id, project_id, status);
