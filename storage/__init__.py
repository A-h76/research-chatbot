"""Storage Manager — public entry point.

Keeps the exact module-level API the rest of the codebase already calls
(`storage.upload`, `storage.delete`, `storage.presigned_url`,
`storage.local_copy`) so converting the old single-file `storage.py` into
this package required zero changes at any existing call site. New code
(presigned/multipart uploads, GC, reconciliation) should import
`storage_manager` / `sweep_temp_dir` / `garbage_collect` / `reconcile`
directly instead.
"""
import os

from .manager import (StorageManager, get_default_manager, sweep_temp_dir,
                      garbage_collect, reconcile, GCReport, ReconcileReport)
from .provider import ObjectInfo, UploadPart
from .checksum import sha256_file, md5_file_b64

_LOCAL_DIR = os.environ.get(
    "LOCAL_STORAGE_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "storage_data"))
_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000")

storage_manager = get_default_manager(local_dir=_LOCAL_DIR, base_url=_BASE_URL)


# ------------------------------------------------------ legacy module-level API
def upload(key, local_path):
    storage_manager.provider.upload(key, local_path)


def delete(key):
    storage_manager.provider.delete(key)


def presigned_url(key, filename, mime, expires_in=300):
    return storage_manager.provider.presigned_get_url(key, filename, mime, expires_in)


def local_copy(key, suffix=""):
    return storage_manager.provider.local_copy(key, suffix)
