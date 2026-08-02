"""Phase 1c — research readiness, health, duplicates."""

from __future__ import annotations

from types import SimpleNamespace

from backend.library.health import find_duplicate_groups, merge_duplicate_files
from backend.library.readiness import research_readiness, readiness_payload


def _stub(**kwargs):
    defaults = dict(
        path="",
        size=0,
        meta_status="done",
        chunks=[],
        title="",
        authors="",
        year="",
        venue="",
        doi="",
        abstract="",
        name="paper",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_readiness_metadata_only_even_when_meta_done():
    uf = _stub(path="", size=0, meta_status="done", chunks=[1, 2])
    assert research_readiness(uf) == "metadata_only"
    assert readiness_payload(uf)["has_pdf"] is False


def test_readiness_pdf_attached_while_pending():
    uf = _stub(path="a.pdf", size=100, meta_status="pending")
    assert research_readiness(uf) == "pdf_attached"


def test_readiness_analysed_without_chunks():
    uf = _stub(path="a.pdf", size=100, meta_status="done", chunks=[])
    assert research_readiness(uf) == "analysed"


def test_readiness_research_ready_with_chunks():
    uf = _stub(path="a.pdf", size=100, meta_status="done", chunks=[1, 2, 3])
    assert research_readiness(uf, chunk_count=3) == "research_ready"
    assert readiness_payload(uf, chunk_count=3)["research_readiness_label"] == "Research ready"


def test_build_library_health_need_pdf_and_counts(tmp_path):
    from sqlalchemy import Column, Integer, String, Text, create_engine, select
    from sqlalchemy.orm import DeclarativeBase, sessionmaker

    from backend.library.health import build_library_health

    class Base(DeclarativeBase):
        pass

    class UserFile(Base):
        __tablename__ = "files"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer)
        kind = Column(String(40), default="document")
        project_id = Column(Integer, nullable=True)
        title = Column(String(500), default="")
        name = Column(String(300), default="")
        path = Column(String(500), default="")
        size = Column(Integer, default=0)
        meta_status = Column(String(20), default="done")
        chunks = []

    engine = create_engine(f"sqlite:///{tmp_path / 'h.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add_all(
        [
            UserFile(user_id=1, kind="document", title="Stub", path="", size=0, meta_status="done"),
            UserFile(
                user_id=1,
                kind="document",
                title="Ready",
                path="r.pdf",
                size=10,
                meta_status="done",
            ),
            UserFile(
                user_id=1,
                kind="document",
                title="Pending",
                path="p.pdf",
                size=10,
                meta_status="pending",
            ),
        ]
    )
    db.commit()
    # Monkey-patch chunks on ready file via instance after load
    ready = db.execute(select(UserFile).where(UserFile.title == "Ready")).scalar_one()
    ready.chunks = [1, 2]

    health = build_library_health(db, UserFile, select, 1)
    assert health["total"] == 3
    assert health["need_pdf"] == 1
    assert health["processing"] == 1
    assert health["by_readiness"]["metadata_only"] == 1
    assert health["research_ready"] >= 1
    db.close()


def test_find_duplicate_groups_by_doi(tmp_path):
    from sqlalchemy import Column, Integer, String, Text, create_engine, select
    from sqlalchemy.orm import DeclarativeBase, sessionmaker

    class Base(DeclarativeBase):
        pass

    class UserFile(Base):
        __tablename__ = "files"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer)
        kind = Column(String(40), default="document")
        project_id = Column(Integer, nullable=True)
        title = Column(String(500), default="")
        name = Column(String(300), default="")
        authors = Column(Text, default="")
        year = Column(String(20), default="")
        venue = Column(String(300), default="")
        doi = Column(String(200), default="")
        abstract = Column(Text, default="")
        path = Column(String(500), default="")
        size = Column(Integer, default=0)
        checksum_sha256 = Column(String(64), default="")
        meta_status = Column(String(20), default="done")
        source_url = Column(Text, default="")
        metadata_source = Column(String(40), default="")
        external_provider = Column(String(40), default="")
        external_item_id = Column(String(120), default="")

    engine = create_engine(f"sqlite:///{tmp_path / 't.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add_all(
        [
            UserFile(user_id=1, kind="document", title="A", doi="10.1/x", path="", size=0),
            UserFile(user_id=1, kind="document", title="A copy", doi="https://doi.org/10.1/x", path="p.pdf", size=9),
            UserFile(user_id=1, kind="document", title="Other", doi="10.2/y", path="", size=0),
        ]
    )
    db.commit()

    groups = find_duplicate_groups(db, UserFile, select, 1)
    assert len(groups) == 1
    g = groups[0]
    assert g["reason"] == "doi"
    assert len(g["file_ids"]) == 2
    # Prefer the row with PDF as keep
    assert g["keep_id"] == g["file_ids"][0]
    keep = db.get(UserFile, g["keep_id"])
    assert keep.path == "p.pdf"
    db.close()


def test_merge_duplicate_files_fills_empty_and_deletes(tmp_path):
    from sqlalchemy import Column, Integer, String, Text, create_engine
    from sqlalchemy.orm import DeclarativeBase, sessionmaker

    class Base(DeclarativeBase):
        pass

    class UserFile(Base):
        __tablename__ = "files"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer)
        kind = Column(String(40), default="document")
        title = Column(String(500), default="")
        name = Column(String(300), default="")
        authors = Column(Text, default="")
        year = Column(String(20), default="")
        venue = Column(String(300), default="")
        doi = Column(String(200), default="")
        abstract = Column(Text, default="")
        path = Column(String(500), default="")
        size = Column(Integer, default=0)
        mime = Column(String(100), default="")
        checksum_sha256 = Column(String(64), default="")
        meta_status = Column(String(20), default="done")
        source_url = Column(Text, default="")
        metadata_source = Column(String(40), default="")
        external_provider = Column(String(40), default="")
        external_item_id = Column(String(120), default="")

    engine = create_engine(f"sqlite:///{tmp_path / 'm.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    keep = UserFile(
        user_id=1,
        title="Keep Me",
        authors="",
        year="",
        doi="10.1/x",
        path="keep.pdf",
        size=10,
    )
    other = UserFile(
        user_id=1,
        title="Keep Me",
        authors="Ada",
        year="2020",
        doi="10.1/x",
        path="",
        size=0,
    )
    db.add_all([keep, other])
    db.commit()
    kid, oid = keep.id, other.id

    result = merge_duplicate_files(
        db, UserFile, 1, keep_id=kid, merge_ids=[oid], delete_merged=True
    )
    assert result["ok"] is True
    assert oid in result["merged_ids"]
    kept = db.get(UserFile, kid)
    assert kept.authors == "Ada"
    assert kept.year == "2020"
    assert kept.path == "keep.pdf"
    assert db.get(UserFile, oid) is None
    db.close()
