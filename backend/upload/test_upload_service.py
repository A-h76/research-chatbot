"""Bite 13 — UploadService convergence tests."""

from __future__ import annotations

from types import SimpleNamespace

from backend.upload.upload_service import (
    UPLOAD_SERVICE_VERSION,
    JwtStorageFacade,
    SessionStorageFacade,
    UploadService,
)


class FakeDB:
    def __init__(self):
        self.added = []
        self._id = 1
        self._batches = {}

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = self._id
            self._id += 1
        self.added.append(obj)
        if obj.__class__.__name__ == "UploadBatch":
            self._batches[obj.id] = obj

    def flush(self):
        pass

    def get(self, model, key):
        if key is None:
            return None
        if getattr(model, "__name__", "") == "UploadBatch" or model is UploadBatch:
            return self._batches.get(key)
        return None


class UserFile:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.id = None


class UploadBatch:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.id = None


class _Spine:
    def __init__(self):
        self.calls = []

    def enqueue_after_store(self, db, user_id, file_id, *, upload_batch_id=None):
        self.calls.append((user_id, file_id, upload_batch_id))
        return 100 + len(self.calls)


def test_upload_service_version():
    assert UPLOAD_SERVICE_VERSION == "1.0"


def test_register_creates_file_and_enqueues():
    spine = _Spine()
    svc = UploadService(UserFile, UploadBatch, import_spine=spine)
    db = FakeDB()
    result = svc.register(
        db,
        user_id=7,
        name="paper.pdf",
        mime="application/pdf",
        kind="document",
        path="abc.pdf",
        size=12,
        batch_source="library",
    )
    assert result.ok
    assert result.spine == UPLOAD_SERVICE_VERSION
    assert result.user_file.user_id == 7
    assert result.user_file.path == "abc.pdf"
    assert result.job_id == 101
    assert spine.calls == [(7, result.user_file.id, result.batch_id)]
    assert result.batch_id is not None


def test_session_and_jwt_paths_converge_on_register(monkeypatch):
    """Session + JWT store helpers both end in UploadService.register."""
    seen = []
    spine = _Spine()
    svc = UploadService(UserFile, UploadBatch, import_spine=spine)

    orig = UploadService.register

    def wrap(self, db, **kwargs):
        seen.append(kwargs.get("batch_source") or kwargs.get("path"))
        return orig(self, db, **kwargs)

    monkeypatch.setattr(UploadService, "register", wrap)

    class SessStore:
        def sha256_file(self, path):
            return "deadbeef"

        def new_key(self, ext):
            return "sess" + ext

        def upload_path(self, key, local_path):
            return key

    class JwtStore:
        def new_document_key(self, user_id, filename):
            return f"users/{user_id}/documents/x/{filename}"

        def upload_bytes(self, key, data, *, content_type):
            return key

        def delete(self, key):
            pass

    db = FakeDB()
    r1 = svc.store_session_and_register(
        db,
        SessStore(),
        user_id=1,
        local_path="/tmp/a",
        filename="a.pdf",
        mime="application/pdf",
        kind="document",
        size=3,
        ext=".pdf",
        batch_source="library",
    )
    assert r1.ok and not r1.duplicate

    r2 = svc.store_jwt_bytes_and_register(
        FakeDB(),
        JwtStore(),
        user_id=2,
        data=b"%PDF",
        filename="b.pdf",
        mime="application/pdf",
        kind="document",
        project_id=77,
        batch_source="api_documents",
    )
    assert r2.ok
    assert r2.user_file.project_id == 77
    assert "library" in seen
    assert "api_documents" in seen


def test_session_dedup_short_circuits():
    existing = UserFile(id=9, user_id=1, path="old.pdf")

    def find_dup(db, user_id, checksum):
        return existing

    svc = UploadService(
        UserFile, UploadBatch, import_spine=_Spine(), find_duplicate_file=find_dup
    )

    class SessStore:
        def sha256_file(self, path):
            return "same"

        def new_key(self, ext):
            raise AssertionError("should not store")

        def upload_path(self, key, local_path):
            raise AssertionError("should not store")

    result = svc.store_session_and_register(
        FakeDB(),
        SessStore(),
        user_id=1,
        local_path="/tmp/a",
        filename="a.pdf",
        mime="application/pdf",
        kind="document",
        size=3,
        ext=".pdf",
    )
    assert result.duplicate is True
    assert result.user_file is existing


def test_storage_facades_key_shapes():
    class Mgr:
        def sha256_file(self, path):
            return "x"

        def upload(self, key, path):
            pass

        def delete(self, key):
            pass

    class Backend:
        def upload(self, file_obj, key, content_type=None):
            return key

        def delete(self, key):
            pass

    sess = SessionStorageFacade(Mgr())
    assert sess.new_key(".pdf").endswith(".pdf")
    jwt = JwtStorageFacade(Backend())
    assert jwt.new_document_key(3, "f.pdf").startswith("users/3/documents/")
    assert "/uploads/9/" in jwt.new_bulk_key(3, 9, "f.pdf")
