"""Unit tests for Library Bridge parsers + import dedup."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.library.bibtex import parse_bibtex, to_bibtex
from backend.library.normalize import LibraryRecord, normalize_doi, title_year_key
from backend.library.ris import parse_ris, to_ris
from backend.library.service import LibraryImportService


SAMPLE_BIB = r"""
@article{smith2020,
  author = {Smith, Jane and Doe, John},
  title = {Attention Is Useful},
  journal = {Nature},
  year = {2020},
  doi = {10.1234/example.2020},
}
@inproceedings{lee2019,
  author = {Lee, Amy},
  title = {Another Paper},
  booktitle = {NeurIPS},
  year = {2019},
}
"""

SAMPLE_RIS = """
TY  - JOUR
AU  - Smith, Jane
AU  - Doe, John
TI  - Attention Is Useful
JO  - Nature
PY  - 2020
DO  - 10.1234/example.2020
ER  -

TY  - CONF
AU  - Lee, Amy
TI  - Another Paper
T2  - NeurIPS
PY  - 2019
ER  -
"""


def test_normalize_doi():
    assert normalize_doi("https://doi.org/10.1234/ABC") == "10.1234/ABC"
    assert normalize_doi("doi:10.1234/ABC") == "10.1234/ABC"


def test_parse_bibtex_roundtrip():
    records = parse_bibtex(SAMPLE_BIB)
    assert len(records) == 2
    assert records[0].doi == "10.1234/example.2020"
    assert "Smith" in records[0].authors
    assert records[0].year == "2020"
    blob = to_bibtex(records)
    assert "10.1234/example.2020" in blob
    again = parse_bibtex(blob)
    assert len(again) == 2


def test_parse_ris_roundtrip():
    records = parse_ris(SAMPLE_RIS)
    assert len(records) == 2
    assert records[0].normalized_doi() == "10.1234/example.2020"
    assert records[1].title == "Another Paper"
    blob = to_ris(records)
    assert "TY  -" in blob
    again = parse_ris(blob)
    assert len(again) == 2


def test_title_year_key():
    assert title_year_key("Hello, World!", "2020") == title_year_key("hello world", "2020")


def test_import_service_dedup_and_project():
    class Base(DeclarativeBase):
        pass

    class UserFile(Base):
        __tablename__ = "files"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer)
        project_id = Column(Integer, nullable=True)
        conversation_id = Column(Integer, nullable=True)
        name = Column(String(300))
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
        meta_status = Column(String(20), default="pending")
        metadata_source = Column(String(30), default="extracted")
        source_url = Column(String(500), default="")
        doi_verified = Column(Integer, default=0)
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

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    svc = LibraryImportService(Session, UserFile, Project, select, enrich_file_from_doi=None)
    records = parse_bibtex(SAMPLE_BIB)
    result = svc.import_records(1, records, create_project_name="My Import", enrich=False)
    assert result["ok"] is True
    assert result["created"] == 2
    assert result["project_id"] is not None

    # Second import — DOI + title/year dedup
    result2 = svc.import_records(1, records, enrich=False)
    assert result2["created"] == 0
    assert result2["skipped"] == 2

    # Same DOI in batch skipped
    dup = [
        LibraryRecord(title="A", doi="10.9/x", year="2021", source="bibtex"),
        LibraryRecord(title="B", doi="10.9/x", year="2021", source="bibtex"),
    ]
    result3 = svc.import_records(1, dup, enrich=False)
    assert result3["created"] == 1
    assert result3["skipped"] == 1
