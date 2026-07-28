"""End-to-end researcher workflow tests.

Simulates complete product journeys (not isolated units):

  A) Happy path — register → project → paper → Phase 1 → Crossref →
     related cache → paper_analysis with Phase 1 → chat inject
  B) Crossref offline — upload/enrich soft-fails → Phase 1 fallback meta → chat
  C) Semantic Scholar circuit open — cached related still served; miss → 503

External HTTP (Crossref / S2 / OpenAI) is mocked. Real DB models, worker
handlers, PromptBuilder, and Flask routes run for real.

Run: pytest tests/integration/test_researcher_workflows.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import select, text

import server
import worker
from backend.scholarly.crossref import enrich_from_extracted_text
from backend.scholarly.semantic_scholar import get_related_papers

from tests.integration.conftest import (
    PAPER_TEXT,
    mock_paper_analysis_ai,
    mock_phase1_service,
    mock_local_copy,
    seed_related_cache,
    seed_uploaded_paper,
)


def _run_phase1(db, uf, mocker, tmp_path: Path):
    paper = tmp_path / "metformin.pdf"
    paper.write_bytes(b"%PDF-1.4 fake")
    mock_local_copy(mocker, str(paper))
    mock_phase1_service(mocker, uf.id, uf.content_hash or server._sha256(PAPER_TEXT))
    job = server.UploadJob(
        file_id=uf.id,
        user_id=uf.user_id,
        job_type="phase1_analysis",
        status="running",
    )
    db.add(job)
    db.commit()
    worker._handle_phase1_analysis(db, job)
    return job


def _run_paper_analysis(db, uf, mocker):
    model_registry = mock_paper_analysis_ai(mocker)
    from backend.ai.prompt_registry import PromptRegistry

    reg = PromptRegistry(db)
    for name, template in (
        ("system_prompt", "You are a careful research assistant."),
        ("paper_analysis", "Analyze the paper.\n{{ text }}\nmax={{ max_chars }}"),
    ):
        try:
            reg.get_prompt(name)
        except ValueError:
            reg.create_prompt(name, "test", template, status="active")
    db.commit()

    job = server.UploadJob(
        file_id=uf.id,
        user_id=uf.user_id,
        job_type="paper_analysis",
        status="running",
    )
    db.add(job)
    db.commit()
    worker._handle_paper_analysis(db, job)
    return model_registry


# ═══════════════════════════════════════════════════════════════════════════
# A) Happy path — full researcher workflow
# ═══════════════════════════════════════════════════════════════════════════


def test_workflow_a_researcher_happy_path(researcher, mocker, tmp_path, monkeypatch):
    """register → project → upload → Phase 1 → Crossref → related → chat Phase 1."""
    db = researcher.db
    client = researcher.client
    user = researcher.user
    project = researcher.project

    # ── Project exists (created in fixture — also verify API list) ────────
    resp = client.get("/api/projects")
    assert resp.status_code == 200
    assert any(p["id"] == project.id for p in resp.get_json())

    # ── Upload completed (import simulated) ───────────────────────────────
    uf = seed_uploaded_paper(db, user, project)

    # ── Crossref enrichment succeeds ──────────────────────────────────────
    monkeypatch.setenv("ENABLE_CROSSREF", "true")
    mocker.patch(
        "backend.scholarly.crossref.fetch_crossref_metadata",
        return_value={
            "title": "Effects of Metformin on HbA1c in Type 2 Diabetes",
            "authors": "Jane Doe; John Smith",
            "year": "2024",
            "venue": "Diabetes Care",
            "abstract": "A randomized controlled trial of metformin.",
            "doi": "10.1234/metformin.2024",
            "source": "crossref",
        },
    )
    assert enrich_from_extracted_text(db, uf.id, PAPER_TEXT) is True
    row = db.execute(
        text(
            "SELECT title, venue, doi_verified, metadata_source, title_source "
            "FROM files WHERE id=:id"
        ),
        {"id": uf.id},
    ).mappings().fetchone()
    assert row["doi_verified"] in (True, 1)
    assert row["metadata_source"] == "crossref"
    assert row["venue"] == "Diabetes Care"
    assert (row["title_source"] or "") in ("crossref", "")

    # ── Phase 1 pipeline completes ────────────────────────────────────────
    _run_phase1(db, uf, mocker, tmp_path)
    apr = db.execute(
        select(server.AnalysisPipelineResult).where(
            server.AnalysisPipelineResult.file_id == uf.id
        )
    ).scalar_one()
    assert apr.status == "done"
    phases = json.loads(apr.phase_results)
    assert "classification" in phases
    assert phases["classification"]["domain"]["label"] == "medicine"

    # paper_analysis job was enqueued by phase1 handler
    pa_jobs = (
        db.execute(
            select(server.UploadJob).where(
                server.UploadJob.file_id == uf.id,
                server.UploadJob.job_type == "paper_analysis",
            )
        )
        .scalars()
        .all()
    )
    assert any(j.status == "pending" for j in pa_jobs)

    # ── Related papers appear (fresh cache) ───────────────────────────────
    monkeypatch.setenv("ENABLE_SEMANTIC_SCHOLAR", "true")
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "test-key")
    monkeypatch.setattr(
        "backend.scholarly.semantic_scholar._S2_API_KEY",
        "test-key",
        raising=False,
    )
    seed_related_cache(db, uf.id)
    related_resp = client.get(f"/api/files/{uf.id}/related")
    assert related_resp.status_code == 200
    related_body = related_resp.get_json()
    assert related_body["related"][0]["title"] == "Cached Reference Paper"
    assert related_body["recommended"][0]["title"] == "Cached Recommended Paper"

    # ── LLM paper analysis consumes Phase 1 via PromptBuilder ─────────────
    model_registry = _run_paper_analysis(db, uf, mocker)
    assert model_registry.call.called
    prompt_sent = model_registry.call.call_args[0][1][0]["content"]
    assert "Phase 1 Structured Analysis" in prompt_sent
    assert "Metformin" in prompt_sent

    pa = db.execute(
        select(server.PaperAnalysis).where(server.PaperAnalysis.file_id == uf.id)
    ).scalar_one()
    assert pa.status == "done"
    data = json.loads(pa.data)
    assert "HbA1c" in data["executive_summary"]

    # ── Paper chat: PromptBuilder keeps Phase 1 for developer injection ───
    monkeypatch.setenv("PAPER_CHAT_PHASE1_CONTEXT", "true")
    monkeypatch.setenv("PAPER_CHAT_USE_PROMPT_BUILDER", "true")
    db.refresh(uf)
    phase1_ctx = server._load_paper_phase1_context(db, uf.id)
    assert "Phase 1 Structured Analysis" in phase1_ctx
    assert "medicine" in phase1_ctx or "Metformin" in phase1_ctx

    system, phase1_for_dev = server.build_paper_chat_system_prompt(
        user, uf, phase1_context=phase1_ctx
    )
    assert "THIS PAPER ONLY" in system
    assert "Phase 1" not in system  # system-prompt hash parity preserved
    assert "Phase 1 Structured Analysis" in phase1_for_dev

    # Conversation scoped to the paper (paper chat)
    convo = server.Conversation(
        user_id=user.id,
        project_id=project.id,
        file_id=uf.id,
        title="Metformin questions",
    )
    db.add(convo)
    db.commit()
    assert convo.file_id == uf.id


# ═══════════════════════════════════════════════════════════════════════════
# B) Crossref offline — upload / Phase 1 / chat still work
# ═══════════════════════════════════════════════════════════════════════════


def test_workflow_b_crossref_offline_fallback(researcher, mocker, tmp_path, monkeypatch):
    """Crossref down → enrich soft-fails → Phase 1 fills meta → chat works."""
    db = researcher.db
    user = researcher.user
    project = researcher.project

    uf = seed_uploaded_paper(db, user, project, with_fallback_meta=True)
    # Empty DOI forces text extraction path; Crossref returns None (offline).
    uf.doi = ""
    # Keep extracted fallback title from importer/Phase 1.1 style
    db.commit()

    monkeypatch.setenv("ENABLE_CROSSREF", "true")
    mocker.patch("backend.scholarly.crossref.fetch_crossref_metadata", return_value=None)
    mocker.patch("backend.scholarly.crossref._cached_crossref", return_value=None)

    # Soft-fail: does not raise; enrichment not applied
    assert enrich_from_extracted_text(db, uf.id, PAPER_TEXT) is False

    row = db.execute(
        text("SELECT doi_verified, metadata_source, title FROM files WHERE id=:id"),
        {"id": uf.id},
    ).mappings().fetchone()
    # DOI may have been extracted from text even if Crossref failed
    assert row["doi_verified"] in (False, 0, None)
    assert (row["metadata_source"] or "extracted") != "crossref" or row["title"]
    # Fallback bibliographic fields from upload/extract still present
    assert "Metformin" in (row["title"] or "")

    # Phase 1 still completes (mocked service)
    _run_phase1(db, uf, mocker, tmp_path)
    apr = db.execute(
        select(server.AnalysisPipelineResult).where(
            server.AnalysisPipelineResult.file_id == uf.id
        )
    ).scalar_one()
    assert apr.status == "done"

    # Chat Phase 1 inject still works without Crossref
    ctx = server._load_paper_phase1_context(db, uf.id)
    assert "Phase 1 Structured Analysis" in ctx
    system, phase1 = server.build_paper_chat_system_prompt(user, uf, phase1_context=ctx)
    assert system
    assert phase1


# ═══════════════════════════════════════════════════════════════════════════
# C) Semantic Scholar circuit open — cache hit vs graceful miss
# ═══════════════════════════════════════════════════════════════════════════


def test_workflow_c_s2_circuit_open_uses_cache_or_graceful_503(
    researcher, monkeypatch
):
    """Circuit open: serve cached related papers; without cache → 503 soft fail."""
    db = researcher.db
    client = researcher.client
    user = researcher.user
    project = researcher.project

    uf = seed_uploaded_paper(db, user, project)
    monkeypatch.setenv("ENABLE_SEMANTIC_SCHOLAR", "true")
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "test-key")
    monkeypatch.setattr(
        "backend.scholarly.semantic_scholar._S2_API_KEY",
        "test-key",
        raising=False,
    )
    # SQLite can't run the circuit SQL that uses Postgres NOW(); force open
    # at the function boundary (same effect as provider_circuit.opened_at set).
    monkeypatch.setattr(
        "backend.scholarly.circuit_is_open",
        lambda provider, db=None: provider == "semantic_scholar",
    )

    # ── With cache: Related tab still works even while circuit is open ────
    seed_related_cache(db, uf.id)
    bundle = get_related_papers(
        file_id=uf.id,
        doi=uf.doi,
        title=uf.title or uf.name,
        db=db,
    )
    assert bundle is not None
    assert any(p.title == "Cached Recommended Paper" for p in bundle.recommended)

    resp = client.get(f"/api/files/{uf.id}/related")
    assert resp.status_code == 200
    assert resp.get_json()["recommended"][0]["title"] == "Cached Recommended Paper"

    # ── Without cache: live fetch blocked → graceful unavailable ──────────
    uf2 = seed_uploaded_paper(db, user, project)
    resp2 = client.get(f"/api/files/{uf2.id}/related")
    assert resp2.status_code == 503
    body = resp2.get_json()
    assert body["error"] == "related_unavailable"
    assert body["related"] == []
    assert "temporarily unavailable" in (body.get("message") or "").lower()
