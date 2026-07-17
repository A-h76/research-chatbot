"""Integration tests for the storage backend compatibility layer.

LocalBackend gets full coverage against a real temporary directory
(pytest's tmp_path — no mocking, real files on real disk), per the task's
own scope. R2Backend gets one real round-trip test too, since real R2
credentials are available in this environment and skipping real
verification in favor of a mock would be exactly the gap this project's
own testing-guide.md warns about (a mocked storage test missing a real
integration bug) — skipped automatically if R2 isn't configured.

Run: pytest backend/storage/test_backends.py -v
"""
import io
import os

import pytest

from backend.storage.interface import StorageBackend
from backend.storage.local import LocalBackend
from backend.storage.factory import get_storage_backend


# ------------------------------------------------------------------ LocalBackend
@pytest.fixture
def local_backend(tmp_path):
    return LocalBackend(root_dir=str(tmp_path))


def test_local_upload_returns_key(local_backend):
    key = local_backend.upload(io.BytesIO(b"hello world"), "notes.txt")
    assert key == "notes.txt"


def test_local_upload_creates_dated_subfolder(local_backend, tmp_path):
    local_backend.upload(io.BytesIO(b"data"), "report.pdf")
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc)
    expected = tmp_path / f"{today:%Y}" / f"{today:%m}" / f"{today:%d}" / "report.pdf"
    assert expected.exists()
    assert expected.read_bytes() == b"data"


def test_local_download_round_trip(local_backend):
    content = b"the quick brown fox"
    local_backend.upload(io.BytesIO(content), "fox.txt")
    assert local_backend.download("fox.txt") == content


def test_local_download_missing_key_raises(local_backend):
    with pytest.raises(FileNotFoundError):
        local_backend.download("does-not-exist.txt")


def test_local_delete_removes_file(local_backend):
    local_backend.upload(io.BytesIO(b"temp"), "scratch.txt")
    assert local_backend.download("scratch.txt") == b"temp"
    local_backend.delete("scratch.txt")
    with pytest.raises(FileNotFoundError):
        local_backend.download("scratch.txt")


def test_local_delete_missing_key_does_not_raise(local_backend):
    local_backend.delete("never-existed.txt")   # best-effort, no error


def test_local_generate_presigned_url_is_file_uri(local_backend):
    local_backend.upload(io.BytesIO(b"x"), "doc.txt")
    url = local_backend.generate_presigned_url("doc.txt")
    assert url.startswith("file:")
    assert "doc.txt" in url


def test_local_presigned_url_missing_key_raises(local_backend):
    with pytest.raises(FileNotFoundError):
        local_backend.generate_presigned_url("nope.txt")


def test_local_backend_satisfies_the_abc(local_backend):
    assert isinstance(local_backend, StorageBackend)


def test_abc_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        StorageBackend()


# ------------------------------------------------------------------ factory
def test_factory_returns_local_when_no_r2_config(monkeypatch):
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    monkeypatch.delenv("R2_BUCKET", raising=False)
    backend = get_storage_backend()
    assert isinstance(backend, LocalBackend)


def test_factory_explicit_local_choice(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    backend = get_storage_backend()
    assert isinstance(backend, LocalBackend)


def test_factory_rejects_unknown_choice(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "azure-blob")
    with pytest.raises(ValueError):
        get_storage_backend()


# ------------------------------------------------------------------ R2Backend
# Real round-trip, not mocked — skipped automatically if R2 isn't
# configured in this environment (e.g. CI without R2 secrets).
_r2_configured = bool(os.environ.get("R2_BUCKET"))


@pytest.mark.skipif(not _r2_configured, reason="R2 not configured in this environment")
def test_r2_backend_real_upload_download_delete_round_trip():
    from backend.storage.r2 import R2Backend
    import uuid

    backend = R2Backend()
    key = f"backend-storage-compat-test-{uuid.uuid4().hex}.txt"
    content = b"real R2 round trip via the compat layer"

    try:
        returned_key = backend.upload(io.BytesIO(content), key, content_type="text/plain")
        assert returned_key == key

        downloaded = backend.download(key)
        assert downloaded == content

        url = backend.generate_presigned_url(key, expires_in=60)
        assert url.startswith("https://")
    finally:
        backend.delete(key)
        with pytest.raises(Exception):
            # local_copy() on a deleted key should fail — confirms
            # delete() genuinely removed the object from R2, not just
            # from this test's local expectations.
            backend.download(key)
