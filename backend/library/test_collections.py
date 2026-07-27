"""Tests for Library collections (Phase 1.6)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint, create_engine, select
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.library.collections import CollectionService
from backend.library.normalize import LibraryRecord
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
    metadata_source = Column(String(30), default="extracted")
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
    emoji = Column(String(16), default="📁")
    description = Column(Text, default="")
    instructions = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class LibraryCollection(Base):
    __tablename__ = "library_collections"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    name = Column(String(200))
    description = Column(Text, default="")
    parent_id = Column(Integer, nullable=True)
    external_id = Column(String(100), default="")
    source = Column(String(30), default="manual")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class LibraryCollectionPaper(Base):
    __tablename__ = "library_collection_papers"
    __table_args__ = (UniqueConstraint("collection_id", "file_id"),)
    id = Column(Integer, primary_key=True)
    collection_id = Column(Integer)
    file_id = Column(Integer)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def _services():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    coll = CollectionService(Session, LibraryCollection, LibraryCollectionPaper, UserFile, select)
    imp = LibraryImportService(
        Session, UserFile, Project, select, collection_service=coll, enrich_file_from_doi=None
    )
    return Session, coll, imp


def test_create_list_delete_collection():
    _, coll, _ = _services()
    c = coll.create_collection(1, "Machine Learning", description="ML papers")
    assert c and c["name"] == "Machine Learning"
    assert c["paper_count"] == 0

    items = coll.list_collections(1)
    assert len(items) == 1

    assert coll.delete_collection(1, c["id"]) is True
    assert coll.list_collections(1) == []


def test_add_remove_papers():
    Session, coll, _ = _services()
    db = Session()
    f1 = UserFile(user_id=1, title="Paper A", name="a", kind="document")
    f2 = UserFile(user_id=1, title="Paper B", name="b", kind="document")
    db.add_all([f1, f2])
    db.commit()
    fid1, fid2 = f1.id, f2.id
    db.close()

    c = coll.create_collection(1, "CV")
    result = coll.add_papers(1, c["id"], [fid1, fid2, fid1])
    assert result["added"] == 2
    assert result["paper_count"] == 2

    ids = coll.file_ids_in_collection(1, c["id"])
    assert set(ids) == {fid1, fid2}

    rem = coll.remove_papers(1, c["id"], [fid1])
    assert rem["removed"] == 1
    assert rem["paper_count"] == 1


def test_import_creates_zotero_collection_and_membership():
    _, coll, imp = _services()
    records = [
        LibraryRecord(
            title="Attention Is All You Need",
            authors="Vaswani",
            year="2017",
            doi="10.5555/3295222.3295349",
            source="zotero",
            collection_keys=["ABCD1234"],
            collection_name="Transformers",
        ),
        LibraryRecord(
            title="BERT",
            authors="Devlin",
            year="2019",
            doi="10.18653/v1/N19-1423",
            source="zotero",
            collection_keys=["ABCD1234"],
            collection_name="Transformers",
        ),
    ]
    result = imp.import_records(1, records, enrich=False)
    assert result["ok"] is True
    assert result["created"] == 2
    assert result["collection_ids"]
    cid = result["collection_ids"][0]
    folder = coll.get_collection(1, cid)
    assert folder["name"] == "Transformers"
    assert folder["source"] == "zotero"
    assert folder["external_id"] == "ABCD1234"
    assert folder["paper_count"] == 2

    # Re-import — dedupe papers but still in collection
    result2 = imp.import_records(1, records, enrich=False)
    assert result2["created"] == 0
    assert result2["skipped"] == 2
    folder = coll.get_collection(1, cid)
    assert folder["paper_count"] == 2


def test_get_or_create_external_idempotent():
    _, coll, _ = _services()
    a = coll.get_or_create_external(1, name="ML", external_id="Z1", source="zotero")
    b = coll.get_or_create_external(1, name="Machine Learning", external_id="Z1", source="zotero")
    assert a["id"] == b["id"]
    assert b["name"] == "Machine Learning"
