"""LocalBackend — genuinely independent (not a wrapper over the real
storage/local_provider.py), unlike R2Backend/S3Backend.

Two reasons: (1) the task asks for date-subfolder organization
(./uploads/YYYY/MM/DD/<key>), which the real LocalProvider doesn't do —
it's a flat layout by design, since its whole job is standing in for R2
during dev; (2) the real LocalProvider's "presigned URL" is a signed,
time-limited token pointing back at a Flask route that doesn't exist in
this narrower interface's world. Reimplementing that machinery to fit an
interface with no upload/download routes behind it would be more code
than this simple, self-contained version.

Uses ./uploads/ as literally asked — safe alongside the app's existing
UPLOAD_DIR (server.py's throwaway-temp-file directory, flat UUID-named
files) because everything this backend writes goes into a dated
subfolder, never the root, so the two can never collide on a filename.
"""
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Optional

from .interface import StorageBackend

DEFAULT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "..", "uploads")


class LocalBackend(StorageBackend):
    def __init__(self, root_dir: str = DEFAULT_ROOT):
        self.root_dir = os.path.abspath(root_dir)
        os.makedirs(self.root_dir, exist_ok=True)

    def _dated_path(self, key: str) -> Path:
        today = datetime.now(timezone.utc)
        subdir = Path(self.root_dir) / f"{today:%Y}" / f"{today:%m}" / f"{today:%d}"
        subdir.mkdir(parents=True, exist_ok=True)
        return subdir / os.path.basename(key)

    def _find(self, key: str) -> Optional[Path]:
        """A lookup by key alone (no date given) has to search the dated
        subfolders — the tradeoff for organizing by date at write time."""
        name = os.path.basename(key)
        for path in Path(self.root_dir).rglob(name):
            return path
        return None

    def upload(self, file_obj: BinaryIO, key: str, content_type: Optional[str] = None) -> str:
        dest = self._dated_path(key)
        with open(dest, "wb") as f:
            f.write(file_obj.read())
        return key

    def download(self, key: str) -> bytes:
        path = self._find(key)
        if not path:
            raise FileNotFoundError(key)
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._find(key)
        if path:
            try:
                path.unlink()
            except OSError:
                pass

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        # No real HTTP route serves these in this standalone compat
        # layer (see module docstring) — file:// is the honest answer,
        # not a fabricated http:// URL nothing actually serves.
        path = self._find(key)
        if not path:
            raise FileNotFoundError(key)
        return path.as_uri()
