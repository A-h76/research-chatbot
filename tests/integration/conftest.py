"""Shared fixtures for researcher workflow integration tests.

These tests exercise real SQLAlchemy models + worker handlers + Flask
routes together. External network APIs (Crossref, Semantic Scholar,
OpenAI) are mocked. Worker queue claim_batch is NOT used — SQLite from
root conftest cannot FOR UPDATE SKIP LOCKED; handlers are invoked
directly (same pattern as test_worker.py).

Run: pytest tests/integration/ -v
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import text

import server
import worker


SCHOLARLY_DDL = """
CREATE TABLE IF NOT EXISTS provider_cache (
    id INTEGER PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    cache_key VARCHAR(500) NOT NULL,
    response_json TEXT NOT NULL DEFAULT '{}',
    provider_version VARCHAR(20) DEFAULT '',
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    fetch_status VARCHAR(20) DEFAULT 'idle',
    fetch_started_at TIMESTAMP,
    locked_by VARCHAR(120),
    UNIQUE(provider, cache_key)
);
CREATE TABLE IF NOT EXISTS provider_circuit (
    provider VARCHAR(50) PRIMARY KEY,
    failures INTEGER NOT NULL DEFAULT 0,
    opened_at TIMESTAMP,
    updated_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS provider_metrics (
    id INTEGER PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    endpoint VARCHAR(200) NOT NULL,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(30) NOT NULL,
    cache_hit INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP
);
"""


@pytest.fixture
def db():
    session = server.SessionLocal()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def scholarly_tables(db):
    """provider_cache / circuit / metrics are migration-only — create for SQLite."""
    for stmt in SCHOLARLY_DDL.strip().split(";"):
        s = stmt.strip()
        if s:
            db.execute(text(s))
    db.commit()
    # Seed closed circuits
    for provider in ("crossref", "openalex", "semantic_scholar"):
        db.execute(
            text(
                "INSERT OR IGNORE INTO provider_circuit "
                "(provider, failures, opened_at, updated_at) VALUES (:p, 0, NULL, :u)"
            ),
            {"p": provider, "u": datetime.now(timezone.utc)},
        )
    db.commit()


@pytest.fixture
def client():
    return server.app.test_client()


@pytest.fixture
def researcher(db, client):
    """Authenticated researcher with a project — simulates register → create project."""
    email = f"researcher-{os.urandom(4).hex()}@example.com"
    user = server.User(email=email, name="Dr. Ada", auth_provider="dev")
    db.add(user)
    db.commit()

    project = server.Project(
        user_id=user.id,
        name="Thesis Chapter 2",
        emoji="📚",
        instructions="Prefer clinical evidence when available.",
    )
    db.add(project)
    db.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id

    return SimpleNamespace(user=user, project=project, client=client, db=db)


PAPER_TEXT = """
Effects of Metformin on HbA1c in Type 2 Diabetes
Jane Doe; John Smith
doi: 10.1234/metformin.2024

Abstract
A randomized controlled trial of metformin 1000mg daily in adults with T2D.

Methods
Patients received metformin or placebo for 12 weeks.

Results
HbA1c decreased significantly in the metformin arm.
""".strip()


PHASE1_RESULTS = {
    "document_understanding": {
        "metadata": {
            "title": "Effects of Metformin on HbA1c in Type 2 Diabetes",
            "authors": ["Jane Doe", "John Smith"],
            "doi": "10.1234/metformin.2024",
            "year": "2024",
        }
    },
    "classification": {
        "document_type": {"label": "rct", "confidence": 0.9},
        "domain": {"label": "medicine", "confidence": 0.92},
        "study_design": {"label": "randomized_controlled_trial", "confidence": 0.88},
    },
    "analysis_context": {
        "routing_profile": {"primary_routing": "medical", "module_pipeline": ["medical", "evidence"]}
    },
    "medical_understanding": {
        "skipped": False,
        "pico_elements": {
            "population": {"description": "Adults with T2D"},
            "interventions": [{"name": "Metformin"}],
            "outcomes": [{"name": "HbA1c"}],
        },
        "clinical_entities": [{"value": "Metformin", "entity_type": "drug"}],
    },
    "evidence_grading": {"skipped": False, "overall_grade": {"grade_value": "high", "confidence": 0.8}},
    "prompt_assembly": {},
    "knowledge_graph": {"statistics": {"total_nodes": 4, "total_edges": 3, "average_degree": 1.5}},
}


def seed_uploaded_paper(db, user, project, *, with_fallback_meta=False):
    """Simulate a completed import: UserFile + Chunk + content_hash."""
    uf = server.UserFile(
        user_id=user.id,
        project_id=project.id,
        name="metformin.pdf",
        mime="application/pdf",
        kind="document",
        path=f"users/{user.id}/metformin.pdf",
        size=len(PAPER_TEXT),
        text_len=len(PAPER_TEXT),
        content_hash=server._sha256(PAPER_TEXT),
        doi="10.1234/metformin.2024" if not with_fallback_meta else "",
        title="Effects of Metformin on HbA1c in Type 2 Diabetes" if with_fallback_meta else "",
        authors="Jane Doe; John Smith" if with_fallback_meta else "",
        year="2024" if with_fallback_meta else "",
        meta_status="pending",
    )
    db.add(uf)
    db.flush()
    db.add(
        server.Chunk(
            file_id=uf.id,
            idx=0,
            content=PAPER_TEXT[:800],
            embedding=json.dumps([0.1, 0.2, 0.3]),
            page=1,
            section="Abstract",
        )
    )
    db.commit()
    return uf


def force_circuit_open(db, provider: str):
    db.execute(
        text(
            "INSERT INTO provider_circuit (provider, failures, opened_at, updated_at) "
            "VALUES (:p, 5, :o, :u) "
            "ON CONFLICT(provider) DO UPDATE SET failures=5, opened_at=:o, updated_at=:u"
        ),
        {
            "p": provider,
            "o": datetime.now(timezone.utc),
            "u": datetime.now(timezone.utc),
        },
    )
    db.commit()


def seed_related_cache(db, file_id: int):
    from backend.scholarly import ProviderCache

    payload = {
        "related": [
            {
                "paper_id": "ref1",
                "doi": "10.9/ref",
                "title": "Cached Reference Paper",
                "authors": "Prior et al.",
                "year": 2020,
                "venue": "Diabetes Care",
                "abstract": "Prior metformin evidence.",
                "citation_count": 100,
                "open_access_url": "",
                "source": "semantic_scholar",
            }
        ],
        "citing": [],
        "recommended": [
            {
                "paper_id": "rec1",
                "doi": "",
                "title": "Cached Recommended Paper",
                "authors": "Ada",
                "year": 2023,
                "venue": "",
                "abstract": "Related work.",
                "citation_count": 12,
                "open_access_url": "https://oa.example/x",
                "source": "semantic_scholar",
            }
        ],
        "provider_version": "2024-01",
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }
    ProviderCache(db, "semantic_scholar").set(
        f"related:file:{file_id}",
        payload,
        ttl_hours=24 * 7,
        provider_version="2024-01",
    )
    db.commit()
    return payload


def mock_phase1_service(mocker, file_id: int, content_hash: str):
    from backend.analysis_pipeline.models import AnalysisJobStatus, AnalysisResult

    result = AnalysisResult(
        file_id=file_id,
        content_hash=content_hash,
        status=AnalysisJobStatus.DONE,
        phase_results=PHASE1_RESULTS,
        pipeline_version="2.0.0",
        total_processing_time_ms=42.0,
    )
    mocker.patch(
        "backend.analysis_pipeline.service.AnalysisPipelineService.analyze_file_path",
        return_value=result,
    )
    return result


def mock_local_copy(mocker, paper_path: str):
    from contextlib import contextmanager

    @contextmanager
    def _copy(key, suffix=".bin"):
        yield paper_path

    mocker.patch.object(server.storage.storage_manager.provider, "local_copy", _copy)


def mock_paper_analysis_ai(mocker):
    """Mock PromptRegistry/ModelRegistry used by worker paper_analysis."""
    analysis = {
        "executive_summary": "Metformin lowers HbA1c in T2D.",
        "abstract_explained": "RCT of metformin.",
        "research_objective": "Test metformin effect on HbA1c",
        "problem_statement": "Need better glycemic control",
        "methodology": "12-week RCT",
        "dataset": None,
        "experiments": "metformin vs placebo",
        "results": "HbA1c decreased",
        "key_contributions": ["RCT evidence for metformin"],
        "strengths": ["RCT design"],
        "limitations": ["Short follow-up"],
        "future_work": ["Longer trials"],
        "keywords": ["metformin", "HbA1c"],
        "important_terms": {"HbA1c": "glycated hemoglobin"},
    }

    prompt_registry = mocker.Mock()
    prompt_registry.get_prompt.return_value = ("rendered", mocker.Mock())
    model_registry = mocker.Mock()
    model_registry.call.return_value = {
        "content": json.dumps(analysis),
        "model": "gpt-4o-mini",
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150,
        "finish_reason": "stop",
        "cost": 0.001,
    }
    mocker.patch.object(worker, "PromptRegistry", return_value=prompt_registry)
    mocker.patch.object(worker, "ModelRegistry", return_value=model_registry)
    mocker.patch.object(worker, "_get_text_for_file", lambda uf: PAPER_TEXT)
    return model_registry
