"""Discover arXiv import — Golden Rule wiring (#24)."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from backend.library.discover_routes import create_discover_blueprint
from backend.scholarly.arxiv import ArxivWork


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
        self._id = 200

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

    work = ArxivWork(
        id="2107.12345",
        arxiv_id="2107.12345",
        doi="10.48550/arXiv.2107.12345",
        title="Sample Paper",
        authors="Ada",
        year=2021,
        open_access_url="https://arxiv.org/pdf/2107.12345.pdf",
    )
    monkeypatch.setattr(
        "backend.scholarly.arxiv.get_work_by_id",
        lambda aid, *, db: work,
    )
    from backend.scholarly.uftr.outcomes import FullTextOutcome
    from backend.scholarly.uftr.resolvers import Candidate

    monkeypatch.setattr(
        "backend.scholarly.uftr.resolve.collect_candidates",
        lambda **kw: [Candidate(url=work.open_access_url, resolver="arxiv")],
    )
    monkeypatch.setattr(
        "backend.scholarly.uftr.resolve.download_candidate",
        lambda url, **kw: (FullTextOutcome.FOUND, b"%PDF-1.4 x", "application/pdf", url),
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


def test_arxiv_import_attaches_pdf_and_enqueues(discover_app):
    app, db, enqueued = discover_app
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = 3
    res = client.post(
        "/api/discover/import",
        json={
            "provider": "arxiv",
            "arxiv_id": "2107.12345",
            "title": "Sample Paper",
            "doi": "10.48550/arXiv.2107.12345",
        },
    )
    assert res.status_code == 201, res.get_data(as_text=True)
    body = res.get_json()
    assert body["provider"] == "arxiv"
    assert body["pdf_attached"] is True
    assert body["analysis_queued"] is True
    assert body["file"]["external_provider"] == "arxiv"
    assert body["file"]["external_item_id"] == "2107.12345"
    tags = json.loads(db.added[0].tags)
    assert "from-arxiv" in tags
    assert enqueued == [(3, body["file"]["id"])]
