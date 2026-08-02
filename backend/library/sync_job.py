"""Worker entrypoint for library_sync jobs (no Flask request context)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from security.token_crypto import seal_secret, unseal_secret

from . import mendeley as mendeley_mod
from .service import LibraryImportService
from .sync import LibrarySyncService, execute_provider_sync

logger = logging.getLogger(__name__)


def _oauth_plain(row, *, secret_key: str) -> dict[str, str]:
    return {
        "access_token": unseal_secret(row.access_token or "", secret_key=secret_key),
        "access_secret": unseal_secret(row.access_secret or "", secret_key=secret_key),
        "refresh_token": unseal_secret(row.refresh_token or "", secret_key=secret_key),
    }


def _store_oauth(row, *, secret_key: str, access_token=None, refresh_token=None):
    if access_token is not None:
        row.access_token = seal_secret(access_token, secret_key=secret_key)
    if refresh_token is not None:
        row.refresh_token = seal_secret(refresh_token, secret_key=secret_key)


def resolve_provider_tokens(
    db,
    row,
    provider: str,
    *,
    secret_key: str,
) -> dict[str, Any]:
    """Return adapter token kwargs; refresh Mendeley when needed."""
    if provider == "zotero":
        toks = _oauth_plain(row, secret_key=secret_key)
        return {
            "access_token": toks["access_token"],
            "access_secret": toks["access_secret"],
            "external_user_id": row.external_user_id,
        }
    toks = _oauth_plain(row, secret_key=secret_key)
    token = (toks["access_token"] or "").strip()
    if token:
        return {"access_token": token}
    refresh = (toks["refresh_token"] or "").strip()
    if not refresh:
        raise RuntimeError("mendeley_not_connected")
    refreshed = mendeley_mod.refresh_access_token(refresh)
    _store_oauth(
        row,
        secret_key=secret_key,
        access_token=refreshed.get("access_token") or "",
        refresh_token=refreshed.get("refresh_token") or refresh,
    )
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"access_token": _oauth_plain(row, secret_key=secret_key)["access_token"] or ""}


def run_library_sync_job(
    db,
    job,
    *,
    OutboxEvent,
    select_fn,
    SessionLocal,
    LibraryConnection,
    LibrarySyncRun,
    UserFile,
    Project=None,
    enrich_file_from_doi=None,
    secret_key: str = "",
) -> dict:
    """Execute one library_sync UploadJob. Raises on failure for worker retry."""
    events = (
        db.execute(
            select_fn(OutboxEvent).where(
                OutboxEvent.aggregate_type == "upload_job",
                OutboxEvent.aggregate_id == job.id,
            )
        )
        .scalars()
        .all()
    )
    payload: dict = {}
    for ev in events:
        try:
            raw = json.loads(ev.payload or "{}")
        except json.JSONDecodeError:
            raw = {}
        if isinstance(raw, dict) and raw.get("type") == "library_sync":
            payload = raw
            break
    if not payload:
        raise RuntimeError("library_sync missing outbox payload")

    provider = str(payload.get("provider") or "").strip().lower()
    if provider not in {"zotero", "mendeley"}:
        raise RuntimeError(f"unsupported library_sync provider: {provider}")
    connection_id = int(payload["connection_id"])
    run_id = int(payload["sync_run_id"])
    limit = int(payload.get("limit") or 200)
    cursor_before = payload.get("cursor_before") or ""

    row = db.get(LibraryConnection, connection_id)
    if not row or int(row.user_id) != int(job.user_id) or row.provider != provider:
        raise RuntimeError("library connection missing or mismatched")

    token_kwargs = resolve_provider_tokens(db, row, provider, secret_key=secret_key)

    import_svc = LibraryImportService(
        SessionLocal,
        UserFile,
        Project,
        select_fn,
        enrich_file_from_doi=enrich_file_from_doi,
        collection_service=None,
    )
    sync_service = LibrarySyncService(
        SessionLocal,
        UserFile,
        LibraryConnection,
        LibrarySyncRun,
        select_fn,
        import_svc,
        enrich_file_from_doi=enrich_file_from_doi,
    )

    sync_service.patch_run_detail(
        run_id,
        {"job_id": job.id, "phase": "running", "attempt": getattr(job, "attempts", 0)},
        status="running",
    )

    return execute_provider_sync(
        sync_service=sync_service,
        SessionLocal=SessionLocal,
        LibraryConnection=LibraryConnection,
        user_id=int(job.user_id),
        provider=provider,
        connection_id=connection_id,
        cursor_before=cursor_before or (row.sync_cursor or ""),
        token_kwargs=token_kwargs,
        limit=limit,
        run_id=run_id,
        job_id=job.id,
    )
