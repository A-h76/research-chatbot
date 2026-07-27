-- Migration 0018: scholarly provider integrations
-- Adds provider_cache, and new columns on files for Crossref enrichment.

-- Shared cache table for all external scholarly providers.
-- Keyed by (provider, cache_key); cache_key is typically a DOI, query hash, or paper ID.
CREATE TABLE IF NOT EXISTS provider_cache (
    id              SERIAL PRIMARY KEY,
    provider        VARCHAR(50)  NOT NULL,          -- 'crossref' | 'openalex' | 'semantic_scholar'
    cache_key       VARCHAR(500) NOT NULL,           -- doi / query-hash / s2_paper_id
    response_json   TEXT         NOT NULL DEFAULT '{}',
    provider_version VARCHAR(20) DEFAULT '',         -- API version if relevant
    expires_at      TIMESTAMP    NOT NULL,
    created_at      TIMESTAMP    DEFAULT NOW(),
    updated_at      TIMESTAMP    DEFAULT NOW(),
    UNIQUE(provider, cache_key)
);

CREATE INDEX IF NOT EXISTS idx_provider_cache_lookup
    ON provider_cache(provider, cache_key);

CREATE INDEX IF NOT EXISTS idx_provider_cache_expires
    ON provider_cache(expires_at);

-- Crossref enrichment columns on files table.
-- All additive; existing rows get NULLs / defaults without touching data.
ALTER TABLE files ADD COLUMN IF NOT EXISTS doi_verified       BOOLEAN      DEFAULT FALSE;
ALTER TABLE files ADD COLUMN IF NOT EXISTS crossref_last_synced TIMESTAMP  DEFAULT NULL;
ALTER TABLE files ADD COLUMN IF NOT EXISTS crossref_version   VARCHAR(20)  DEFAULT '';
ALTER TABLE files ADD COLUMN IF NOT EXISTS title_source       VARCHAR(30)  DEFAULT 'extracted';  -- extracted|crossref|user
ALTER TABLE files ADD COLUMN IF NOT EXISTS authors_source     VARCHAR(30)  DEFAULT 'extracted';
ALTER TABLE files ADD COLUMN IF NOT EXISTS year_source        VARCHAR(30)  DEFAULT 'extracted';
ALTER TABLE files ADD COLUMN IF NOT EXISTS venue_source       VARCHAR(30)  DEFAULT 'extracted';
ALTER TABLE files ADD COLUMN IF NOT EXISTS abstract_source    VARCHAR(30)  DEFAULT 'extracted';
ALTER TABLE files ADD COLUMN IF NOT EXISTS metadata_source    VARCHAR(30)  DEFAULT 'extracted';  -- summary source field
