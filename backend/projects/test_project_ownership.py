"""HTTP ownership / IDOR gates for personal projects (V1 #19)."""

from __future__ import annotations

import server


def _make_user(email_prefix: str):
    db = server.SessionLocal()
    try:
        user = server.User(
            name=email_prefix,
            email=f"{email_prefix}-{server.uuid.uuid4().hex[:8]}@test.local",
            picture="",
            auth_provider="dev",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id
    finally:
        db.close()


def _make_project(user_id: int, name: str = "Owner Project"):
    db = server.SessionLocal()
    try:
        project = server.Project(
            user_id=user_id,
            name=name,
            emoji="📁",
            description="private",
            instructions="",
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project.id
    finally:
        db.close()


def _client_as(user_id: int):
    client = server.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
    return client


def test_list_excludes_other_users_projects():
    owner_id = _make_user("owner")
    other_id = _make_user("other")
    owner_pid = _make_project(owner_id, "Owner Only")
    other_pid = _make_project(other_id, "Other Only")

    owner_list = _client_as(owner_id).get("/api/projects").get_json()
    owner_ids = {p["id"] for p in owner_list}
    assert owner_pid in owner_ids
    assert other_pid not in owner_ids

    other_list = _client_as(other_id).get("/api/projects").get_json()
    other_ids = {p["id"] for p in other_list}
    assert other_pid in other_ids
    assert owner_pid not in other_ids


def test_crud_idor_returns_404():
    owner_id = _make_user("crud-owner")
    other_id = _make_user("crud-other")
    pid = _make_project(owner_id)
    client = _client_as(other_id)

    assert client.get(f"/api/projects/{pid}").status_code == 404
    assert (
        client.patch(f"/api/projects/{pid}", json={"name": "Hijacked"}).status_code
        == 404
    )
    assert client.delete(f"/api/projects/{pid}").status_code == 404

    # Owner still owns the intact project
    ok = _client_as(owner_id).get(f"/api/projects/{pid}")
    assert ok.status_code == 200
    assert ok.get_json()["name"] == "Owner Project"


def test_hub_questions_insights_idor_returns_404():
    owner_id = _make_user("hub-owner")
    other_id = _make_user("hub-other")
    pid = _make_project(owner_id)
    client = _client_as(other_id)

    assert client.get(f"/api/projects/{pid}/hub").status_code == 404
    assert client.get(f"/api/projects/{pid}/insights").status_code == 404
    assert client.get(f"/api/projects/{pid}/questions").status_code == 404
    assert (
        client.post(
            f"/api/projects/{pid}/questions",
            json={"text": "Should not create"},
        ).status_code
        == 404
    )


def test_research_and_memory_idor_returns_404():
    owner_id = _make_user("ws-owner")
    other_id = _make_user("ws-other")
    pid = _make_project(owner_id)
    client = _client_as(other_id)

    assert client.get(f"/api/projects/{pid}/research").status_code == 404
    assert (
        client.post(
            f"/api/projects/{pid}/research",
            json={"preset": "evidence"},
        ).status_code
        == 404
    )
    assert client.get(f"/api/projects/{pid}/memory").status_code == 404
