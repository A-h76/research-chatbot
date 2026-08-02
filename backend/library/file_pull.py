"""Ref-mgr PDF pull — download attachments onto metadata stubs + enqueue import."""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Callable

from backend.library.adapters import get_adapter
from backend.library.sync import has_research_asset

logger = logging.getLogger(__name__)


def stubs_needing_pdf(
    db,
    UserFile,
    select_fn,
    *,
    user_id: int,
    provider: str,
    file_ids: list[int] | None = None,
    limit: int = 20,
) -> list[Any]:
    """Metadata-only library rows linked to a ref-mgr item."""
    provider = (provider or "").strip().lower()
    limit = max(1, min(int(limit or 20), 50))
    q = select_fn(UserFile).where(
        UserFile.user_id == user_id,
        UserFile.external_provider == provider,
        UserFile.external_item_id.isnot(None),
        UserFile.external_item_id != "",
    )
    if file_ids:
        ids = [int(x) for x in file_ids if x is not None]
        if not ids:
            return []
        q = q.where(UserFile.id.in_(ids))
    rows = db.execute(q.limit(limit * 3)).scalars().all()
    out = []
    for uf in rows:
        if has_research_asset(uf):
            continue
        if not (getattr(uf, "external_item_id", None) or "").strip():
            continue
        out.append(uf)
        if len(out) >= limit:
            break
    return out


def apply_pdf_bytes_to_stub(
    db,
    uf,
    *,
    data: bytes,
    filename: str,
    content_type: str = "application/pdf",
    storage,
    upload_dir: str,
    enqueue_import: Callable | None,
    user_id: int,
    max_file_mb: int = 50,
) -> dict[str, Any]:
    """Store PDF on a stub and enqueue the shared ``import`` pipeline."""
    if has_research_asset(uf):
        return {"ok": False, "error": "already_has_pdf", "file_id": uf.id}

    if not data:
        return {"ok": False, "error": "empty_pdf", "file_id": uf.id}

    max_bytes = int(max_file_mb or 50) * 1024 * 1024
    if len(data) > max_bytes:
        return {"ok": False, "error": "file_too_large", "file_id": uf.id}

    from backend.upload.validation import kind_for_extension

    safe_name = (filename or "attachment.pdf").strip() or "attachment.pdf"
    if not safe_name.lower().endswith(".pdf"):
        safe_name = f"{safe_name}.pdf"
    ext = ".pdf"
    disk_name = uuid.uuid4().hex + ext
    path = os.path.join(upload_dir, disk_name)

    os.makedirs(upload_dir, exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    size = os.path.getsize(path)
    try:
        checksum = storage.sha256_file(path)
        storage.upload(disk_name, path)
    except Exception as exc:
        try:
            os.remove(path)
        except OSError:
            pass
        logger.warning("pdf pull storage failed file_id=%s: %s", uf.id, exc)
        return {"ok": False, "error": "storage_unavailable", "file_id": uf.id}
    finally:
        try:
            os.remove(path)
        except OSError:
            pass

    uf.path = disk_name
    uf.size = size
    uf.mime = content_type or "application/pdf"
    uf.kind = kind_for_extension(ext) or "document"
    uf.checksum_sha256 = checksum
    uf.meta_status = "pending"
    if not (uf.name or "").strip() or uf.name == uf.title:
        uf.name = safe_name[:300]
    db.flush()

    queued = False
    if enqueue_import:
        try:
            enqueue_import(db, user_id, uf.id)
            queued = True
        except Exception as exc:
            logger.warning("pdf pull enqueue failed file_id=%s: %s", uf.id, exc)
            queued = False

    return {
        "ok": True,
        "file_id": uf.id,
        "queued": queued,
        "size": size,
        "filename": safe_name,
    }


def pull_pdfs_for_provider(
    *,
    db,
    UserFile,
    select_fn,
    provider: str,
    user_id: int,
    token_kwargs: dict[str, Any],
    storage,
    upload_dir: str,
    enqueue_import: Callable | None,
    file_ids: list[int] | None = None,
    limit: int = 20,
    max_file_mb: int = 50,
) -> dict[str, Any]:
    """Pull PDFs from Zotero/Mendeley onto need_pdf stubs; enqueue import jobs."""
    provider = (provider or "").strip().lower()
    if provider not in {"zotero", "mendeley"}:
        return {"ok": False, "error": "unsupported_provider", "pulled": 0}

    adapter = get_adapter(provider)
    caps = adapter.capabilities()
    if not caps.file_import:
        return {"ok": False, "error": "file_import_unsupported", "pulled": 0}

    stubs = stubs_needing_pdf(
        db,
        UserFile,
        select_fn,
        user_id=user_id,
        provider=provider,
        file_ids=file_ids,
        limit=limit,
    )
    if not stubs:
        return {
            "ok": True,
            "pulled": 0,
            "queued": 0,
            "skipped": [],
            "errors": [],
            "results": [],
            "detail": "no_stubs_needing_pdf",
        }

    item_keys = [str(uf.external_item_id).strip() for uf in stubs]
    by_ext = {str(uf.external_item_id).strip(): uf for uf in stubs}

    max_bytes = int(max_file_mb or 50) * 1024 * 1024
    fetched = adapter.import_files(
        item_keys=item_keys,
        max_bytes=max_bytes,
        **token_kwargs,
    )

    results: list[dict[str, Any]] = []
    pulled = 0
    queued_n = 0
    for hit in fetched.get("downloaded") or []:
        ext_id = str(hit.get("external_id") or "").strip()
        uf = by_ext.get(ext_id)
        if not uf:
            continue
        applied = apply_pdf_bytes_to_stub(
            db,
            uf,
            data=hit.get("data") or b"",
            filename=str(hit.get("filename") or "attachment.pdf"),
            content_type=str(hit.get("content_type") or "application/pdf"),
            storage=storage,
            upload_dir=upload_dir,
            enqueue_import=enqueue_import,
            user_id=user_id,
            max_file_mb=max_file_mb,
        )
        results.append(applied)
        if applied.get("ok"):
            pulled += 1
            if applied.get("queued"):
                queued_n += 1

    return {
        "ok": True,
        "provider": provider,
        "pulled": pulled,
        "queued": queued_n,
        "skipped": fetched.get("skipped") or [],
        "errors": (fetched.get("errors") or [])
        + [r for r in results if not r.get("ok")],
        "results": results,
        "considered": len(stubs),
    }
