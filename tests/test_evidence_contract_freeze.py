"""A-402 freeze guards: RI envelope + error shape must stay compatible."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os

os.environ.setdefault("BETA_INVITE_ONLY", "1")

import server

from backend.evidence.envelope import stamp_ri_envelope
from backend.evidence.objects import serialize_evidence_object


RI_ENVELOPE_REQUIRED = frozenset(
    {"query", "objects", "total", "truncated", "stage", "timing_ms", "versions"}
)

EVIDENCE_DTO_REQUIRED = frozenset(
    {
        "id",
        "user_id",
        "project_id",
        "file_id",
        "paper_id",
        "page",
        "char_start",
        "char_end",
        "section",
        "quote",
        "claim",
        "study_type",
        "study_quality",
        "supports",
        "contradicts",
        "limitations",
        "confidence_band",
        "status",
        "pipeline_version",
        "created_by",
        "content_hash",
        "supersedes_id",
        "provenance",
        "source_kg_node_id",
        "created_at",
        "updated_at",
    }
)


def _client():
    return server.app.test_client()


def _login(client, user_id: int):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _seed(user_id: int):
    db = server.SessionLocal()
    try:
        db.add(
            server.User(
                id=user_id,
                email=f"a402-{user_id}@example.com",
                name=f"A402 {user_id}",
                created_at=datetime.now(timezone.utc),
            )
        )
        project = server.Project(user_id=user_id, name=f"A{user_id}", emoji="A")
        db.add(project)
        db.flush()
        db.commit()
        return {"project_id": project.id}
    finally:
        db.close()


def test_ri_envelope_required_keys():
    out = stamp_ri_envelope(
        {
            "query": {"intent": "list_project"},
            "objects": [],
            "total": 0,
            "truncated": False,
            "stage": "retrieval",
            "retrieval_version": "1.0.0",
        },
        timing_ms=1.2,
    )
    assert RI_ENVELOPE_REQUIRED.issubset(out.keys())
    assert out["versions"]["retrieval"] == "1.0.0"
    assert "items" not in out


def test_evidence_object_dto_required_keys():
    class Row:
        id = 1
        user_id = 2
        project_id = 3
        file_id = 4
        page = 5
        char_start = None
        char_end = None
        section = ""
        quote = "q"
        claim = "c"
        study_type = ""
        study_quality = ""
        supports_json = "[]"
        contradicts_json = "[]"
        limitations_json = "[]"
        confidence_band = "high"
        status = "accepted"
        pipeline_version = "2.2.0"
        created_by = "pipeline"
        content_hash = "abc"
        supersedes_id = None
        provenance_json = "{}"
        source_kg_node_id = ""
        created_at = None
        updated_at = None

    dto = serialize_evidence_object(Row())
    assert EVIDENCE_DTO_REQUIRED.issubset(dto.keys())
    assert dto["paper_id"] == dto["file_id"] == 4
    assert isinstance(dto["provenance"], dict)
    assert isinstance(dto["supports"], list)


def test_validation_error_shape_is_error_detail():
    seeded = _seed(8402)
    client = _client()
    _login(client, 8402)
    resp = client.post(
        "/api/evidence/search",
        json={
            "intent": "support_sentence",
            "scope": {"project_id": seeded["project_id"]},
            "model": "gpt-4o",
        },
    )
    assert resp.status_code == 422
    body = resp.get_json()
    assert set(body.keys()) >= {"error", "detail"}
    assert body["error"] == "validation_error"
    assert "data" not in body
    assert "errors" not in body


def test_list_evidence_uses_items_not_objects_envelope():
    seeded = _seed(8403)
    client = _client()
    _login(client, 8403)
    resp = client.get(f"/api/projects/{seeded['project_id']}/evidence")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "items" in body
    assert "total" in body
    assert "count" in body
    assert "objects" not in body
