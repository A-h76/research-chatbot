-- Phase A.6: append-only researcher workflow events (instrumentation, not analytics UI)

CREATE TABLE IF NOT EXISTS workflow_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    project_id INTEGER,
    event_name VARCHAR(80) NOT NULL,
    meta_json TEXT DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_workflow_events_user_created
    ON workflow_events (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_workflow_events_project_created
    ON workflow_events (project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_workflow_events_name
    ON workflow_events (event_name);
