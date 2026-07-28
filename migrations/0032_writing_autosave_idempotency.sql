-- Week 1 Writing Shell: autosave idempotency support

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS last_autosave_key VARCHAR(120) DEFAULT '';

