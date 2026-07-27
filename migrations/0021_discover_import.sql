-- Migration 0021: OpenAlex Discover → Add to Library
-- Metadata-only library stubs store the OA / landing URL here.

ALTER TABLE files ADD COLUMN IF NOT EXISTS source_url VARCHAR(500) DEFAULT '';
