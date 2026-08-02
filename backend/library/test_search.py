"""Tests for library search (Phase 1.5)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.library.search import (
    LibrarySearchParams,
    facets_for_user,
    parse_field_query,
    search_library,
)


class Base(DeclarativeBase):
    pass


class UserFile(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    project_id = Column(Integer, nullable=True)
    name = Column(String(300))
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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def _seed(session):
    now = datetime.now(timezone.utc)
    rows = [
        UserFile(
            user_id=1,
            title="Attention Is All You Need",
            authors="Vaswani, Ashish",
            year="2017",
            venue="NeurIPS",
            doi="10.5555/3295222.3295349",
            tags='["from-zotero", "nlp"]',
            metadata_source="zotero",
            reading_status="read",
            created_at=now - timedelta(days=100),
        ),
        UserFile(
            user_id=1,
            title="Deep Residual Learning",
            authors="He, Kaiming",
            year="2016",
            venue="CVPR",
            doi="10.1109/CVPR.2016.90",
            tags='["from-bibtex", "cv"]',
            metadata_source="bibtex",
            reading_status="unread",
            created_at=now - timedelta(days=5),
        ),
        UserFile(
            user_id=1,
            title="Uploaded PDF",
            authors="Local Author",
            year="2024",
            venue="ArXiv",
            path="/uploads/x.pdf",
            size=1000,
            metadata_source="extracted",
            reading_status="reading",
            created_at=now - timedelta(days=1),
        ),
        UserFile(
            user_id=2,
            title="Other user paper",
            authors="Someone",
            year="2020",
        ),
    ]
    session.add_all(rows)
    session.commit()


def test_parse_field_query():
    rest, fields = parse_field_query("author:smith doi:10.1234/x attention")
    assert fields["author"] == "smith"
    assert fields["doi"] == "10.1234/x"
    assert rest == "attention"


def test_search_by_doi_and_author():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    _seed(db)

    params = LibrarySearchParams(user_id=1, doi="10.1109", limit=50)
    total, rows = search_library(db, UserFile, params)
    assert total == 1
    assert "Residual" in rows[0].title

    params = LibrarySearchParams(user_id=1, author="Vaswani", limit=50)
    total, rows = search_library(db, UserFile, params)
    assert total == 1
    assert "Attention" in rows[0].title

    db.close()


def test_search_need_pdf_stubs_only():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add_all(
        [
            UserFile(
                user_id=1,
                kind="document",
                title="Stub",
                name="s",
                path="",
                size=0,
                meta_status="done",
            ),
            UserFile(
                user_id=1,
                kind="document",
                title="Has PDF",
                name="p",
                path="x.pdf",
                size=12,
                meta_status="done",
            ),
        ]
    )
    db.commit()

    total, rows = search_library(
        db, UserFile, LibrarySearchParams(user_id=1, need_pdf=True, limit=50)
    )
    assert total == 1
    assert rows[0].title == "Stub"
    db.close()


def test_search_import_source_and_year():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    _seed(db)

    params = LibrarySearchParams(user_id=1, import_source="zotero", limit=50)
    total, _ = search_library(db, UserFile, params)
    assert total == 1

    params = LibrarySearchParams(user_id=1, year="2016", limit=50)
    total, rows = search_library(db, UserFile, params)
    assert total == 1
    assert rows[0].year == "2016"

    params = LibrarySearchParams(user_id=1, import_source="upload", limit=50)
    total, rows = search_library(db, UserFile, params)
    assert total == 1
    assert rows[0].path

    db.close()


def test_search_pagination():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    _seed(db)

    params = LibrarySearchParams(user_id=1, limit=1, offset=0, sort="title")
    total, rows = search_library(db, UserFile, params)
    assert total == 3
    assert len(rows) == 1

    params.offset = 1
    _, rows2 = search_library(db, UserFile, params)
    assert len(rows2) == 1
    assert rows[0].id != rows2[0].id

    db.close()


def test_facets():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    _seed(db)
    f = facets_for_user(db, UserFile, 1)
    assert f["total"] == 3
    assert f["reading_status"]["read"] == 1
    assert f["import_source"].get("zotero") == 1
    db.close()
