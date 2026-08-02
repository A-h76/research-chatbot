"""Library sync worker path — enqueue 202 + handler roundtrip (#9)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.library.sync import LibrarySyncService
from backend.library.normalize import LibraryRecord


class _Base:
    pass


def _services(tmp_path):
    from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, select
    from sqlalchemy.orm import DeclarativeBase, sessionmaker

    from backend.library.models import create_library_connection_model, create_library_sync_run_model
    from backend.library.service import LibraryImportService

    class Base(DeclarativeBase):
        pass

    class UserFile(Base):
        __tablename__ = "files"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer)
        project_id = Column(Integer, nullable=True)
        conversation_id = Column(Integer, nullable=True)
        name = Column(String(300), default="")
        mime = Column(String(100), default="")
        kind = Column(String(20), default="document")
        path = Column(String(500), default="")
        size = Column(Integer, default=0)
        title = Column(String(500), default="")
        authors = Column(String(1000), default="")
        year = Column(String(10), default="")
        venue = Column(String(300), default="")
        doi = Column(String(200), default="")
        abstract = Column(Text, default="")
        reading_status = Column(String(20), default="unread")
        tags = Column(Text, default="[]")
        meta_status = Column(String(20), default="done")
        metadata_source = Column(String(30), default="")
        source_url = Column(String(500), default="")
        external_provider = Column(String(30), default="")
        external_item_id = Column(String(120), default="")
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    LibraryConnection = create_library_connection_model(Base)
    LibrarySyncRun = create_library_sync_run_model(Base)

    engine = create_engine(f"sqlite:///{tmp_path / 'sync_w.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    imp = LibraryImportService(Session, UserFile, None, select, enrich_file_from_doi=None)
    sync = LibrarySyncService(Session, UserFile, LibraryConnection, LibrarySyncRun, select, imp)
    return Session, UserFile, LibraryConnection, LibrarySyncRun, sync, select


def test_has_active_run_detects_queued(tmp_path):
    Session, UserFile, LibraryConnection, LibrarySyncRun, sync, select = _services(tmp_path)
    run_id = sync.start_run(1, None, "zotero", "", status="queued", detail={"job_id": 9})
    active = sync.has_active_run(1, "zotero")
    assert active is not None
    assert active["id"] == run_id
    assert active["status"] == "queued"
    assert active["job_id"] == 9


def test_enqueue_library_sync_returns_202(researcher, monkeypatch):
    """HTTP returns immediately with job_id — does not block on adapter fetch."""
    import server
    from security.token_crypto import seal_secret

    client = researcher.client
    db = researcher.db
    user = researcher.user

    # Slow adapter would hang in-request sync; async path must return first.
    called = {"n": 0}

    def _slow_sync(**kwargs):
        called["n"] += 1
        import time

        time.sleep(2.0)
        return {"records": [], "sync_cursor": "{}", "fetched": 0}

    monkeypatch.setattr(
        "backend.library.adapters.get_adapter",
        lambda name: SimpleNamespace(
            synchronize=_slow_sync,
            capabilities=lambda: SimpleNamespace(incremental_sync=True),
        ),
    )

    key = server.app.secret_key or "test"
    conn = server.LibraryConnection(
        user_id=user.id,
        provider="zotero",
        status="active",
        access_token=seal_secret("tok", secret_key=key),
        access_secret=seal_secret("sec", secret_key=key),
        external_user_id="42",
        sync_cursor="",
    )
    db.add(conn)
    db.commit()

    import time

    t0 = time.perf_counter()
    resp = client.post("/api/library/zotero/sync", json={})
    elapsed = time.perf_counter() - t0
    assert resp.status_code == 202, resp.get_json()
    body = resp.get_json()
    assert body["status"] == "queued"
    assert body["job_id"]
    assert body["sync_run_id"]
    # Must return before the 2s adapter sleep (proves not in-request).
    assert elapsed < 1.0, f"sync blocked HTTP for {elapsed:.2f}s"
    assert called["n"] == 0  # adapter not invoked on enqueue

    job = db.get(server.UploadJob, body["job_id"])
    assert job is not None
    assert job.job_type == "library_sync"
    assert job.status == "pending"

    # Inline sync still available for tests
    monkeypatch.setattr(
        "backend.library.adapters.get_adapter",
        lambda name: SimpleNamespace(
            synchronize=lambda **kw: {"records": [], "sync_cursor": "{}", "fetched": 0},
            capabilities=lambda: SimpleNamespace(incremental_sync=True),
        ),
    )
    # Finish the queued run so inline doesn't 409
    sync_run = db.get(server.LibrarySyncRun, body["sync_run_id"])
    sync_run.status = "ok"
    sync_run.finished_at = datetime.now(timezone.utc)
    db.commit()

    inline = client.post("/api/library/zotero/sync", json={"sync": True})
    assert inline.status_code == 200, inline.get_json()


def test_library_sync_handler_roundtrip(researcher, monkeypatch):
    import server
    import worker
    from security.token_crypto import seal_secret

    db = researcher.db
    user = researcher.user
    key = server.app.secret_key or "test"
    conn = server.LibraryConnection(
        user_id=user.id,
        provider="zotero",
        status="active",
        access_token=seal_secret("tok", secret_key=key),
        access_secret=seal_secret("sec", secret_key=key),
        external_user_id="42",
        sync_cursor="",
    )
    db.add(conn)
    db.flush()

    run = server.LibrarySyncRun(
        user_id=user.id,
        connection_id=conn.id,
        provider="zotero",
        status="queued",
        cursor_before="",
        detail_json="{}",
    )
    db.add(run)
    db.flush()

    job = server.UploadJob(
        file_id=None,
        user_id=user.id,
        job_type="library_sync",
        status="running",
    )
    db.add(job)
    db.flush()
    db.add(
        server.OutboxEvent(
            aggregate_type="upload_job",
            aggregate_id=job.id,
            event_type="job.enqueued",
            payload=json.dumps(
                {
                    "type": "library_sync",
                    "provider": "zotero",
                    "connection_id": conn.id,
                    "sync_run_id": run.id,
                    "limit": 50,
                    "cursor_before": "",
                }
            ),
        )
    )
    db.commit()

    monkeypatch.setattr(
        "backend.library.adapters.get_adapter",
        lambda name: SimpleNamespace(
            synchronize=lambda **kw: {
                "records": [
                    LibraryRecord(
                        title="From Worker",
                        authors="Ada",
                        year="2023",
                        doi="10.9/worker",
                        source="zotero",
                        external_id="ZW1",
                    )
                ],
                "sync_cursor": '{"library_version": 3}',
                "fetched": 1,
            },
            capabilities=lambda: SimpleNamespace(incremental_sync=True),
        ),
    )

    worker._handle_library_sync(db, job)
    db.refresh(run)
    assert run.status == "ok"
    assert (run.created_count or 0) >= 1
