"""Unit tests for auto evidence_extract enqueue (Paper Analysis 2.4)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from backend.evidence.services.auto_extract import maybe_enqueue_evidence_extract


def test_skips_without_project():
    uf = SimpleNamespace(user_id=1, project_id=None, path="x.pdf", size=10, meta_status="done", chunks=3)
    db = MagicMock()
    db.get.return_value = uf
    assert (
        maybe_enqueue_evidence_extract(
            db,
            user_id=1,
            file_id=9,
            UserFile=object,
            UploadJob=object,
            OutboxEvent=object,
        )
        is None
    )


def test_skips_when_not_research_ready():
    uf = SimpleNamespace(user_id=1, project_id=7, path="x.pdf", size=10, meta_status="pending", chunks=0)
    db = MagicMock()
    db.get.return_value = uf
    assert (
        maybe_enqueue_evidence_extract(
            db,
            user_id=1,
            file_id=9,
            UserFile=object,
            UploadJob=object,
            OutboxEvent=object,
        )
        is None
    )


def test_skips_when_active_job(monkeypatch):
    uf = SimpleNamespace(user_id=1, project_id=7, path="x.pdf", size=10, meta_status="done", chunks=5)
    db = MagicMock()
    db.get.return_value = uf
    monkeypatch.setattr(
        "backend.evidence.services.auto_extract.find_active_evidence_extract_job",
        lambda *a, **k: SimpleNamespace(id=42),
    )
    assert (
        maybe_enqueue_evidence_extract(
            db,
            user_id=1,
            file_id=9,
            UserFile=object,
            UploadJob=object,
            OutboxEvent=object,
        )
        is None
    )


def test_enqueues_when_ready(monkeypatch):
    uf = SimpleNamespace(user_id=1, project_id=7, path="x.pdf", size=10, meta_status="done", chunks=5)
    db = MagicMock()
    db.get.return_value = uf
    monkeypatch.setattr(
        "backend.evidence.services.auto_extract.find_active_evidence_extract_job",
        lambda *a, **k: None,
    )

    created = SimpleNamespace(id=99)

    def _fake_enqueue(**kwargs):
        assert kwargs["job_type"] == "evidence_extract"
        assert kwargs["payload"]["project_id"] == 7
        assert kwargs["payload"]["source"] == "auto_phase1"
        return created

    monkeypatch.setattr(
        "backend.evidence.services.auto_extract.enqueue_upload_job_with_outbox",
        lambda *a, **k: _fake_enqueue(**k),
    )
    job_id = maybe_enqueue_evidence_extract(
        db,
        user_id=1,
        file_id=9,
        UserFile=object,
        UploadJob=object,
        OutboxEvent=object,
    )
    assert job_id == 99
