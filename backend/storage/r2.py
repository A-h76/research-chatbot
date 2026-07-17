"""R2Backend — delegates to the real storage/r2_provider.py (boto3,
Cloudflare R2 endpoint_url + signature_version="s3v4"), translating this
narrower BinaryIO/bytes interface onto that provider's already-tested
key/local_path-based one, rather than reimplementing R2 upload/download
logic a second time.

Constructs its own R2Provider directly (same R2_* env vars the real
package's get_default_manager() reads) rather than reusing the shared
storage.storage_manager singleton — that singleton picks R2 vs. local
based on the *original* STORAGE_PROVIDER env var, and this backend
should mean "R2, specifically" regardless of what that currently
resolves to.
"""
import os
import tempfile
from typing import BinaryIO, Optional

from storage.r2_provider import R2Provider

from .interface import StorageBackend


def _r2_config_from_env():
    bucket = os.environ.get("R2_BUCKET", "")
    endpoint = os.environ.get("R2_ENDPOINT") or (
        f"https://{os.environ.get('R2_ACCOUNT_ID', '')}.r2.cloudflarestorage.com")
    return dict(
        bucket=bucket, endpoint=endpoint,
        access_key=os.environ.get("R2_ACCESS_KEY_ID", ""),
        secret_key=os.environ.get("R2_SECRET_ACCESS_KEY", ""),
    )


class R2Backend(StorageBackend):
    def __init__(self, provider: Optional[R2Provider] = None):
        self._provider = provider or R2Provider(**_r2_config_from_env())

    def upload(self, file_obj: BinaryIO, key: str, content_type: Optional[str] = None) -> str:
        # The real provider's upload() takes a local path (it's built
        # for the app's actual flow: save-then-upload, never bytes in
        # memory) — bridge with a throwaway temp file rather than
        # reaching into the provider's boto3 client directly, which
        # would mean depending on its private internals instead of its
        # public contract.
        fd, tmp_path = tempfile.mkstemp()
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(file_obj.read())
            self._provider.upload(key, tmp_path)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return key

    def download(self, key: str) -> bytes:
        with self._provider.local_copy(key) as local_path:
            with open(local_path, "rb") as f:
                return f.read()

    def delete(self, key: str) -> None:
        self._provider.delete(key)

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return self._provider.presigned_get_url(
            key, filename=os.path.basename(key),
            mime="application/octet-stream", expires_in=expires_in)
