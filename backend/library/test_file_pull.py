"""Ref-mgr PDF pull — adapter → stub attach → import enqueue (#10)."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


def _db(tmp_path):
    from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, select
    from sqlalchemy.orm import DeclarativeBase, sessionmaker

    class Base(DeclarativeBase):
        pass

    class UserFile(Base):
        __tablename__ = "files"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer)
        name = Column(String(300), default="")
        mime = Column(String(100), default="")
        kind = Column(String(20), default="document")
        path = Column(String(500), default="")
        size = Column(Integer, default=0)
        title = Column(String(500), default="")
        meta_status = Column(String(20), default="done")
        checksum_sha256 = Column(String(64), default="")
        external_provider = Column(String(30), default="")
        external_item_id = Column(String(120), default="")
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    engine = create_engine(f"sqlite:///{tmp_path / 'pull.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session, UserFile, select


def test_pull_pdfs_for_provider_attaches_and_enqueues(tmp_path, monkeypatch):
    from backend.library import file_pull

    Session, UserFile, select = _db(tmp_path)
    db = Session()
    stub = UserFile(
        user_id=7,
        title="Stub Paper",
        name="Stub Paper",
        path="",
        size=0,
        meta_status="done",
        external_provider="zotero",
        external_item_id="ITEM99",
    )
    db.add(stub)
    db.commit()
    db.refresh(stub)

    monkeypatch.setattr(
        "backend.library.file_pull.get_adapter",
        lambda name: SimpleNamespace(
            capabilities=lambda: SimpleNamespace(file_import=True),
            import_files=lambda **kw: {
                "downloaded": [
                    {
                        "external_id": "ITEM99",
                        "filename": "ITEM99.pdf",
                        "content_type": "application/pdf",
                        "data": b"%PDF-1.4 test-content",
                    }
                ],
                "skipped": [],
                "errors": [],
                "provider": "zotero",
            },
        ),
    )

    storage = MagicMock()
    storage.sha256_file.return_value = "abc123"
    storage.upload.return_value = None
    enqueued = []

    def _enq(db_, uid, fid):
        enqueued.append((uid, fid))

    upload_dir = str(tmp_path / "uploads")
    result = file_pull.pull_pdfs_for_provider(
        db=db,
        UserFile=UserFile,
        select_fn=select,
        provider="zotero",
        user_id=7,
        token_kwargs={
            "access_token": "t",
            "access_secret": "s",
            "external_user_id": "1",
        },
        storage=storage,
        upload_dir=upload_dir,
        enqueue_import=_enq,
        limit=10,
    )
    db.commit()
    db.refresh(stub)

    assert result["ok"] is True
    assert result["pulled"] == 1
    assert result["queued"] == 1
    assert stub.path
    assert stub.size > 0
    assert stub.meta_status == "pending"
    assert enqueued == [(7, stub.id)]
    storage.upload.assert_called_once()
    db.close()


def test_pull_skips_when_no_pdf_on_provider(tmp_path, monkeypatch):
    from backend.library import file_pull

    Session, UserFile, select = _db(tmp_path)
    db = Session()
    stub = UserFile(
        user_id=1,
        title="No PDF",
        path="",
        size=0,
        external_provider="zotero",
        external_item_id="X",
    )
    db.add(stub)
    db.commit()

    monkeypatch.setattr(
        "backend.library.file_pull.get_adapter",
        lambda name: SimpleNamespace(
            capabilities=lambda: SimpleNamespace(file_import=True),
            import_files=lambda **kw: {
                "downloaded": [],
                "skipped": [{"external_id": "X", "reason": "no_pdf"}],
                "errors": [],
            },
        ),
    )
    result = file_pull.pull_pdfs_for_provider(
        db=db,
        UserFile=UserFile,
        select_fn=select,
        provider="zotero",
        user_id=1,
        token_kwargs={"access_token": "t", "access_secret": "s", "external_user_id": "1"},
        storage=MagicMock(),
        upload_dir=str(tmp_path / "u"),
        enqueue_import=lambda *a: None,
    )
    assert result["pulled"] == 0
    assert result["skipped"][0]["reason"] == "no_pdf"
    db.close()
