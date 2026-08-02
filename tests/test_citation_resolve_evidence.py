"""Citation → EvidenceObject resolve bridge (Subsystem #5 insert-into-draft)."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
import os

os.environ.setdefault("BETA_INVITE_ONLY", "1")

import server
from backend.library.citation_routes import parenthetical_cite


def _client():
    return server.app.test_client()


def _login(client, user_id: int):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def test_parenthetical_cite_format():
    c = SimpleNamespace(authors="Smith, Jane; Doe, John", year="2020", title="T")
    assert parenthetical_cite(c) == "(Smith, 2020)"
    c2 = SimpleNamespace(authors="", year="", title="T")
    assert parenthetical_cite(c2) == "(Unknown, n.d.)"


def test_resolve_evidence_grounded_by_doi():
    uid = 8510
    db = server.SessionLocal()
    try:
        db.add(
            server.User(
                id=uid,
                email=f"cite{uid}@example.com",
                name="Cite User",
                created_at=datetime.now(timezone.utc),
            )
        )
        project = server.Project(user_id=uid, name="CiteP", emoji="C")
        db.add(project)
        db.flush()
        uf = server.UserFile(
            user_id=uid,
            project_id=project.id,
            name="paper.pdf",
            title="Effects of Drug X",
            path="/tmp/paper.pdf",
            size=10,
            meta_status="done",
            kind="document",
            doi="10.1000/cite-test",
        )
        db.add(uf)
        db.flush()
        ev = server.EvidenceObject(
            user_id=uid,
            project_id=project.id,
            file_id=uf.id,
            page=1,
            quote="Drug X reduces HbA1c",
            claim="Drug X reduces HbA1c",
            study_type="RCT",
            confidence_band="high",
            status="accepted",
            pipeline_version="2.2.0",
            content_hash=f"cite-ev-{uid}",
            provenance_json="{}",
        )
        db.add(ev)
        cit = server.Citation(
            user_id=uid,
            project_id=project.id,
            authors="Smith, A",
            title="Effects of Drug X",
            year="2021",
            doi="10.1000/cite-test",
        )
        db.add(cit)
        db.commit()
        project_id = project.id
        citation_id = cit.id
        evidence_id = ev.id
    finally:
        db.close()

    client = _client()
    _login(client, uid)
    resp = client.get(
        f"/api/citations/{citation_id}/resolve-evidence?project_id={project_id}"
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["grounded"] is True
    assert body["evidence_id"] == evidence_id
    assert body["insert_text"] == f"[#{evidence_id}]"
    assert body["parenthetical"] == "(Smith, 2021)"


def test_resolve_evidence_ungrounded_parenthetical():
    uid = 8511
    db = server.SessionLocal()
    try:
        db.add(
            server.User(
                id=uid,
                email=f"cite{uid}@example.com",
                name="Cite User 2",
                created_at=datetime.now(timezone.utc),
            )
        )
        project = server.Project(user_id=uid, name="CiteP2", emoji="C")
        db.add(project)
        db.flush()
        cit = server.Citation(
            user_id=uid,
            project_id=project.id,
            authors="Jones, B",
            title="Unrelated Paper",
            year="2019",
            doi="10.9999/no-match",
        )
        db.add(cit)
        db.commit()
        project_id = project.id
        citation_id = cit.id
    finally:
        db.close()

    client = _client()
    _login(client, uid)
    resp = client.get(
        f"/api/citations/{citation_id}/resolve-evidence?project_id={project_id}"
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["grounded"] is False
    assert body["evidence_id"] is None
    assert body["insert_text"] == "(Jones, 2019)"


def test_resolve_evidence_requires_project_id():
    uid = 8512
    db = server.SessionLocal()
    try:
        db.add(
            server.User(
                id=uid,
                email=f"cite{uid}@example.com",
                name="Cite User 3",
                created_at=datetime.now(timezone.utc),
            )
        )
        cit = server.Citation(
            user_id=uid,
            authors="A",
            title="T",
            year="2020",
        )
        db.add(cit)
        db.commit()
        citation_id = cit.id
    finally:
        db.close()

    client = _client()
    _login(client, uid)
    resp = client.get(f"/api/citations/{citation_id}/resolve-evidence")
    assert resp.status_code == 422
