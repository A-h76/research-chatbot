"""Storage provider interface — one abstraction, two backends (R2, local
disk). Nothing outside `storage/` should know which backend is active."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Iterator, Protocol


@dataclass
class ObjectInfo:
    key: str
    size: int
    etag: str | None = None  # provider-native identity (R2: quoted MD5-ish ETag)


@dataclass
class UploadPart:
    part_number: int
    etag: str


class StorageProvider(Protocol):
    """Every method a caller may need, regardless of backend. `local_copy`
    is the one method every consumer of stored bytes should go through —
    library code (PyMuPDF, python-docx, ...) needs a real filesystem path,
    and only the provider knows whether that means a download or is
    already true."""

    supports_multipart: bool

    def upload(self, key: str, local_path: str) -> None: ...
    def delete(self, key: str) -> None: ...
    def head(self, key: str) -> ObjectInfo | None: ...
    def list_keys(self, prefix: str = "") -> Iterator[str]: ...

    @contextlib.contextmanager
    def local_copy(self, key: str, suffix: str = "") -> Iterator[str]: ...

    def presigned_get_url(
        self, key: str, filename: str, mime: str, expires_in: int = 300
    ) -> str: ...
    def presigned_put_url(
        self,
        key: str,
        mime: str,
        expires_in: int = 600,
        content_md5_b64: str | None = None,
    ) -> str: ...

    def create_multipart_upload(self, key: str, mime: str) -> str: ...
    def presigned_part_url(
        self, key: str, upload_id: str, part_number: int, expires_in: int = 3600
    ) -> str: ...
    def complete_multipart_upload(
        self, key: str, upload_id: str, parts: list[UploadPart]
    ) -> None: ...
    def abort_multipart_upload(self, key: str, upload_id: str) -> None: ...
