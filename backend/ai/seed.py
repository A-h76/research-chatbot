"""Seeds default prompts and model-call presets. Run directly
(python -m backend.ai.seed) or import seed_prompts()/seed_pipelines()
and call with an already-open session (e.g. from server.py on startup).

Both functions are idempotent — safe to call on every startup, not just
once — matching backfill.py's own "checks for existing rows before
inserting" convention.

IMPORTANT — read before assuming this seeds what its name suggests:

seed_prompts() writes into the REAL prompt_versions table via
PromptRegistry, but backfill.py already seeds five prompts there
(extract_metadata, paper_analysis, compare, gap_finder, chat_system) —
real, detailed templates the app's actual code (extract_metadata(),
trigger_paper_analysis(), etc.) depends on. This task's own
"paper_analysis" name collides with that. Seeding here is idempotent BY
NAME: if backfill.py already ran, this function's short "paper_analysis"
stub is skipped, not inserted — the real, live prompt is never
overwritten. The other six names (paper_summary, citation_generation,
semantic_search, gap_analysis, comparison, literature_review) don't
collide with anything and seed normally.

seed_pipelines() does NOT write into pipeline_versions — that table
(also already seeded by backfill.py) represents something structurally
different: an import/embedding pipeline bundle (chunking params + a
required FK to a real model_versions row), not a named chat-call preset
like {"model": "gpt-4o", "temperature": 0.7, "max_tokens": 2000}.
Forcing these three presets into pipeline_versions would mean fabricating
a fake embed_model_version_id FK that has nothing to do with what's
actually being seeded. Instead this defines its own small, new
model_presets table — a different, genuinely new concept, not a
duplicate or a rename of pipeline_versions. No migration exists for this
table since nothing else in the schema needs it; this module creates it
if missing (see _ensure_model_presets_table).
"""
import json
import os
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import declarative_base

from .prompt_registry import PromptRegistry

_Base = declarative_base()


def create_model_preset_model(Base):
    class ModelPreset(Base):
        __tablename__ = "model_presets"
        __table_args__ = (UniqueConstraint("name", name="uq_model_presets_name"),)
        id = Column(Integer, primary_key=True)
        name = Column(String(60), nullable=False)
        config = Column(Text, nullable=False)   # JSON: {"model", "temperature", "max_tokens", ...}
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    return ModelPreset


ModelPreset = create_model_preset_model(_Base)


# The task's own opening phrases ("Summarize this research paper...")
# are clearly truncated illustrations, not complete templates — expanded
# into full, renderable ones with real Jinja2 variables, matching the
# quality bar of backfill.py's own PROMPTS dict rather than seeding
# literal "..." into the database.
DEFAULT_PROMPTS = {
    "paper_summary": (
        "Summarize this research paper, covering its main contribution, "
        "methodology, and key findings.\n\nPaper:\n{{ text }}"
    ),
    "paper_analysis": (
        "Analyze this paper's methodology, including its research design, "
        "data sources, and analytical approach. Identify strengths and "
        "limitations.\n\nPaper:\n{{ text }}"
    ),
    "citation_generation": (
        "Generate a BibTeX citation for the following paper, using only "
        "the metadata given.\n\nTitle: {{ title }}\nAuthors: {{ authors }}\n"
        "Year: {{ year }}\nVenue: {{ venue }}\nDOI: {{ doi }}"
    ),
    "semantic_search": (
        "Given these documents, answer the following question using only "
        "information found in them. Cite which document each fact comes "
        "from.\n\nDocuments:\n{{ documents }}\n\nQuestion: {{ question }}"
    ),
    "gap_analysis": (
        "Identify research gaps in the following set of papers — "
        "underexplored topics, open questions, and missing experiments.\n\n"
        "Papers:\n{{ papers }}"
    ),
    "comparison": (
        "Compare these two papers in terms of methodology, findings, and "
        "contributions. Note similarities and differences.\n\n"
        "Paper A:\n{{ paper_a }}\n\nPaper B:\n{{ paper_b }}"
    ),
    "literature_review": (
        "Synthesize these papers into a coherent literature review, "
        "identifying common themes, contradictions, and trends.\n\n"
        "Papers:\n{{ papers }}"
    ),
}

DEFAULT_PIPELINES = {
    "gpt-4o-chat": {"model": "gpt-4o", "temperature": 0.7, "max_tokens": 2000},
    "gpt-4o-mini-chat": {"model": "gpt-4o-mini", "temperature": 0.7, "max_tokens": 1000},
    "gpt-4o-analysis": {"model": "gpt-4o", "temperature": 0.3, "max_tokens": 4000},
}


def seed_prompts(db_session) -> dict:
    """Returns {name: PromptVersion} for all seven default prompts —
    freshly created ones and pre-existing ones (from this function on a
    prior run, or from backfill.py) alike."""
    registry = PromptRegistry(db_session)
    result = {}
    for name, template in DEFAULT_PROMPTS.items():
        existing = registry.get_active_version(name)
        if existing:
            print(f"SKIP  prompt '{name}' already seeded (v{existing.version})")
            result[name] = existing
            continue
        result[name] = registry.create_prompt(
            name=name, description=f"Default seed prompt: {name}", template_text=template)
        print(f"OK    prompt '{name}' seeded")
    return result


def seed_pipelines(db_session) -> dict:
    """Returns {name: ModelPreset} for the three default chat-call
    presets. Ensures model_presets exists first — see module docstring
    for why this table, not pipeline_versions."""
    _ensure_model_presets_table(db_session)

    result = {}
    for name, config in DEFAULT_PIPELINES.items():
        existing = db_session.query(ModelPreset).filter_by(name=name).first()
        if existing:
            print(f"SKIP  pipeline preset '{name}' already seeded")
            result[name] = existing
            continue
        row = ModelPreset(name=name, config=json.dumps(config))
        db_session.add(row)
        db_session.commit()
        print(f"OK    pipeline preset '{name}' seeded ({config})")
        result[name] = row
    return result


def _ensure_model_presets_table(db_session):
    """No migration creates model_presets (see module docstring) — this
    is the one place responsible for it existing, checked cheaply via
    the bind already on db_session rather than requiring a separate
    engine reference."""
    engine = db_session.get_bind()
    ModelPreset.__table__.create(bind=engine, checkfirst=True)


def seed_all(db_session) -> dict:
    return {"prompts": seed_prompts(db_session), "pipelines": seed_pipelines(db_session)}


if __name__ == "__main__":
    from dotenv import load_dotenv
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from .prompt_registry import _Base as _prompt_base

    load_dotenv()
    # Same DATABASE_URL / SQLite-fallback convention as backfill.py —
    # standalone engine, not server.py's (avoids `import server`, which
    # would re-execute that file under a second module identity since
    # it runs as __main__ — see auth/magic_link.py's docstring for the
    # full explanation of why that's a hard rule in this project).
    url = (os.environ.get("DATABASE_URL") or "sqlite:///chat_dev.db").replace(
        "postgres://", "postgresql://", 1)
    engine = create_engine(url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)

    # prompt_versions only exists today via the Postgres-only migration
    # 0005 — never against local SQLite (no ORM class was ever
    # registered under server.py's own Base to trigger its creation
    # there). checkfirst=True makes this a no-op wherever the real
    # migration already ran (any real Postgres deployment); it only
    # actually creates anything on a fresh SQLite dev DB, so this CLI
    # entrypoint works out of the box either way.
    _prompt_base.metadata.create_all(engine, checkfirst=True)

    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()
