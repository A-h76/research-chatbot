"""Tests for MemoryEngine against a real (in-memory SQLite) DB, using a
minimal stand-in for server.py's real Memory class (same convention as
backend/upload/test_upload.py's fixture — MemoryEngine is
constructor-injected and doesn't care which Memory class it's given,
real or a test stand-in with the same columns).

Run: pytest backend/ai/test_memory_engine.py -v
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, Column, Integer, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.ai.memory_engine import MemoryEngine


@pytest.fixture
def env():
    engine = create_engine("sqlite:///:memory:")
    Base = declarative_base()

    class Memory(Base):
        __tablename__ = "memories"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, nullable=False)
        project_id = Column(Integer, nullable=True)
        fact = Column(Text, nullable=False)
        importance = Column(Integer, default=3)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    return {"db": db, "Memory": Memory, "engine": MemoryEngine(db, Memory)}


def _add(env, user_id=1, project_id=None, fact="a fact", importance=3, age_seconds=0):
    m = env["Memory"](
        user_id=user_id, project_id=project_id, fact=fact, importance=importance,
        created_at=datetime.now(timezone.utc) - timedelta(seconds=age_seconds),
    )
    env["db"].add(m)
    env["db"].commit()
    return m


# ------------------------------------------------------------ project scoping
def test_project_none_returns_only_global_memories(env):
    _add(env, project_id=None, fact="global one")
    _add(env, project_id=7, fact="project seven one")

    results = env["engine"].get_relevant_memories(1, "anything")
    assert [m.fact for m in results] == ["global one"]


def test_project_id_returns_that_project_plus_global(env):
    _add(env, project_id=None, fact="global one")
    _add(env, project_id=7, fact="project seven one")
    _add(env, project_id=9, fact="project nine one")

    results = env["engine"].get_relevant_memories(1, "anything", project_id=7)
    assert {m.fact for m in results} == {"global one", "project seven one"}


def test_scoped_to_requesting_user(env):
    _add(env, user_id=1, fact="mine")
    _add(env, user_id=2, fact="not mine")

    results = env["engine"].get_relevant_memories(1, "anything")
    assert [m.fact for m in results] == ["mine"]


def test_empty_when_no_memories_exist(env):
    assert env["engine"].get_relevant_memories(1, "anything") == []


# ------------------------------------------------------------ ranking
def test_keyword_overlap_ranks_matching_fact_first(env):
    _add(env, fact="likes deep learning and transformers", importance=3)
    _add(env, fact="prefers tea over coffee", importance=3)

    results = env["engine"].get_relevant_memories(1, "tell me about transformers")
    assert results[0].fact == "likes deep learning and transformers"


def test_importance_breaks_ties_when_keyword_overlap_equal(env):
    _add(env, fact="unrelated fact one", importance=1)
    _add(env, fact="unrelated fact two", importance=5)

    results = env["engine"].get_relevant_memories(1, "query with no overlap at all")
    assert results[0].fact == "unrelated fact two"


def test_recency_breaks_ties_when_keyword_and_importance_equal(env):
    _add(env, fact="older unrelated fact", importance=3, age_seconds=1000)
    _add(env, fact="newer unrelated fact", importance=3, age_seconds=0)

    results = env["engine"].get_relevant_memories(1, "query with no overlap at all")
    assert results[0].fact == "newer unrelated fact"


def test_limit_is_respected(env):
    for i in range(10):
        _add(env, fact=f"fact number {i}")

    results = env["engine"].get_relevant_memories(1, "fact", limit=3)
    assert len(results) == 3


def test_default_limit_is_five(env):
    for i in range(10):
        _add(env, fact=f"fact number {i}")

    results = env["engine"].get_relevant_memories(1, "fact")
    assert len(results) == 5
