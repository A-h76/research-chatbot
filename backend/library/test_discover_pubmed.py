"""Discover PubMed import — Golden Rule wiring (#22)."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from backend.library.discover_routes import create_discover_blueprint
from backend.scholarly.pubmed import PubmedWork


class _FakeScalars:
    def __init__(self, row=None):
        self._row = row

    def first(self):
        return self._row


class _FakeResult:
    def __init__(self, row=None):
        self._row = row

    def scalars(self):
        return _FakeScalars(self._row)


class FakeDB:
    def __init__(self):
        self.added = []
        self.committed = False
        self._id = 100

    def execute(self, *_a, **_k):
        return _FakeResult(None)

    def get(self, *_a, **_k):
        return None

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = self._id
            self._id += 1
        self.added.append(obj)

    def flush(self):
        pass

    def refresh(self, obj):
        pass

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

    def close(self):
        pass


@pytest.fixture
def discover_app(monkeypatch):
    from flask import Flask

    db = FakeDB()

    class UserFile:
        user_id = SimpleNamespace()
        doi = SimpleNamespace()
        external_provider = SimpleNamespace()
        external_item_id = SimpleNamespace()

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
            self.id = None

    class Project:
        pass

    class _Q:
        def where(self, *a, **k):
            return self

    def select_fn(model):
        return _Q()

    def login_required(fn):
        return fn

    enqueued = []

    def enqueue_import(_db, uid, fid):
        enqueued.append((uid, fid))

    storage = SimpleNamespace(
        sha256_file=lambda path: "abc",
        upload=lambda key, path: None,
    )

    monkeypatch.setattr(
        "backend.scholarly.provider_enabled",
        lambda p: True,
    )

    # Patch where discover_routes imports it
    import backend.scholarly.crossref as cx

    monkeypatch.setattr(cx, "enrich_file_from_doi", lambda *a, **k: None)

    work = PubmedWork(
        id="31452104",
        pmid="31452104",
        doi="10.1038/s41586-019-1490-y",
        title="PubMed Paper",
        authors="Doe J",
        year=2019,
        venue="Nature",
        abstract="Abs",
        open_access_url="https://example.com/paper.pdf",
        pmcid="PMC6789012",
        is_open_access=True,
    )
    monkeypatch.setattr(
        "backend.scholarly.pubmed.get_work_by_pmid",
        lambda pmid, *, db, enrich=True: work,
    )
    monkeypatch.setattr(
        "backend.scholarly.pubmed.download_open_access_pdf",
        lambda w, *, max_bytes=0: (b"%PDF-1.4 fake", "PMID31452104.pdf"),
    )

    applied = {}

    def fake_apply(db, uf, **kwargs):
        uf.path = "disk.pdf"
        uf.size = 12
        uf.mime = "application/pdf"
        applied.update(kwargs)
        if kwargs.get("enqueue_import"):
            kwargs["enqueue_import"](db, kwargs["user_id"], uf.id)
        return {"ok": True, "queued": True, "file_id": uf.id}

    monkeypatch.setattr(
        "backend.library.file_pull.apply_pdf_bytes_to_stub",
        fake_apply,
    )
    monkeypatch.setattr(
        "backend.library.sync.has_research_asset",
        lambda uf: False,
    )

    bp = create_discover_blueprint(
        SessionLocal=lambda: db,
        UserFile=UserFile,
        Project=Project,
        select_fn=select_fn,
        login_required=login_required,
        file_to_dict=lambda x: {
            "id": x.id,
            "title": x.title,
            "external_provider": getattr(x, "external_provider", ""),
            "external_item_id": getattr(x, "external_item_id", ""),
            "metadata_source": getattr(x, "metadata_source", ""),
            "path": getattr(x, "path", ""),
        },
        app_logger=SimpleNamespace(warning=lambda *a, **k: None),
        storage=storage,
        upload_dir="/tmp",
        enqueue_import=enqueue_import,
        max_file_mb=50,
    )

    app = Flask(__name__)
    app.secret_key = "test"
    app.register_blueprint(bp)
    app.config["TESTING"] = True

    return app, db, enqueued, applied


def test_pubmed_import_attaches_oa_and_enqueues(discover_app):
    app, db, enqueued, applied = discover_app
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = 7

    res = client.post(
        "/api/discover/import",
        json={
            "provider": "pubmed",
            "pmid": "31452104",
            "title": "PubMed Paper",
            "doi": "10.1038/s41586-019-1490-y",
            "open_access_url": "https://example.com/paper.pdf",
            "pmcid": "PMC6789012",
        },
    )
    assert res.status_code == 201, res.get_data(as_text=True)
    body = res.get_json()
    assert body["already_exists"] is False
    assert body["provider"] == "pubmed"
    assert body["pdf_attached"] is True
    assert body["analysis_queued"] is True
    assert body["file"]["external_provider"] == "pubmed"
    assert body["file"]["external_item_id"] == "31452104"
    assert body["file"]["metadata_source"] == "pubmed"
    assert len(db.added) == 1
    tags = json.loads(db.added[0].tags)
    assert "from-pubmed" in tags
    assert "pmid:31452104" in tags
    assert enqueued == [(7, body["file"]["id"])]
    assert applied.get("filename") == "PMID31452104.pdf"
