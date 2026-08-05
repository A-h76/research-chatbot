"""Tests for project-scoped cross-paper research (Sprint B)."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import select

import server
from backend.projects.research import create_project_research_service


def _mock_llm(paper_id: int) -> str:
    return json.dumps(
        {
            "summary": "Papers disagree on effect size.",
            "answer": "There is tension between the RCT and observational findings.",
            "claims": [
                {
                    "claim": "Effect sizes diverge across study designs.",
                    "support": [
                        {
                            "paper_id": paper_id,
                            "title": "Paper A",
                            "section": "invalid_section",
                            "snippet": "Reported d=0.4 in the primary analysis.",
                            "citation": "Smith 2020",
                        }
                    ],
                }
            ],
        }
    )


class _MockGateway:
    def __init__(self, paper_id: int = 0):
        self.paper_id = paper_id

    def call(self, **kwargs):
        return {
            "content": _mock_llm(self.paper_id),
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
            "cost": 0.01,
        }


@pytest.fixture
def research_svc():
    from backend.analysis_pipeline.summary import build_phase1_prompt_context

    return create_project_research_service(
        SessionLocal=server.SessionLocal,
        select=select,
        Project=server.Project,
        UserFile=server.UserFile,
        PaperAnalysis=server.PaperAnalysis,
        DerivedAnalysis=server.DerivedAnalysis,
        AnalysisPipelineResult=server.AnalysisPipelineResult,
        get_prompt_builder=server.get_prompt_builder,
        ai_gateway=_MockGateway(),
        get_model_registry=lambda db: object(),
        utility_model="test-model",
        build_phase1_prompt_context=build_phase1_prompt_context,
    )


@pytest.fixture
def sync_research_threads(research_svc):
    research_svc._spawn_background = lambda target, args: target(*args)
    return research_svc


@pytest.fixture
def researcher():
    db = server.SessionLocal()
    try:
        user = server.User(
            name="Researcher",
            email=f"research-{server.uuid.uuid4().hex[:8]}@test.local",
            picture="",
            auth_provider="dev",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        project = server.Project(
            user_id=user.id,
            name="Thesis",
            emoji="🔬",
            description="Metformin review",
            instructions="Be precise.",
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        uid, pid = user.id, project.id
    finally:
        db.close()

    client = server.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = uid

    return {"user_id": uid, "project_id": pid, "client": client}


@pytest.fixture
def researcher_with_papers(researcher):
    uid = researcher["user_id"]
    pid = researcher["project_id"]
    db = server.SessionLocal()
    paper_ids = []
    try:
        for i, title in enumerate(["Paper A", "Paper B"], start=1):
            f = server.UserFile(
                user_id=uid,
                project_id=pid,
                name=f"p{i}.pdf",
                kind="document",
                title=title,
                authors=f"Author{i}",
                year="2020",
                meta_status="done",
                path=f"/tmp/p{i}.pdf",
                size=10,
            )
            db.add(f)
            db.commit()
            db.refresh(f)
            paper_ids.append(f.id)
            db.add(
                server.PaperAnalysis(
                    file_id=f.id,
                    user_id=uid,
                    status="done",
                    content_hash=f"hash-{i}",
                    data=json.dumps(
                        {
                            "executive_summary": f"Summary for {title}",
                            "methodology": "RCT with n=100",
                            "results": "Significant effect",
                        }
                    ),
                )
            )
        db.commit()
    finally:
        db.close()
    return {**researcher, "paper_ids": paper_ids}


def test_research_not_found(research_svc, sync_research_threads):
    payload, err = research_svc.start_research(
        99999, 1, preset="evidence", query="", file_ids=None, force=False
    )
    assert payload is None
    assert err == "not_found"


def test_research_too_few_ready(research_svc, sync_research_threads, researcher):
    payload, err = research_svc.start_research(
        researcher["project_id"],
        researcher["user_id"],
        preset="evidence",
        query="",
        file_ids=None,
        force=False,
    )
    assert payload is None
    assert err == "too_few_ready"


def test_research_preset_returns_claims(
    research_svc, sync_research_threads, researcher_with_papers, monkeypatch
):
    uid = researcher_with_papers["user_id"]
    project_id = researcher_with_papers["project_id"]
    fid = researcher_with_papers["paper_ids"][0]

    monkeypatch.setattr(research_svc, "ai_gateway", _MockGateway(fid))

    payload, err = research_svc.start_research(
        project_id,
        uid,
        preset="disagree",
        query="",
        file_ids=None,
        force=False,
    )
    assert err is None
    assert payload["status"] == "done"
    assert payload["summary"]
    assert payload["claims"]
    assert payload["claims"][0]["support"][0]["paper_id"] == fid
    assert payload["claims"][0]["support"][0]["section"] == ""


def test_research_rejects_paper_outside_project(
    research_svc, sync_research_threads, researcher_with_papers
):
    uid = researcher_with_papers["user_id"]
    project_id = researcher_with_papers["project_id"]
    in_project = researcher_with_papers["paper_ids"][0]

    db = server.SessionLocal()
    try:
        other = server.UserFile(
            user_id=uid,
            project_id=None,
            name="orphan.pdf",
            kind="document",
            title="Orphan",
            meta_status="done",
            path="/tmp/o.pdf",
            size=10,
        )
        db.add(other)
        db.commit()
        db.refresh(other)
        orphan_id = other.id
        db.add(
            server.PaperAnalysis(
                file_id=orphan_id,
                user_id=uid,
                status="done",
                content_hash="orphan",
                data=json.dumps({"executive_summary": "Orphan summary"}),
            )
        )
        db.commit()
    finally:
        db.close()

    payload, err = research_svc.start_research(
        project_id,
        uid,
        preset="evidence",
        query="",
        file_ids=[orphan_id, in_project],
        force=False,
    )
    assert payload is None
    assert err == "too_few_ready"


def test_research_cache_hit(research_svc, sync_research_threads, researcher_with_papers, monkeypatch):
    uid = researcher_with_papers["user_id"]
    project_id = researcher_with_papers["project_id"]
    fid = researcher_with_papers["paper_ids"][0]
    gw = _MockGateway(fid)
    calls = {"n": 0}

    class _CountingGW(_MockGateway):
        def call(self, **kwargs):
            calls["n"] += 1
            return super().call(**kwargs)

    monkeypatch.setattr(research_svc, "ai_gateway", _CountingGW(fid))

    first, err1 = research_svc.start_research(
        project_id, uid, preset="evidence", query="", file_ids=None, force=False
    )
    assert err1 is None
    assert first["status"] == "done"
    assert calls["n"] == 1

    second, err2 = research_svc.start_research(
        project_id, uid, preset="evidence", query="", file_ids=None, force=False
    )
    assert err2 is None
    assert second["id"] == first["id"]
    assert second["status"] == "done"
    assert calls["n"] == 1


def test_research_http(researcher_with_papers, monkeypatch):
    server.project_research_service._spawn_background = lambda target, args: target(*args)
    client = researcher_with_papers["client"]
    pid = researcher_with_papers["project_id"]
    fid = researcher_with_papers["paper_ids"][0]
    paper_ids = researcher_with_papers["paper_ids"]

    monkeypatch.setattr(
        server.project_research_service,
        "ai_gateway",
        _MockGateway(fid),
    )

    resp = client.post(f"/api/projects/{pid}/research", json={"preset": "evidence"})
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["kind"] == "research"
    assert body["status"] == "done"
    assert body["claims"]
    for claim in body["claims"]:
        for s in claim["support"]:
            assert s["paper_id"] in paper_ids

    listed = client.get(f"/api/projects/{pid}/research")
    assert listed.status_code == 200
    assert listed.get_json()["total"] >= 1
