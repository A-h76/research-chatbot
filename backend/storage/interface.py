"""StorageBackend — the ABC-typed, BinaryIO-based interface this prompt
asked for. A compatibility layer over the real storage/ package (project
root), not a second implementation of R2/local/S3 upload logic: the real
package is already tested, already wired into upload_file(), worker.py,
and the gc-storage/reconcile-storage CLI commands, and already has
capabilities (multipart, head/list_keys for GC+reconciliation) this
narrower interface doesn't cover. See backend/storage/r2.py and
backend/storage/local.py for how each backend delegates.
"""

import abc
from typing import BinaryIO, Optional


class StorageBackend(abc.ABC):
    @abc.abstractmethod
    def upload(
        self, file_obj: BinaryIO, key: str, content_type: Optional[str] = None
    ) -> str:
        """Returns a public URL or the key, backend-dependent."""
        ...

    @abc.abstractmethod
    def download(self, key: str) -> bytes: ...

    @abc.abstractmethod
    def delete(self, key: str) -> None: ...

    @abc.abstractmethod
    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str: ...
