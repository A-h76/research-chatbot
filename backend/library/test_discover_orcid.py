"""Discover ORCID import — Golden Rule wiring (#26)."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from backend.library.discover_routes import create_discover_blueprint
from backend.scholarly.orcid import OrcidWork


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
        self._id = 400

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
        pass

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

    enqueued = []

    def enqueue_import(_db, uid, fid):
        enqueued.append((uid, fid))

    monkeypatch.setattr("backend.scholarly.provider_enabled", lambda p: True)
    import backend.scholarly.crossref as cx

    monkeypatch.setattr(cx, "enrich_file_from_doi", lambda *a, **k: None)

    work = OrcidWork(
        id="0000-0002-1825-0097:152600",
        orcid_id="0000-0002-1825-0097",
        put_code="152600",
        doi="10.1234/orcid.sample",
        title="Sample ORCID Paper",
        year=2020,
        open_access_url="https://example.org/paper.pdf",
        is_open_access=True,
    )
    monkeypatch.setattr(
        "backend.scholarly.orcid.get_work_by_id",
        lambda wid, *, db, enrich=True: work,
    )
    monkeypatch.setattr(
        "backend.scholarly.orcid.enrich_oa_hints",
        lambda w, *, db: w,
    )
    monkeypatch.setattr(
        "backend.scholarly.orcid.download_open_access_pdf",
        lambda w, *, max_bytes=0, db=None: (b"%PDF-1.4 x", "orcid_152600.pdf"),
    )

    def fake_apply(db, uf, **kwargs):
        uf.path = "disk.pdf"
        uf.size = 10
        if kwargs.get("enqueue_import"):
            kwargs["enqueue_import"](db, kwargs["user_id"], uf.id)
        return {"ok": True, "queued": True, "file_id": uf.id}

    monkeypatch.setattr("backend.library.file_pull.apply_pdf_bytes_to_stub", fake_apply)
    monkeypatch.setattr("backend.library.sync.has_research_asset", lambda uf: False)

    bp = create_discover_blueprint(
        SessionLocal=lambda: db,
        UserFile=UserFile,
        Project=Project,
        select_fn=lambda m: _Q(),
        login_required=lambda f: f,
        file_to_dict=lambda x: {
            "id": x.id,
            "title": x.title,
            "external_provider": getattr(x, "external_provider", ""),
            "external_item_id": getattr(x, "external_item_id", ""),
            "metadata_source": getattr(x, "metadata_source", ""),
        },
        app_logger=SimpleNamespace(warning=lambda *a, **k: None),
        storage=SimpleNamespace(sha256_file=lambda p: "s", upload=lambda *a: None),
        upload_dir="/tmp",
        enqueue_import=enqueue_import,
        max_file_mb=50,
    )
    app = Flask(__name__)
    app.secret_key = "test"
    app.register_blueprint(bp)
    return app, db, enqueued


def test_orcid_import_attaches_pdf_and_enqueues(discover_app):
    app, db, enqueued = discover_app
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = 5
    res = client.post(
        "/api/discover/import",
        json={
            "provider": "orcid",
            "orcid_id": "0000-0002-1825-0097",
            "put_code": "152600",
            "id": "0000-0002-1825-0097:152600",
            "title": "Sample ORCID Paper",
            "doi": "10.1234/orcid.sample",
            "open_access_url": "https://example.org/paper.pdf",
        },
    )
    assert res.status_code == 201, res.get_data(as_text=True)
    body = res.get_json()
    assert body["provider"] == "orcid"
    assert body["pdf_attached"] is True
    assert body["analysis_queued"] is True
    assert body["file"]["external_provider"] == "orcid"
    assert body["file"]["external_item_id"] == "0000-0002-1825-0097:152600"
    tags = json.loads(db.added[0].tags)
    assert "from-orcid" in tags
    assert enqueued == [(5, body["file"]["id"])]


def test_orcid_import_metadata_only_when_no_pdf(discover_app, monkeypatch):
    app, db, enqueued = discover_app
    monkeypatch.setattr(
        "backend.scholarly.orcid.download_open_access_pdf",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "backend.scholarly.orcid.get_work_by_id",
        lambda wid, *, db, enrich=True: OrcidWork(
            id="0000-0002-1825-0097:99",
            orcid_id="0000-0002-1825-0097",
            put_code="99",
            title="No PDF work",
            doi="",
        ),
    )
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = 5
    res = client.post(
        "/api/discover/import",
        json={
            "provider": "orcid",
            "orcid_id": "0000-0002-1825-0097",
            "put_code": "99",
            "title": "No PDF work",
        },
    )
    assert res.status_code == 201, res.get_data(as_text=True)
    body = res.get_json()
    assert body["pdf_attached"] is False
    assert body["analysis_queued"] is False
    assert enqueued == []
