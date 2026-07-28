"""Phase 1b — conflict-safe merge + sync apply tests."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.library.normalize import LibraryRecord
from backend.library.service import LibraryImportService
from backend.library.sync import (
    LibrarySyncService,
    has_research_asset,
    merge_metadata_into_existing,
    title_similarity,
)


def test_title_similarity():
    assert title_similarity("Hello World", "hello world") > 0.9
    assert title_similarity("Completely Different", "Another Thing") < 0.5


def test_merge_fills_empty_only_on_asset():
    uf = SimpleNamespace(
        id=1,
        title="Original Title About Transformers",
        authors="",
        year="",
        venue="",
        doi="",
        abstract="",
        source_url="",
        name="Original Title About Transformers",
        path="abc.pdf",
        size=1000,
        meta_status="done",
        external_provider="",
        external_item_id="",
    )
    assert has_research_asset(uf) is True
    rec = LibraryRecord(
        title="Totally Unrelated Paper Name",
        authors="Ada Lovelace",
        year="2020",
        doi="10.1/x",
        source="zotero",
        external_id="KEY1",
    )
    updated, conflicts = merge_metadata_into_existing(uf, rec, protect_asset=True)
    assert "authors" in updated
    assert "doi" in updated
    assert "title" not in updated  # protected
    assert "title" in conflicts
    assert uf.authors == "Ada Lovelace"


def test_merge_updates_stub_title_when_similar():
    uf = SimpleNamespace(
        id=2,
        title="Attention Is All You Need",
        authors="",
        year="",
        venue="",
        doi="",
        abstract="",
        source_url="",
        name="Attention Is All You Need",
        path="",
        size=0,
        meta_status="done",
        external_provider="",
        external_item_id="",
    )
    rec = LibraryRecord(
        title="Attention Is All You Need.",
        authors="Vaswani",
        year="2017",
        source="zotero",
        external_id="KEY2",
    )
    updated, conflicts = merge_metadata_into_existing(uf, rec, protect_asset=False)
    assert "title" in updated
    assert conflicts == []
    assert uf.year == "2017"


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
    kind = Column(String(30), default="document")
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
    metadata_source = Column(String(30), default="zotero")
    source_url = Column(String(500), default="")
    doi_verified = Column(Integer, default=0)
    external_provider = Column(String(30), default="")
    external_item_id = Column(String(120), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    name = Column(String(100))
    emoji = Column(String(8), default="")
    description = Column(Text, default="")


class LibraryConnection(Base):
    __tablename__ = "library_connections"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    provider = Column(String(30))
    status = Column(String(20), default="active")
    sync_cursor = Column(Text, default="")
    last_synced_at = Column(DateTime, nullable=True)


class LibrarySyncRun(Base):
    __tablename__ = "library_sync_runs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    connection_id = Column(Integer, nullable=True)
    provider = Column(String(30))
    status = Column(String(20), default="running")
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime, nullable=True)
    created_count = Column(Integer, default=0)
    updated_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    conflict_count = Column(Integer, default=0)
    cursor_before = Column(Text, default="")
    cursor_after = Column(Text, default="")
    error_text = Column(Text, default="")
    detail_json = Column(Text, default="{}")


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_apply_sync_creates_then_updates_without_touching_pdf():
    Session = _session()
    import_svc = LibraryImportService(Session, UserFile, Project, select, enrich_file_from_doi=None)
    sync_svc = LibrarySyncService(
        Session, UserFile, LibraryConnection, LibrarySyncRun, select, import_svc
    )

    first = sync_svc.apply_sync_records(
        1,
        [
            LibraryRecord(
                title="Paper A",
                authors="",
                year="2020",
                doi="10.1/a",
                source="zotero",
                external_id="A1",
            )
        ],
        source_tag="from-zotero",
    )
    assert first["created"] == 1

    # Attach a fake PDF
    db = Session()
    uf = db.get(UserFile, first["created_ids"][0])
    uf.path = "x.pdf"
    uf.size = 99
    db.commit()
    db.close()

    second = sync_svc.apply_sync_records(
        1,
        [
            LibraryRecord(
                title="Completely Different Remote Title",
                authors="New Author",
                year="2021",
                doi="10.1/a",
                source="zotero",
                external_id="A1",
            )
        ],
    )
    assert second["created"] == 0
    assert second["updated"] >= 1
    assert second["conflicts"] >= 1

    db = Session()
    uf = db.execute(select(UserFile).where(UserFile.user_id == 1)).scalar_one()
    assert uf.path == "x.pdf"
    assert uf.size == 99
    assert uf.authors == "New Author"
    assert uf.title == "Paper A"  # protected
    db.close()


def test_zotero_adapter_synchronize_shape(monkeypatch):
    from backend.library.adapters import get_adapter

    def fake_since(*args, **kwargs):
        return (
            [
                LibraryRecord(
                    title="Inc",
                    doi="10.1/inc",
                    source="zotero",
                    external_id="Z1",
                )
            ],
            42,
        )

    monkeypatch.setattr(
        "backend.library.zotero.fetch_items_since",
        fake_since,
    )
    adapter = get_adapter("zotero")
    assert adapter.capabilities().incremental_sync is True
    out = adapter.synchronize(
        access_token="t",
        access_secret="s",
        external_user_id="1",
        sync_cursor='{"library_version": 10}',
    )
    assert out["fetched"] == 1
    import json
    assert json.loads(out["sync_cursor"])["library_version"] == 42
