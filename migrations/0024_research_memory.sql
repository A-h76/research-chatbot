-- Migration 0024: research memory fields on memories (Sprint C).
-- Extends existing memories table — no parallel store.
-- Research Memory is AI-generated from research outputs, not chat history.

ALTER TABLE memories ADD COLUMN IF NOT EXISTS kind VARCHAR(30) NOT NULL DEFAULT 'fact';
ALTER TABLE memories ADD COLUMN IF NOT EXISTS source VARCHAR(20) NOT NULL DEFAULT 'chat';
ALTER TABLE memories ADD COLUMN IF NOT EXISTS source_ref VARCHAR(80) DEFAULT '';
ALTER TABLE memories ADD COLUMN IF NOT EXISTS payload TEXT DEFAULT '{}';
ALTER TABLE memories ADD COLUMN IF NOT EXISTS pinned INTEGER NOT NULL DEFAULT 0;
ALTER TABLE memories ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active';
ALTER TABLE memories ADD COLUMN IF NOT EXISTS claim_hash VARCHAR(64) DEFAULT '';

CREATE INDEX IF NOT EXISTS ix_memories_project_status
    ON memories (project_id, status);

CREATE INDEX IF NOT EXISTS ix_memories_user_project_kind
    ON memories (user_id, project_id, kind);

CREATE INDEX IF NOT EXISTS ix_memories_claim_hash
    ON memories (user_id, project_id, kind, claim_hash);
