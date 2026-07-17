"""Local-disk storage provider — zero-config fallback so the app runs
without an R2 account, the same way DATABASE_URL falls back to SQLite.

There's no separate object store to bypass, so "presigned upload" degrades
to a signed, time-limited URL back to this same Flask server: the token
(via itsdangerous, already a Flask dependency) carries the key + an
expiry, and a route in server.py trusts any request bearing a valid token
instead of checking session auth — that's what makes it usable the same
way a real presigned URL is (no cookies required)."""
import contextlib
import os
import shutil

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from .checksum import md5_file_b64
from .provider import ObjectInfo


class LocalProvider:
    supports_multipart = False

    def __init__(self, root_dir: str, secret_key: str, base_url: str):
        self.root_dir = root_dir
        os.makedirs(root_dir, exist_ok=True)
        self._signer = URLSafeTimedSerializer(secret_key, salt="local-storage-upload")
        self.base_url = base_url.rstrip("/")

    def _path(self, key: str) -> str:
        # Keys are always our own uuid4().hex + ext; reject anything that
        # could escape root_dir if that assumption is ever violated.
        safe = os.path.basename(key)
        if safe != key:
            raise ValueError(f"unsafe storage key: {key!r}")
        return os.path.join(self.root_dir, safe)

    def path_for(self, key: str) -> str:
        """Public accessor for callers (e.g. a Flask send_file route) that
        need the real path rather than a copy/context-manager."""
        return self._path(key)

    def upload(self, key, local_path):
        shutil.copyfile(local_path, self._path(key))

    def delete(self, key):
        try:
            os.remove(self._path(key))
        except OSError:
            pass

    def head(self, key):
        path = self._path(key)
        if not os.path.exists(path):
            return None
        return ObjectInfo(key=key, size=os.path.getsize(path),
                          etag=md5_file_b64(path))

    def list_keys(self, prefix=""):
        for name in os.listdir(self.root_dir):
            if name.startswith(prefix):
                yield name

    @contextlib.contextmanager
    def local_copy(self, key, suffix=""):
        # Already local — no download needed, just hand back the real path.
        yield self._path(key)

    def presigned_get_url(self, key, filename, mime, expires_in=300):
        token = self._signer.dumps({"key": key, "name": filename, "mime": mime})
        return f"{self.base_url}/api/uploads/local-get/{key}?token={token}"

    def presigned_put_url(self, key, mime, expires_in=600, content_md5_b64=None):
        token = self._signer.dumps({"key": key, "mime": mime,
                                    "max_age": expires_in})
        return f"{self.base_url}/api/uploads/local-put/{key}?token={token}"

    def verify_token(self, token: str, max_age: int = 3600) -> dict:
        try:
            return self._signer.loads(token, max_age=max_age)
        except (BadSignature, SignatureExpired) as e:
            raise ValueError("invalid or expired upload token") from e

    def create_multipart_upload(self, key, mime):
        raise NotImplementedError("local provider has no part-size limit; "
                                  "use a single presigned_put_url instead")

    def presigned_part_url(self, key, upload_id, part_number, expires_in=3600):
        raise NotImplementedError

    def complete_multipart_upload(self, key, upload_id, parts):
        raise NotImplementedError

    def abort_multipart_upload(self, key, upload_id):
        raise NotImplementedError
