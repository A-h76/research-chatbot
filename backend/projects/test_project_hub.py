"""Tests for ProjectService hub + research questions (Sprint A)."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import select

import server
from backend.projects import create_project_service


@pytest.fixture
def project_svc():
    return create_project_service(
        SessionLocal=server.SessionLocal,
        select=select,
        Project=server.Project,
        UserFile=server.UserFile,
        Note=server.Note,
        Memory=server.Memory,
        Conversation=server.Conversation,
        DerivedAnalysis=server.DerivedAnalysis,
        ProjectQuestion=server.ProjectQuestion,
        AnalysisPipelineResult=server.AnalysisPipelineResult,
    )


@pytest.fixture
def researcher():
    db = server.SessionLocal()
    try:
        user = server.User(
            name="Researcher",
            email=f"hub-{server.uuid.uuid4().hex[:8]}@test.local",
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


def test_hub_empty_project(researcher, project_svc):
    hub = project_svc.get_hub(researcher["project_id"], researcher["user_id"])
    assert hub is not None
    assert hub["project"]["name"] == "Thesis"
    assert hub["stats"]["papers"] == 0
    assert hub["stats"]["open_questions"] == 0
    assert hub["open_questions"] == []


def test_hub_includes_papers_notes_insights_questions(researcher, project_svc):
    uid = researcher["user_id"]
    pid = researcher["project_id"]
    db = server.SessionLocal()
    try:
        f = server.UserFile(
            user_id=uid,
            project_id=pid,
            name="paper.pdf",
            kind="document",
            title="Attention Is All You Need",
            authors="Vaswani",
            year="2017",
            reading_status="unread",
            meta_status="done",
            path="/tmp/x",
            size=10,
        )
        db.add(f)
        db.flush()
        note = server.Note(
            user_id=uid,
            project_id=pid,
            title="Method note",
            content="Transformers use self-attention.",
        )
        db.add(note)
        da = server.DerivedAnalysis(
            user_id=uid,
            project_id=pid,
            kind="compare",
            selection_hash="abc",
            file_ids=json.dumps([f.id]),
            data="{}",
            model="test",
        )
        db.add(da)
        q = server.ProjectQuestion(
            user_id=uid,
            project_id=pid,
            text="Do transformers outperform RNNs on long sequences?",
            status="open",
            source="manual",
        )
        db.add(q)
        db.commit()
    finally:
        db.close()

    hub = project_svc.get_hub(pid, uid)
    assert hub["stats"]["papers"] == 1
    assert hub["stats"]["notes"] == 1
    assert hub["stats"]["insights"] == 1
    assert hub["stats"]["open_questions"] == 1
    assert hub["open_questions"][0]["text"].startswith("Do transformers")
    assert any(a["kind"] == "question_open" for a in hub["unread_activity"])


def test_hub_not_found_wrong_user(researcher, project_svc):
    assert project_svc.get_hub(researcher["project_id"], user_id=99999) is None


def test_hub_http_endpoint(researcher):
    resp = researcher["client"].get(f"/api/projects/{researcher['project_id']}/hub")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["project"]["id"] == researcher["project_id"]
    assert "open_questions" in body


def test_hub_http_404(researcher):
    resp = researcher["client"].get("/api/projects/999999/hub")
    assert resp.status_code == 404


def test_get_file_includes_parent_project(researcher):
    uid = researcher["user_id"]
    pid = researcher["project_id"]
    db = server.SessionLocal()
    try:
        f = server.UserFile(
            user_id=uid,
            project_id=pid,
            name="child.pdf",
            kind="document",
            title="Child Paper",
            path="/tmp/y",
            size=1,
        )
        db.add(f)
        db.commit()
        fid = f.id
    finally:
        db.close()

    resp = researcher["client"].get(f"/api/files/{fid}")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["project"]["id"] == pid
    assert body["project"]["name"] == "Thesis"


def test_questions_crud_http(researcher):
    client = researcher["client"]
    pid = researcher["project_id"]

    create = client.post(
        f"/api/projects/{pid}/questions",
        json={"text": "What is the strongest evidence for efficacy?"},
    )
    assert create.status_code == 201, create.get_json()
    q = create.get_json()
    assert q["status"] == "open"
    qid = q["id"]

    listed = client.get(f"/api/projects/{pid}/questions")
    assert listed.status_code == 200
    assert listed.get_json()["total"] == 1

    hub = client.get(f"/api/projects/{pid}/hub").get_json()
    assert hub["stats"]["open_questions"] == 1

    patched = client.patch(
        f"/api/projects/{pid}/questions/{qid}",
        json={"status": "answered"},
    )
    assert patched.status_code == 200
    assert patched.get_json()["status"] == "answered"

    hub2 = client.get(f"/api/projects/{pid}/hub").get_json()
    assert hub2["stats"]["open_questions"] == 0

    deleted = client.delete(f"/api/projects/{pid}/questions/{qid}")
    assert deleted.status_code == 200
    assert client.get(f"/api/projects/{pid}/questions").get_json()["total"] == 0


def test_create_question_requires_text(researcher):
    client = researcher["client"]
    pid = researcher["project_id"]
    resp = client.post(f"/api/projects/{pid}/questions", json={"text": ""})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "text_required"


def test_insights_list_http(researcher):
    client = researcher["client"]
    pid = researcher["project_id"]
    uid = researcher["user_id"]
    db = server.SessionLocal()
    try:
        db.add(
            server.DerivedAnalysis(
                user_id=uid,
                project_id=pid,
                kind="gaps",
                selection_hash="xyz",
                file_ids="[]",
                data='{"preamble": "Field overview snippet"}',
                model="test",
            )
        )
        db.commit()
    finally:
        db.close()

    resp = client.get(f"/api/projects/{pid}/insights")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] == 1
    assert body["items"][0]["kind"] == "gaps"
    assert "Field overview" in body["items"][0]["preview"]
