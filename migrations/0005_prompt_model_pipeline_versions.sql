-- Prompt Registry: named, versioned prompt templates. Exactly one active
-- version per name is enforced at the DB level, not just in application
-- code, via the partial unique index below.
CREATE TABLE prompt_versions (
    id         bigserial PRIMARY KEY,
    name       text NOT NULL,
    version    integer NOT NULL,
    template   text NOT NULL,
    is_active  boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (name, version)
);

CREATE UNIQUE INDEX ix_prompt_versions_active
    ON prompt_versions (name) WHERE is_active;

-- Model Registry: our own versioning of a model choice, independent of
-- the env-var value in use at any given moment, so "which model produced
-- this row" survives an env var change.
CREATE TABLE model_versions (
    id                bigserial PRIMARY KEY,
    logical_name      text NOT NULL,
    provider_model_id text NOT NULL,
    version           integer NOT NULL,
    is_active         boolean NOT NULL DEFAULT false,
    created_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (logical_name, version)
);

CREATE UNIQUE INDEX ix_model_versions_active
    ON model_versions (logical_name) WHERE is_active;

-- Pipeline Version: one addressable bundle of "what exactly produced this
-- file's chunks and analysis" — model + prompt versions as a JSONB
-- snapshot rather than a many-to-many join table, because pipeline
-- versions are created rarely and always read as one whole bundle, never
-- queried prompt-by-prompt.
CREATE TABLE pipeline_versions (
    id                        bigserial PRIMARY KEY,
    version                   integer NOT NULL UNIQUE,
    importer_registry_version text NOT NULL,
    chunking_params           jsonb NOT NULL,
    embed_model_version_id    bigint NOT NULL REFERENCES model_versions(id),
    utility_model_version_id  bigint REFERENCES model_versions(id),
    prompt_versions           jsonb NOT NULL,
    is_active                 boolean NOT NULL DEFAULT false,
    created_at                timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX ix_pipeline_versions_active
    ON pipeline_versions (is_active) WHERE is_active;

-- pipeline_versions now exists, so upload_jobs.pipeline_version_id (added
-- as a plain column in 0002, before this table existed) gets its FK here.
ALTER TABLE upload_jobs
    ADD CONSTRAINT fk_upload_jobs_pipeline_version
    FOREIGN KEY (pipeline_version_id) REFERENCES pipeline_versions(id);
