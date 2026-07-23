"""get_storage_backend() — reads STORAGE_BACKEND ("r2" | "local" | "s3")
and returns the matching backend. Same fallback shape as the real
storage/ package's own provider selection (and DATABASE_URL defaulting
to SQLite): no R2 config present, no explicit choice -> local."""

import os

from .interface import StorageBackend
from .local import LocalBackend
from .r2 import R2Backend
from .s3 import S3Backend


def get_storage_backend() -> StorageBackend:
    choice = os.environ.get("STORAGE_BACKEND", "").strip().lower()

    if not choice:
        choice = "r2" if os.environ.get("R2_BUCKET") else "local"

    if choice == "r2":
        return R2Backend()
    if choice == "s3":
        return S3Backend()
    if choice == "local":
        return LocalBackend()
    raise ValueError(f"unknown STORAGE_BACKEND: {choice!r} (expected r2, local, or s3)")
