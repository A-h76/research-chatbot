-- Migration 0040: Universal Full-Text Resolution (UFTR) provenance
-- JSON Text: outcome, user_reason, full_text_source, fetch_attempts, last_attempt_at

ALTER TABLE files ADD COLUMN IF NOT EXISTS fulltext_json TEXT DEFAULT '{}';
