-- Migration 0020: provider ops refinements
-- - provider_circuit: DB-backed circuit breaker shared across processes
-- - locked_by on provider_cache for distributed lock ownership visibility

CREATE TABLE IF NOT EXISTS provider_circuit (
    provider   VARCHAR(50) PRIMARY KEY,
    failures   INTEGER     NOT NULL DEFAULT 0,
    opened_at  TIMESTAMP   DEFAULT NULL,
    updated_at TIMESTAMP   DEFAULT NOW()
);

ALTER TABLE provider_cache ADD COLUMN IF NOT EXISTS locked_by VARCHAR(120) DEFAULT NULL;

-- Seed rows so health checks always have something to read.
INSERT INTO provider_circuit (provider, failures, opened_at, updated_at)
VALUES
    ('crossref', 0, NULL, NOW()),
    ('openalex', 0, NULL, NOW()),
    ('semantic_scholar', 0, NULL, NOW())
ON CONFLICT (provider) DO NOTHING;
