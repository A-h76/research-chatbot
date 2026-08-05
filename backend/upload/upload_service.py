"""Canonical UploadService (Bite 13) — one accept/register implementation.

Public HTTP APIs stay dual (session + JWT) per ADR-0014. Storage façades stay
dual (``storage/`` vs ``backend/storage/``). Business policy converges here:

    validate (route)
        ↓
    store via stack-specific StorageFacade
        ↓
    UploadService.register()  → UserFile + UploadBatch + ImportService.enqueue

Do not merge storage folders. Do not change worker or upload_jobs schema.
"""

from __future__ import annotations

import io
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)

UPLOAD_SERVICE_VERSION = "1.0"


@dataclass
class UploadResult:
    ok: bool
    user_file: Any = None
    job_id: int | None = None
    batch_id: int | None = None
    duplicate: bool = False
    error: str | None = None
    spine: str = UPLOAD_SERVICE_VERSION


class SessionStorageFacade:
    """Adapter over root ``storage/`` (StorageManager) — Stack A."""

    def __init__(self, storage: Any):
        self.storage = storage

    def new_key(self, ext: str) -> str:
        return uuid.uuid4().hex + (ext or "")

    def sha256_file(self, path: str) -> str:
        return self.storage.sha256_file(path)

    def upload_path(self, key: str, local_path: str) -> str:
        self.storage.upload(key, local_path)
        return key

    def delete(self, key: str) -> None:
        try:
            self.storage.delete(key)
        except Exception:
            logger.debug("session storage delete soft-fail key=%s", key, exc_info=True)


class JwtStorageFacade:
    """Adapter over ``backend/storage`` StorageBackend — Stack B."""

    def __init__(self, storage_backend: Any):
        self.backend = storage_backend

    def new_document_key(self, user_id: int, filename: str) -> str:
        return f"users/{user_id}/documents/{uuid.uuid4().hex}/{filename}"

    def new_bulk_key(self, user_id: int, batch_id: int, filename: str) -> str:
        return f"users/{user_id}/uploads/{batch_id}/{uuid.uuid4().hex}/{filename}"

    def upload_bytes(self, key: str, data: bytes, *, content_type: str) -> str:
        self.backend.upload(io.BytesIO(data), key, content_type=content_type)
        return key

    def delete(self, key: str) -> None:
        try:
            self.backend.delete(key)
        except Exception:
            logger.debug("jwt storage delete soft-fail key=%s", key, exc_info=True)


class UploadService:
    """Shared upload register policy for all document upload entry points."""

    def __init__(
        self,
        UserFile: Any,
        UploadBatch: Any,
        *,
        import_spine: Any = None,
        find_duplicate_file: Callable | None = None,
        UploadJob: Any = None,
        OutboxEvent: Any = None,
    ):
        self.UserFile = UserFile
        self.UploadBatch = UploadBatch
        self.import_spine = import_spine
        self.find_duplicate_file = find_duplicate_file
        self.UploadJob = UploadJob
        self.OutboxEvent = OutboxEvent

    def find_checksum_duplicate(self, db, user_id: int, checksum: str | None) -> Any | None:
        if not checksum or not self.find_duplicate_file:
            return None
        return self.find_duplicate_file(db, user_id, checksum)

    def ensure_batch(
        self,
        db,
        user_id: int,
        *,
        batch_id: int | None = None,
        source: str = "library",
        project_id: int | None = None,
        conversation_id: int | None = None,
        file_count: int | None = None,
        increment: bool = True,
    ) -> Any:
        """Return an UploadBatch owned by user_id; create when missing."""
        batch = db.get(self.UploadBatch, batch_id) if batch_id else None
        if not batch or batch.user_id != user_id:
            kwargs: dict[str, Any] = {
                "user_id": user_id,
                "source": source,
                "file_count": file_count if file_count is not None else 0,
            }
            # Real UploadBatch has these; some test doubles omit them.
            if hasattr(self.UploadBatch, "project_id"):
                kwargs["project_id"] = project_id
            if hasattr(self.UploadBatch, "conversation_id"):
                kwargs["conversation_id"] = conversation_id
            batch = self.UploadBatch(**kwargs)
            db.add(batch)
            db.flush()
        if increment:
            batch.file_count = (batch.file_count or 0) + 1
        elif file_count is not None:
            batch.file_count = file_count
        return batch

    def register(
        self,
        db,
        *,
        user_id: int,
        name: str,
        mime: str,
        kind: str,
        path: str,
        size: int,
        checksum_sha256: str | None = None,
        project_id: int | None = None,
        conversation_id: int | None = None,
        batch: Any | None = None,
        batch_source: str = "library",
        create_batch: bool = True,
        enqueue: bool = True,
    ) -> UploadResult:
        """Create UserFile and enqueue the shared ``import`` job via ImportService.

        Caller is responsible for storing bytes (via a StorageFacade) and for
        stack-specific quota accounting. This method is the single register
        implementation for session, JWT, bulk, and presign confirm.
        """
        if create_batch and batch is None:
            batch = self.ensure_batch(
                db,
                user_id,
                source=batch_source,
                project_id=project_id,
                conversation_id=conversation_id,
                increment=True,
            )

        uf_kwargs: dict[str, Any] = {
            "user_id": user_id,
            "name": (name or "upload")[:300],
            "mime": mime or "",
            "kind": kind or "document",
            "path": path,
            "size": int(size or 0),
            "project_id": project_id,
            "conversation_id": conversation_id,
        }
        if hasattr(self.UserFile, "checksum_sha256"):
            uf_kwargs["checksum_sha256"] = checksum_sha256
        uf = self.UserFile(**uf_kwargs)
        db.add(uf)
        db.flush()

        job_id = None
        if enqueue and (kind or "document") == "document":
            batch_id = getattr(batch, "id", None) if batch is not None else None
            if self.import_spine is not None:
                job_id = self.import_spine.enqueue_after_store(
                    db, user_id, uf.id, upload_batch_id=batch_id
                )
            elif self.UploadJob is not None and self.OutboxEvent is not None:
                from backend.jobs.outbox import enqueue_upload_job_with_outbox

                job = enqueue_upload_job_with_outbox(
                    db,
                    UploadJob=self.UploadJob,
                    OutboxEvent=self.OutboxEvent,
                    user_id=user_id,
                    file_id=uf.id,
                    job_type="import",
                    upload_batch_id=batch_id,
                )
                job_id = getattr(job, "id", None)

        return UploadResult(
            ok=True,
            user_file=uf,
            job_id=job_id,
            batch_id=getattr(batch, "id", None) if batch is not None else None,
            spine=UPLOAD_SERVICE_VERSION,
        )

    def store_session_and_register(
        self,
        db,
        facade: SessionStorageFacade,
        *,
        user_id: int,
        local_path: str,
        filename: str,
        mime: str,
        kind: str,
        size: int,
        ext: str,
        project_id: int | None = None,
        conversation_id: int | None = None,
        batch_id: int | None = None,
        batch_source: str = "library",
        skip_dedup: bool = False,
    ) -> UploadResult:
        """Stack A: checksum → optional dedup → storage.upload → register."""
        checksum = facade.sha256_file(local_path)
        if not skip_dedup:
            dup = self.find_checksum_duplicate(db, user_id, checksum)
            if dup:
                return UploadResult(
                    ok=True,
                    user_file=dup,
                    duplicate=True,
                    spine=UPLOAD_SERVICE_VERSION,
                )

        key = facade.new_key(ext)
        try:
            facade.upload_path(key, local_path)
        except Exception:
            logger.exception("session storage upload failed key=%s", key)
            return UploadResult(ok=False, error="storage_unavailable", spine=UPLOAD_SERVICE_VERSION)

        batch = self.ensure_batch(
            db,
            user_id,
            batch_id=batch_id,
            source=batch_source,
            project_id=project_id,
            conversation_id=conversation_id,
            increment=True,
        )
        return self.register(
            db,
            user_id=user_id,
            name=filename,
            mime=mime,
            kind=kind,
            path=key,
            size=size,
            checksum_sha256=checksum,
            project_id=project_id,
            conversation_id=conversation_id,
            batch=batch,
            batch_source=batch_source,
            create_batch=False,
        )

    def store_jwt_bytes_and_register(
        self,
        db,
        facade: JwtStorageFacade,
        *,
        user_id: int,
        data: bytes,
        filename: str,
        mime: str,
        kind: str,
        key: str | None = None,
        project_id: int | None = None,
        batch: Any | None = None,
        batch_source: str = "api_documents",
        create_batch: bool = True,
    ) -> UploadResult:
        """Stack B: storage_backend.upload(bytes) → register."""
        size = len(data or b"")
        if create_batch and batch is None:
            batch = self.ensure_batch(
                db,
                user_id,
                source=batch_source,
                file_count=0,
                project_id=project_id,
                increment=False,
            )
            batch.file_count = (batch.file_count or 0) + 1

        object_key = key or facade.new_document_key(user_id, filename)
        try:
            facade.upload_bytes(object_key, data, content_type=mime)
        except Exception:
            logger.exception("jwt storage upload failed key=%s", object_key)
            return UploadResult(ok=False, error="storage_unavailable", spine=UPLOAD_SERVICE_VERSION)

        result = self.register(
            db,
            user_id=user_id,
            name=filename,
            mime=mime,
            kind=kind,
            path=object_key,
            size=size,
            project_id=project_id,
            batch=batch,
            batch_source=batch_source,
            create_batch=False,
        )
        if not result.ok:
            facade.delete(object_key)
        return result
