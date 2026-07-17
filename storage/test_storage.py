"""Self-check for the storage package — no framework, no fixtures.
Run: python -m storage.test_storage
"""
import os
import shutil
import tempfile

from storage.checksum import sha256_file, md5_file_b64
from storage.local_provider import LocalProvider
from storage.manager import sweep_temp_dir, garbage_collect, reconcile


def _write(path, content: bytes):
    with open(path, "wb") as f:
        f.write(content)


def test_checksum_is_deterministic_and_content_sensitive():
    d = tempfile.mkdtemp()
    try:
        a, b = os.path.join(d, "a"), os.path.join(d, "b")
        _write(a, b"hello world")
        _write(b, b"hello world!")
        assert sha256_file(a) == sha256_file(a)
        assert sha256_file(a) != sha256_file(b)
        assert md5_file_b64(a) == md5_file_b64(a)
    finally:
        shutil.rmtree(d)


def test_local_provider_round_trip():
    d = tempfile.mkdtemp()
    try:
        provider = LocalProvider(root_dir=os.path.join(d, "blobs"),
                                 secret_key="test-secret",
                                 base_url="http://localhost:5000")
        src = os.path.join(d, "src.txt")
        _write(src, b"paper contents")

        key = "abc123.txt"
        provider.upload(key, src)

        info = provider.head(key)
        assert info is not None and info.size == len(b"paper contents")

        with provider.local_copy(key) as p:
            assert open(p, "rb").read() == b"paper contents"

        provider.delete(key)
        assert provider.head(key) is None
    finally:
        shutil.rmtree(d)


def test_local_provider_signed_tokens_round_trip_and_expire():
    provider = LocalProvider(root_dir=tempfile.mkdtemp(), secret_key="s",
                             base_url="http://localhost:5000")
    url = provider.presigned_put_url("k.pdf", "application/pdf", expires_in=600)
    token = url.split("token=")[1]
    payload = provider.verify_token(token, max_age=600)
    assert payload["key"] == "k.pdf"

    try:
        provider.verify_token(token, max_age=-1)   # any age is > -1 seconds
        assert False, "expected expired token to raise"
    except ValueError:
        pass

    try:
        provider.verify_token(token + "x", max_age=600)
        assert False, "expected tampered token to raise"
    except ValueError:
        pass


def test_sweep_temp_dir_removes_only_stale_files():
    d = tempfile.mkdtemp()
    try:
        fresh, stale = os.path.join(d, "fresh"), os.path.join(d, "stale")
        _write(fresh, b"x")
        _write(stale, b"x")
        old = os.path.getmtime(stale) - 7200
        os.utime(stale, (old, old))

        removed = sweep_temp_dir(d, max_age_seconds=3600)
        assert removed == ["stale"]
        assert os.path.exists(fresh) and not os.path.exists(stale)
    finally:
        shutil.rmtree(d)


def test_garbage_collect_deletes_given_keys():
    provider = LocalProvider(root_dir=tempfile.mkdtemp(), secret_key="s",
                             base_url="http://localhost:5000")
    src = tempfile.mktemp()
    _write(src, b"x")
    provider.upload("orphan.pdf", src)
    assert provider.head("orphan.pdf") is not None

    report = garbage_collect(provider, ["orphan.pdf"])
    assert report.deleted == ["orphan.pdf"]
    assert provider.head("orphan.pdf") is None


def test_reconcile_finds_orphans_and_missing_without_deleting_by_default():
    provider = LocalProvider(root_dir=tempfile.mkdtemp(), secret_key="s",
                             base_url="http://localhost:5000")
    src = tempfile.mktemp()
    _write(src, b"x")
    provider.upload("a.pdf", src)   # in storage
    provider.upload("b.pdf", src)   # in storage AND referenced by "DB"

    known_keys = {"b.pdf", "c.pdf"}   # c.pdf: DB row, object missing from storage

    report = reconcile(provider, known_keys, dry_run=True)
    assert report.orphaned_keys == ["a.pdf"]
    assert report.missing_keys == ["c.pdf"]
    assert report.deleted == []
    assert provider.head("a.pdf") is not None   # dry-run: nothing removed

    report2 = reconcile(provider, known_keys, dry_run=False)
    assert report2.deleted == ["a.pdf"]
    assert provider.head("a.pdf") is None        # apply: orphan actually removed
    assert provider.head("b.pdf") is not None    # known key untouched


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} passed")
