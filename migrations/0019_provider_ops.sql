-- Migration 0019: scholarly provider ops (metrics, fetch coalescing)
-- Extends provider_cache for request coalescing + stale refresh locks.
-- Adds provider_metrics for latency / cache / status observability.

ALTER TABLE provider_cache ADD COLUMN IF NOT EXISTS fetch_status VARCHAR(20) DEFAULT 'idle';
-- idle | fetching | ready
ALTER TABLE provider_cache ADD COLUMN IF NOT EXISTS fetch_started_at TIMESTAMP DEFAULT NULL;
-- Ensure provider_version is present (already in 0018; IF NOT EXISTS is safe).
ALTER TABLE provider_cache ADD COLUMN IF NOT EXISTS provider_version VARCHAR(20) DEFAULT '';

CREATE TABLE IF NOT EXISTS provider_metrics (
    id           SERIAL PRIMARY KEY,
    provider     VARCHAR(50)  NOT NULL,   -- crossref | openalex | semantic_scholar
    endpoint     VARCHAR(200) NOT NULL,   -- e.g. works/search, paper/related
    latency_ms   INTEGER      NOT NULL DEFAULT 0,
    status       VARCHAR(30)  NOT NULL,   -- ok | error | timeout | rate_limited | circuit_open | cache_hit | cache_stale
    cache_hit    BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_provider_metrics_provider_created
    ON provider_metrics(provider, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_provider_metrics_status
    ON provider_metrics(status, created_at DESC);
