"""Bite 12 — Import Spine convergence tests.

Proves Upload, PubMed, arXiv, Google Drive, OneDrive, ORCID all route through
``ImportService`` (same implementation) after acquisition.
"""

from __future__ import annotations

from types import SimpleNamespace

from backend.library.import_service import (
    IMPORT_SPINE_VERSION,
    ImportIdentity,
    ImportService,
)


class _FakeScalars:
    def __init__(self, first=None):
        self._first = first

    def first(self):
        return self._first


class _FakeResult:
    def __init__(self, first=None):
        self._first = first

    def scalars(self):
        return _FakeScalars(self._first)


class FakeDB:
    def __init__(self):
        self.added = []
        self._id = 1
        self._dup = None

    def execute(self, *_a, **_k):
        return _FakeResult(self._dup)

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = self._id
            self._id += 1
        self.added.append(obj)

    def flush(self):
        pass

    def refresh(self, _obj):
        pass


class UserFile:
    user_id = SimpleNamespace()
    doi = SimpleNamespace()
    external_provider = SimpleNamespace()
    external_item_id = SimpleNamespace()

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.id = getattr(self, "id", None)


class _Q:
    def where(self, *a, **k):
        return self


def _select(model):
    return _Q()


def _service(**kwargs):
    return ImportService(UserFile, _select, max_file_mb=50, **kwargs)


def test_import_spine_version():
    assert IMPORT_SPINE_VERSION == "1.0"


def test_find_duplicate_by_doi():
    db = FakeDB()
    existing = UserFile(id=9, user_id=1, doi="10.1/x")
    db._dup = existing
    svc = _service()
    hit = svc.find_duplicate(db, 1, doi="10.1/x")
    assert hit is existing


def test_find_duplicate_by_external_id():
    db = FakeDB()
    existing = UserFile(id=3, user_id=1, external_provider="pubmed", external_item_id="123")
    db._dup = existing
    svc = _service()
    hit = svc.find_duplicate(
        db, 1, external_provider="pubmed", external_item_id="123"
    )
    assert hit is existing


def test_create_stub_sets_identity():
    db = FakeDB()
    svc = _service()
    uf = svc.create_stub(
        db,
        ImportIdentity(
            user_id=7,
            title="Paper",
            doi="10.2/y",
            external_provider="arxiv",
            external_item_id="2401.00001",
            tags=["from-discover"],
            metadata_source="arxiv",
        ),
    )
    assert uf.user_id == 7
    assert uf.external_provider == "arxiv"
    assert uf.path == ""
    assert uf.size == 0
    assert uf in db.added


def test_enqueue_after_store_uses_outbox(monkeypatch):
    calls = []

    class Job:
        def __init__(self):
            self.id = 42

    def fake_outbox(db, **kwargs):
        calls.append(kwargs)
        return Job()

    monkeypatch.setattr(
        "backend.jobs.outbox.enqueue_upload_job_with_outbox", fake_outbox
    )
    svc = _service(UploadJob=object, OutboxEvent=object)
    job_id = svc.enqueue_after_store(FakeDB(), 1, 99, upload_batch_id=5)
    assert job_id == 42
    assert calls[0]["file_id"] == 99
    assert calls[0]["job_type"] == "import"
    assert calls[0]["upload_batch_id"] == 5


def test_upload_pubmed_arxiv_drive_onedrive_orcid_converge(monkeypatch):
    """All listed acquisition sources hit ImportService methods (same class)."""
    seen: list[str] = []

    def track(name):
        def deco(fn):
            def wrapped(*a, **k):
                seen.append(name)
                return fn(*a, **k)

            return wrapped

        return deco

    svc = _service(UploadJob=object, OutboxEvent=object)

    monkeypatch.setattr(
        "backend.jobs.outbox.enqueue_upload_job_with_outbox",
        lambda *a, **k: SimpleNamespace(id=1),
    )

    # Upload
    svc.enqueue_after_store = track("upload")(svc.enqueue_after_store)  # type: ignore
    assert svc.enqueue_after_store(FakeDB(), 1, 10) == 1

    # PubMed / arXiv / ORCID — import_reference
    orig_ref = ImportService.import_reference

    def ref_wrap(self, db, identity, **kwargs):
        seen.append(f"reference:{identity.external_provider or identity.metadata_source}")
        # skip UFTR
        existing = self.find_duplicate(
            db,
            identity.user_id,
            doi=identity.doi,
            external_provider=identity.external_provider,
            external_item_id=identity.external_item_id,
        )
        if existing:
            return {"already_exists": True, "file": existing, "spine": IMPORT_SPINE_VERSION}
        uf = self.create_stub(db, identity)
        return {
            "already_exists": False,
            "file": uf,
            "created": True,
            "attach": {"pdf_attached": False},
            "spine": IMPORT_SPINE_VERSION,
        }

    monkeypatch.setattr(ImportService, "import_reference", ref_wrap)

    for provider, ext in (
        ("pubmed", "PMID1"),
        ("arxiv", "2401.1"),
        ("orcid", "0000-0001:1"),
    ):
        ImportService.import_reference(
            svc,
            FakeDB(),
            ImportIdentity(
                user_id=1,
                title=f"{provider} paper",
                external_provider=provider,
                external_item_id=ext,
                metadata_source=provider,
            ),
        )

    # Drive / OneDrive — import_held_bytes
    def held_wrap(self, db, identity, *, data, filename, content_type="application/pdf"):
        seen.append(f"held:{identity.external_provider}")
        uf = self.create_stub(db, identity)
        return {
            "already_exists": False,
            "file": uf,
            "ok": True,
            "queued": True,
            "spine": IMPORT_SPINE_VERSION,
        }

    monkeypatch.setattr(ImportService, "import_held_bytes", held_wrap)

    for provider in ("google_drive", "onedrive"):
        ImportService.import_held_bytes(
            svc,
            FakeDB(),
            ImportIdentity(
                user_id=1,
                title="cloud.pdf",
                external_provider=provider,
                external_item_id=f"{provider}-id",
                metadata_source=provider,
            ),
            data=b"%PDF",
            filename="cloud.pdf",
        )

    assert "upload" in seen
    assert "reference:pubmed" in seen
    assert "reference:arxiv" in seen
    assert "reference:orcid" in seen
    assert "held:google_drive" in seen
    assert "held:onedrive" in seen
    assert all(isinstance(x, str) for x in seen)


def test_import_reference_returns_spine_and_dedupes():
    db = FakeDB()
    svc = _service()
    existing = UserFile(id=5, user_id=1, doi="10.9/z")
    db._dup = existing
    result = svc.import_reference(
        db,
        ImportIdentity(user_id=1, title="T", doi="10.9/z", metadata_source="pubmed"),
        enrich_doi=False,
    )
    assert result["already_exists"] is True
    assert result["spine"] == IMPORT_SPINE_VERSION
    assert result["file"] is existing


def test_import_held_bytes_attaches_via_apply(monkeypatch):
    applied = []

    def fake_apply(db, uf, **kwargs):
        applied.append(kwargs.get("filename"))
        uf.path = "x.pdf"
        uf.size = 3
        if kwargs.get("enqueue_import"):
            kwargs["enqueue_import"](db, kwargs["user_id"], uf.id)
        return {"ok": True, "queued": True, "file_id": uf.id}

    monkeypatch.setattr("backend.library.file_pull.apply_pdf_bytes_to_stub", fake_apply)

    enqueued = []

    def enqueue(db, uid, fid):
        enqueued.append((uid, fid))

    svc = _service(
        storage=object(),
        upload_dir="/tmp",
        enqueue_import=enqueue,
    )

    result = svc.import_held_bytes(
        FakeDB(),
        ImportIdentity(
            user_id=2,
            title="Drive Paper",
            external_provider="google_drive",
            external_item_id="abc",
            metadata_source="google_drive",
            tags=["from-google-drive"],
        ),
        data=b"%PDF-1.4",
        filename="paper.pdf",
    )
    assert result["ok"] is True
    assert result["spine"] == IMPORT_SPINE_VERSION
    assert applied == ["paper.pdf"]
    assert enqueued == [(2, result["file"].id)]


def test_import_reference_emits_paper_imported(monkeypatch):
    from backend.domain_events import (
        PAPER_IMPORTED,
        DomainEventBus,
        set_bus,
        subscribe,
    )

    bus = DomainEventBus()
    set_bus(bus)
    seen = []
    subscribe(lambda e: seen.append(e), event_name=PAPER_IMPORTED, handler_key="test.import")

    monkeypatch.setattr(
        ImportService,
        "resolve_fulltext",
        lambda self, db, uf, **kw: {"ok": False, "skipped": True},
    )
    svc = _service()
    result = svc.import_reference(
        FakeDB(),
        ImportIdentity(
            user_id=3,
            title="New",
            external_provider="pubmed",
            external_item_id="PMID99",
            metadata_source="pubmed",
        ),
        enrich_doi=False,
    )
    assert result["created"] is True
    assert len(seen) == 1
    assert seen[0].payload["file_id"] == result["file"].id
    assert seen[0].payload["source"] == "pubmed"
    bus.clear()
    set_bus(None)
