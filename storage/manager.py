"""Provider selection + the storage-hygiene jobs (GC, reconciliation,
temp-dir sweep) named in the storage architecture.

Deliberately DB-agnostic: this module only knows about bytes and keys, never
about SQLAlchemy models — the caller (server.py, where the models live)
queries the DB and passes in plain keys/sets, so storage/ stays testable
without a database and there's no circular import back into server.py."""
import os
import time
from dataclasses import dataclass, field

from .provider import StorageProvider
from .r2_provider import R2Provider
from .local_provider import LocalProvider


class StorageManager:
    def __init__(self, provider: StorageProvider):
        self.provider = provider

    def new_key(self, ext: str) -> str:
        import uuid
        return uuid.uuid4().hex + (ext or "")


def get_default_manager(local_dir: str, base_url: str) -> StorageManager:
    """R2 if configured (matches production), local disk otherwise — same
    fallback shape as DATABASE_URL defaulting to SQLite when unset."""
    provider_choice = os.environ.get("STORAGE_PROVIDER", "").strip().lower()
    bucket = os.environ.get("R2_BUCKET", "")
    account_id = os.environ.get("R2_ACCOUNT_ID", "")
    endpoint = os.environ.get("R2_ENDPOINT") or (
        f"https://{account_id}.r2.cloudflarestorage.com" if account_id else "")

    use_r2 = provider_choice == "r2" or (not provider_choice and bucket and endpoint)

    if use_r2:
        provider = R2Provider(
            bucket=bucket, endpoint=endpoint,
            access_key=os.environ.get("R2_ACCESS_KEY_ID", ""),
            secret_key=os.environ.get("R2_SECRET_ACCESS_KEY", ""),
        )
    else:
        provider = LocalProvider(
            root_dir=local_dir,
            secret_key=os.environ.get("FLASK_SECRET_KEY") or os.urandom(32).hex(),
            base_url=base_url,
        )
    return StorageManager(provider)


# ------------------------------------------------------------- temp lifecycle
def sweep_temp_dir(dir_path: str, max_age_seconds: int = 3600) -> list[str]:
    """Delete stray files left in the throwaway-temp directory by a request
    that crashed before its own `finally: os.remove(path)` ran. Anything
    older than max_age is definitely orphaned — a normal request's temp
    file lives for the duration of one HTTP call."""
    removed = []
    cutoff = time.time() - max_age_seconds
    if not os.path.isdir(dir_path):
        return removed
    for name in os.listdir(dir_path):
        path = os.path.join(dir_path, name)
        try:
            if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                os.remove(path)
                removed.append(name)
        except OSError:
            continue
    return removed


# ------------------------------------------------------------- garbage collection
@dataclass
class GCReport:
    deleted: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


def garbage_collect(provider: StorageProvider, stale_keys: list[str]) -> GCReport:
    """Delete storage objects for expired/abandoned upload sessions — keys
    the caller has already determined have no confirmed UserFile row."""
    report = GCReport()
    for key in stale_keys:
        try:
            provider.delete(key)
            report.deleted.append(key)
        except Exception:
            report.failed.append(key)
    return report


# ------------------------------------------------------------- reconciliation
@dataclass
class ReconcileReport:
    orphaned_keys: list[str] = field(default_factory=list)   # in storage, no DB row
    missing_keys: list[str] = field(default_factory=list)    # DB row, not in storage
    deleted: list[str] = field(default_factory=list)         # orphans actually removed


def reconcile(provider: StorageProvider, known_keys: set[str],
             dry_run: bool = True) -> ReconcileReport:
    """Compare what's actually in storage against what the DB references.
    Defaults to dry-run: this can find real drift either direction, but
    deleting orphans is destructive, so it only happens when explicitly
    asked for (`dry_run=False`) — never as a side effect of just checking."""
    report = ReconcileReport()
    stored_keys = set(provider.list_keys())

    report.orphaned_keys = sorted(stored_keys - known_keys)
    report.missing_keys = sorted(known_keys - stored_keys)

    if not dry_run:
        for key in report.orphaned_keys:
            try:
                provider.delete(key)
                report.deleted.append(key)
            except Exception:
                continue
    return report
