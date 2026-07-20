"""Round-trip tests for backend/ai/models.py against a real (in-memory
SQLite) DB — table creation, the composite unique constraint, and the FK
to model_versions all actually need to work, not just import cleanly.

Run: pytest backend/ai/test_models.py -v
"""
import json

import pytest
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.ai.models import create_prompt_version_model, create_pipeline_version_model


@pytest.fixture
def env():
    engine = create_engine("sqlite:///:memory:")
    Base = declarative_base()

    class ModelVersion(Base):
        # Minimal stand-in for server.py's real ModelVersion — just
        # enough for PipelineVersion's FK to attach to in this isolated
        # test DB, not a redeclaration of the real one.
        __tablename__ = "model_versions"
        id = Column(Integer, primary_key=True)
        logical_name = Column(String(50))

    PromptVersion = create_prompt_version_model(Base)
    PipelineVersion = create_pipeline_version_model(Base)

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    return {
        "SessionLocal": SessionLocal, "ModelVersion": ModelVersion,
        "PromptVersion": PromptVersion, "PipelineVersion": PipelineVersion,
    }


def test_prompt_version_round_trip(env):
    db = env["SessionLocal"]()
    db.add(env["PromptVersion"](name="paper_analysis", version=1,
                                template="Analyze: {text}", is_active=True))
    db.commit()

    row = db.query(env["PromptVersion"]).filter_by(name="paper_analysis").one()
    assert row.version == 1
    assert row.is_active is True
    db.close()


def test_prompt_version_unique_name_and_version(env):
    db = env["SessionLocal"]()
    db.add(env["PromptVersion"](name="x", version=1, template="a"))
    db.commit()

    db.add(env["PromptVersion"](name="x", version=1, template="b"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.close()


def test_prompt_version_same_name_different_version_allowed(env):
    db = env["SessionLocal"]()
    db.add(env["PromptVersion"](name="x", version=1, template="a"))
    db.add(env["PromptVersion"](name="x", version=2, template="b"))
    db.commit()   # no raise

    versions = db.query(env["PromptVersion"]).filter_by(name="x").all()
    assert len(versions) == 2
    db.close()


def test_pipeline_version_round_trip_with_model_version_fk(env):
    db = env["SessionLocal"]()
    mv = env["ModelVersion"](logical_name="embed_model")
    db.add(mv)
    db.flush()

    pv = env["PipelineVersion"](
        version=1, importer_registry_version="v3",
        chunking_params=json.dumps({"max_tokens": 500}),
        embed_model_version_id=mv.id,
        prompt_versions=json.dumps({"paper_analysis": 1}),
        is_active=True,
    )
    db.add(pv)
    db.commit()

    row = db.query(env["PipelineVersion"]).filter_by(version=1).one()
    assert row.embed_model_version_id == mv.id
    assert row.utility_model_version_id is None
    assert json.loads(row.chunking_params) == {"max_tokens": 500}
    db.close()


def test_pipeline_version_requires_embed_model_version(env):
    db = env["SessionLocal"]()
    pv = env["PipelineVersion"](
        version=1, importer_registry_version="v3",
        chunking_params="{}", embed_model_version_id=None,
        prompt_versions="{}",
    )
    db.add(pv)
    with pytest.raises(IntegrityError):
        db.commit()
    db.close()
