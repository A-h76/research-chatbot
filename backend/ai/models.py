"""ORM models for the two tables migration 0005
(prompt_model_pipeline_versions.sql) creates that server.py never got
model classes for: prompt_versions and pipeline_versions.

Deliberately does NOT define ModelVersion or AIUsageLedger — those
already exist as live, actively-written-to classes in server.py (mapped
to model_versions and ai_usage_ledger respectively; see AIUsageLedger's
own docstring there for what writes to it). Redeclaring them here would
either collide with server.py's real ones or fork into a second,
disconnected definition of the same tables — see this task's own note on
why that's a real hazard, not just a style question.

There is also no `prompt_templates` table in the schema — 0005 defines
one flat `prompt_versions` table (rows share a `name`; a partial unique
index enforces one is_active=true per name, in Postgres only — see the
comment on PROMPT_VERSION_ACTIVE_INDEX_SQL below). So there's no separate
"template" parent row for PromptVersion to relate to; grouping is done by
querying `WHERE name = ...`, not a foreign key.

Factory functions (create_X_model(Base)), not classes importing `server`
— same reason as every other new model in this project (quotas/models.py,
auth/*): server.py runs as __main__, so a module it reaches into
importing "server" back re-executes the whole file under a second module
identity and recurses. server.py calls these with its own Base after
Base is defined, the same way it already does for
quotas.create_usage_log_model.

IDs are plain auto-incrementing integers (SQLAlchemy Integer / Postgres
bigserial), matching every other table in this schema — the schema has
no UUID primary keys anywhere, so introducing one here would be the odd
one out, not a consistency improvement.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)


def create_prompt_version_model(Base):
    class PromptVersion(Base):
        """One row per (name, version) — 0005's prompt_versions table.
        `is_active` marks the version currently served for that name; the
        migration's partial unique index (one active row per name) is
        Postgres-only and enforced there, not re-declared here — same
        convention server.py's own ModelVersion class already follows for
        its sibling table's identical constraint.

        The six columns below (migrations/0015_prompt_engine.sql — see
        docs/prompt-engine-architecture.md §3) add authoring metadata and
        a `status` lifecycle that's independent of `is_active`: `status`
        is draft|active|archived (which authoring states a version has
        passed through), `is_active` is still "the one version currently
        served for this name". PromptRegistry enforces that only a
        status='active' row may ever have is_active=True — not a DB-level
        CHECK here (SQLite has no reliable equivalent this project relies
        on elsewhere either; migration 0015's Postgres CHECK is the real
        enforcement for direct SQL, this is the enforcement for anything
        going through the ORM)."""

        __tablename__ = "prompt_versions"
        __table_args__ = (
            UniqueConstraint("name", "version", name="uq_prompt_versions_name_version"),
            Index("ix_prompt_versions_name_active", "name", "is_active"),
        )

        id = Column(Integer, primary_key=True)
        name = Column(Text, nullable=False)
        version = Column(Integer, nullable=False)
        template = Column(Text, nullable=False)
        is_active = Column(Boolean, nullable=False, default=False)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

        description = Column(Text, nullable=False, default="")
        status = Column(Text, nullable=False, default="draft")
        category = Column(Text, nullable=False, default="")
        examples = Column(Text, nullable=False, default="[]")  # JSON array, app-serialized
        expected_output_type = Column(Text, nullable=False, default="text")
        # Soft FK -> users.id: no ForeignKey(), prompt_versions lives under
        # this module's own private Base, not server.py's real one — same
        # reason CostLedgerEntry.user_id has none. Real FK constraint is
        # migration-level only (0015).
        author_user_id = Column(Integer, nullable=True)

    return PromptVersion


def create_pipeline_version_model(Base):
    class PipelineVersion(Base):
        """One row per pipeline bundle — 0005's pipeline_versions table.
        chunking_params / prompt_versions are JSON snapshots stored as
        Text (json.dumps/loads at the call site), matching how every
        other JSON-shaped column in this schema is represented
        (UserFile.tags, OutboxEvent.payload, ImportSession.checkpoint) —
        not SQLAlchemy's JSON/JSONB type, for consistency with the rest
        of this codebase rather than per-column preference.

        The `prompt_versions` column here is that JSON snapshot, not a
        relationship to the PromptVersion model above — same name,
        unrelated to the prompt_versions *table*; the migration's own
        comment explains why a JSONB snapshot was chosen over a join
        table (pipeline versions are created rarely, always read as one
        whole bundle)."""

        __tablename__ = "pipeline_versions"
        __table_args__ = (Index("ix_pipeline_versions_active", "is_active"),)

        id = Column(Integer, primary_key=True)
        version = Column(Integer, nullable=False, unique=True)
        importer_registry_version = Column(Text, nullable=False)
        chunking_params = Column(Text, nullable=False)  # JSON
        embed_model_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=False)
        utility_model_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=True)
        prompt_versions = Column(Text, nullable=False)  # JSON snapshot, see docstring
        is_active = Column(Boolean, nullable=False, default=False)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    return PipelineVersion


def create_persona_model(Base):
    class Persona(Base):
        """One row per persona — migrations/0015_prompt_engine.sql's
        personas table (docs/prompt-engine-architecture.md §5).

        `is_active` here means something different from
        PromptVersion.is_active above: many personas can be True at once
        (it just means "offered as a selectable option"), there's no
        partial-unique-per-name index enforcing exactly one. Don't assume
        the two columns behave the same way just because they share a
        name."""

        __tablename__ = "personas"
        id = Column(Integer, primary_key=True)
        name = Column(Text, nullable=False, unique=True)
        description = Column(Text, nullable=False, default="")
        system_prompt = Column(Text, nullable=False)
        is_active = Column(Boolean, nullable=False, default=True)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
        updated_at = Column(
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        )

    return Persona


def create_prompt_execution_model(Base):
    class PromptExecution(Base):
        """One row per PromptBuilder.build() call that actually went on
        to a model — migrations/0015_prompt_engine.sql's prompt_executions
        table (docs/prompt-engine-architecture.md §9). Real ForeignKeys to
        prompt_versions/personas since both live on this same Base (see
        prompt_registry.py); project_id/user_id are plain columns, same
        cross-Base reason as PromptVersion.author_user_id."""

        __tablename__ = "prompt_executions"
        id = Column(Integer, primary_key=True)
        prompt_version_id = Column(Integer, ForeignKey("prompt_versions.id"), nullable=True)
        persona_id = Column(Integer, ForeignKey("personas.id"), nullable=True)
        project_id = Column(Integer, nullable=True)
        user_id = Column(Integer, nullable=False)
        assembled_prompt = Column(Text, nullable=False)
        output_schema = Column(Text, nullable=True)  # JSON-as-text, nullable
        tokens_used = Column(Integer, nullable=True)
        latency_ms = Column(Integer, nullable=True)
        status = Column(Text, nullable=False, default="pending")  # pending|success|failed
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    return PromptExecution
