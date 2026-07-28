-- Migration 0022: hot-path indexes for chat, library, and worker queues.
--
-- Schema mapping notes (vs informal "chat_id" / "jobs" names):
--   messages.conversation_id  — there is no messages.chat_id / file_id / project_id
--   upload_jobs              — the jobs table
--   Paper/project scope lives on conversations.file_id / conversations.project_id
--
-- Already present (do not recreate with a different definition):
--   ix_files_user, ix_files_user_checksum
--   ix_upload_jobs_pending (status, run_after) WHERE pending
--   ix_upload_jobs_file / _batch / _user_status
--   ix_outbox_events_pending (status, created_at) WHERE pending
--   UNIQUE(provider, cache_key) + idx_provider_cache_lookup on provider_cache

-- ── Messages: load history for one conversation ─────────────────────────────
CREATE INDEX IF NOT EXISTS ix_messages_conversation_created
    ON messages (conversation_id, created_at);

-- ── Conversations: recent list, project chat, paper chat ────────────────────
CREATE INDEX IF NOT EXISTS ix_conversations_user_updated
    ON conversations (user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS ix_conversations_user_project
    ON conversations (user_id, project_id);
CREATE INDEX IF NOT EXISTS ix_conversations_user_file
    ON conversations (user_id, file_id);
CREATE INDEX IF NOT EXISTS ix_conversations_project
    ON conversations (project_id);
CREATE INDEX IF NOT EXISTS ix_conversations_file
    ON conversations (file_id);

-- ── Files: library project filter + chat attachments ────────────────────────
CREATE INDEX IF NOT EXISTS ix_files_user_project
    ON files (user_id, project_id);
CREATE INDEX IF NOT EXISTS ix_files_conversation
    ON files (conversation_id);

-- ── Upload jobs: type/status dashboards + file-stage lookups ────────────────
CREATE INDEX IF NOT EXISTS ix_upload_jobs_type_status
    ON upload_jobs (job_type, status);
CREATE INDEX IF NOT EXISTS ix_upload_jobs_status_created
    ON upload_jobs (status, created_at);
CREATE INDEX IF NOT EXISTS ix_upload_jobs_file_type
    ON upload_jobs (file_id, job_type);

-- ── Outbox: status scans beyond the pending-only partial index ──────────────
CREATE INDEX IF NOT EXISTS ix_outbox_events_status_created
    ON outbox_events (status, created_at);

-- ── Adjacent surfaces hit by the same product pages ─────────────────────────
CREATE INDEX IF NOT EXISTS ix_projects_user
    ON projects (user_id);
CREATE INDEX IF NOT EXISTS ix_memories_user
    ON memories (user_id);
CREATE INDEX IF NOT EXISTS ix_memories_user_project
    ON memories (user_id, project_id);
CREATE INDEX IF NOT EXISTS ix_citations_user
    ON citations (user_id);
