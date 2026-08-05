"""Canonical Import Spine (Bite 12) — single post-acquisition implementation.

Providers stay thin: they acquire metadata or bytes, then call ImportService.
After this boundary every path converges on:

    stub / identity
        ↓
    attach PDF (held bytes)  OR  UFTR resolve_and_attach (references)
        ↓
    enqueue ``import`` job  →  Worker → SUE → Evidence

Do not put provider HTTP / OAuth here. Do not rewrite worker or upload_jobs.
UploadService (Bite 13) will own accept/store policy; this module owns
library import policy + shared enqueue/attach/UFTR entry.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

IMPORT_SPINE_VERSION = "1.0"


@dataclass
class ImportIdentity:
    """Bibliographic + provenance identity for a library row (pre- or post-bytes)."""

    user_id: int
    project_id: int | None = None
    name: str = ""
    title: str = ""
    authors: str = ""
    year: str = ""
    venue: str = ""
    doi: str = ""
    abstract: str = ""
    source_url: str = ""
    metadata_source: str = "user"
    external_provider: str = ""
    external_item_id: str = ""
    tags: list[str] = field(default_factory=list)
    meta_status: str = "done"
    reading_status: str = "unread"


class ImportService:
    """Business policy for library acquisition after provider edges."""

    def __init__(
        self,
        UserFile: Any,
        select_fn: Callable,
        *,
        storage: Any = None,
        upload_dir: str | None = None,
        enqueue_import: Callable | None = None,
        max_file_mb: int = 50,
        enrich_file_from_doi: Callable | None = None,
        UploadJob: Any = None,
        OutboxEvent: Any = None,
    ):
        self.UserFile = UserFile
        self.select = select_fn
        self.storage = storage
        self.upload_dir = upload_dir
        self._enqueue_import = enqueue_import
        self.max_file_mb = max_file_mb
        self.enrich_file_from_doi = enrich_file_from_doi
        self.UploadJob = UploadJob
        self.OutboxEvent = OutboxEvent

    # ── identity / dedup ───────────────────────────────────────────────

    def find_duplicate(
        self,
        db,
        user_id: int,
        *,
        doi: str | None = None,
        external_provider: str | None = None,
        external_item_id: str | None = None,
    ) -> Any | None:
        """DOI first, then external_provider + external_item_id."""
        doi_n = (doi or "").strip()
        if doi_n:
            hit = (
                db.execute(
                    self.select(self.UserFile).where(
                        self.UserFile.user_id == user_id,
                        self.UserFile.doi == doi_n,
                    )
                )
                .scalars()
                .first()
            )
            if hit:
                return hit

        prov = (external_provider or "").strip()
        ext = (external_item_id or "").strip()
        if prov and ext:
            hit = (
                db.execute(
                    self.select(self.UserFile).where(
                        self.UserFile.user_id == user_id,
                        self.UserFile.external_provider == prov,
                        self.UserFile.external_item_id == ext,
                    )
                )
                .scalars()
                .first()
            )
            if hit:
                return hit
        return None

    def create_stub(self, db, identity: ImportIdentity) -> Any:
        """Create a metadata-only (or empty) UserFile stub. No commit."""
        tags = list(identity.tags or [])
        display = (identity.name or identity.title or "import")[:300]
        uf = self.UserFile(
            user_id=identity.user_id,
            project_id=identity.project_id,
            conversation_id=None,
            name=display,
            mime="",
            kind="document",
            path="",
            size=0,
            title=(identity.title or display)[:500],
            authors=(identity.authors or "")[:1000],
            year=(identity.year or "")[:10],
            venue=(identity.venue or "")[:300],
            doi=(identity.doi or "")[:200],
            abstract=(identity.abstract or "")[:8000],
            reading_status=identity.reading_status or "unread",
            tags=json.dumps(tags[:40]),
            meta_status=identity.meta_status or "done",
            metadata_source=(identity.metadata_source or "user")[:40],
            source_url=(identity.source_url or "")[:500],
            doi_verified=False,
            external_provider=(identity.external_provider or "")[:30],
            external_item_id=(identity.external_item_id or "")[:120],
        )
        db.add(uf)
        db.flush()
        return uf

    def maybe_enrich_doi(self, db, uf) -> None:
        doi = (getattr(uf, "doi", None) or "").strip()
        if not doi or not self.enrich_file_from_doi:
            return
        try:
            self.enrich_file_from_doi(db, uf.id)
            db.refresh(uf)
        except Exception as exc:
            logger.warning("import_service enrich skipped file_id=%s: %s", uf.id, exc)

    # ── enqueue (shared worker chain) ─────────────────────────────────

    def enqueue_after_store(
        self,
        db,
        user_id: int,
        file_id: int,
        *,
        upload_batch_id: int | None = None,
    ) -> int | None:
        """Enqueue the shared ``import`` job after bytes are already on a UserFile.

        Used by Upload stacks (session + JWT) and any path that stored bytes
        outside ``attach_pdf_bytes``. Prefer this over inlining UploadJob writes.
        Returns UploadJob.id when known, else None (still may have enqueued via DI).
        """
        return self._enqueue(db, user_id, file_id, upload_batch_id=upload_batch_id)

    def _enqueue(
        self,
        db,
        user_id: int,
        file_id: int,
        *,
        upload_batch_id: int | None = None,
    ) -> int | None:
        if self.UploadJob is not None and self.OutboxEvent is not None:
            try:
                from backend.jobs.outbox import enqueue_upload_job_with_outbox

                job = enqueue_upload_job_with_outbox(
                    db,
                    UploadJob=self.UploadJob,
                    OutboxEvent=self.OutboxEvent,
                    user_id=user_id,
                    file_id=file_id,
                    job_type="import",
                    upload_batch_id=upload_batch_id,
                )
                return getattr(job, "id", None)
            except Exception as exc:
                logger.warning(
                    "import_service outbox enqueue failed file_id=%s: %s", file_id, exc
                )
                return None

        if self._enqueue_import is not None:
            try:
                try:
                    result = self._enqueue_import(
                        db, user_id, file_id, upload_batch_id=upload_batch_id
                    )
                except TypeError:
                    result = self._enqueue_import(db, user_id, file_id)
                return result if isinstance(result, int) else None
            except Exception as exc:
                logger.warning(
                    "import_service enqueue failed file_id=%s: %s", file_id, exc
                )
                return None
        return None

    def _make_enqueue_fn(self) -> Callable | None:
        if self._enqueue_import is None and (
            self.UploadJob is None or self.OutboxEvent is None
        ):
            return None

        def _fn(db, user_id, file_id, upload_batch_id=None):
            self._enqueue(db, user_id, file_id, upload_batch_id=upload_batch_id)

        return _fn

    # ── PDF attach (held bytes) ───────────────────────────────────────

    def attach_pdf_bytes(
        self,
        db,
        uf,
        *,
        data: bytes,
        filename: str,
        user_id: int,
        content_type: str = "application/pdf",
    ) -> dict[str, Any]:
        """Store held PDF bytes on a stub and enqueue import (Golden Rule)."""
        from backend.library.file_pull import apply_pdf_bytes_to_stub

        if self.storage is None or not self.upload_dir:
            return {
                "ok": False,
                "error": "storage_not_configured",
                "file_id": getattr(uf, "id", None),
            }

        return apply_pdf_bytes_to_stub(
            db,
            uf,
            data=data,
            filename=filename,
            content_type=content_type,
            storage=self.storage,
            upload_dir=self.upload_dir,
            enqueue_import=self._make_enqueue_fn(),
            user_id=user_id,
            max_file_mb=self.max_file_mb,
        )

    def attach_manual_pdf(
        self,
        db,
        uf,
        *,
        data: bytes,
        filename: str,
        user_id: int,
        content_type: str = "application/pdf",
    ) -> dict[str, Any]:
        """Manual Attach PDF — same attach spine + UFTR manual provenance."""
        applied = self.attach_pdf_bytes(
            db,
            uf,
            data=data,
            filename=filename,
            user_id=user_id,
            content_type=content_type,
        )
        if applied.get("ok"):
            try:
                from backend.scholarly.uftr.state import record_manual_attach

                record_manual_attach(uf, source="manual")
            except Exception:
                pass
        return applied

    # ── UFTR (reference → full text) ──────────────────────────────────

    def resolve_fulltext(
        self,
        db,
        uf,
        *,
        user_id: int,
        work: Any = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """UFTR platform entry (ADR-0015) — no per-provider PDF fetch."""
        if self.storage is None or not self.upload_dir:
            return {
                "pdf_attached": False,
                "analysis_queued": False,
                "pdf_error": "storage_not_configured",
                "fulltext": None,
            }
        try:
            from backend.scholarly.uftr import resolve_and_attach

            result = resolve_and_attach(
                db,
                uf,
                storage=self.storage,
                upload_dir=self.upload_dir,
                enqueue_import=self._make_enqueue_fn(),
                user_id=user_id,
                max_file_mb=self.max_file_mb,
                work=work,
                force=force,
            )
            self._note_uftr_workflow(uf, user_id=user_id, result=result)
            return result
        except Exception as exc:
            logger.warning("import_service UFTR failed file_id=%s: %s", uf.id, exc)
            fail = {
                "pdf_attached": False,
                "analysis_queued": False,
                "pdf_error": "uftr_failed",
                "fulltext": None,
            }
            self._note_uftr_workflow(uf, user_id=user_id, result=fail)
            return fail

    def _note_uftr_workflow(self, uf, *, user_id: int, result: dict[str, Any]) -> None:
        try:
            from backend.workflow.engine import get_engine

            get_engine().note_uftr_result(
                user_id=int(user_id),
                file_id=int(uf.id),
                project_id=getattr(uf, "project_id", None),
                pdf_attached=bool(result.get("pdf_attached")),
                analysis_queued=bool(result.get("analysis_queued")),
                pdf_error=result.get("pdf_error"),
            )
        except Exception:
            logger.warning("UFTR workflow note failed", exc_info=True)

    # ── high-level acquisition APIs ───────────────────────────────────

    def import_reference(
        self,
        db,
        identity: ImportIdentity,
        *,
        work: Any = None,
        enrich_doi: bool = True,
    ) -> dict[str, Any]:
        """Discover / scholarly reference import: dedupe → stub → enrich → UFTR."""
        existing = self.find_duplicate(
            db,
            identity.user_id,
            doi=identity.doi,
            external_provider=identity.external_provider,
            external_item_id=identity.external_item_id,
        )
        if existing:
            return {
                "already_exists": True,
                "file": existing,
                "created": False,
                "spine": IMPORT_SPINE_VERSION,
            }

        uf = self.create_stub(db, identity)
        if enrich_doi:
            self.maybe_enrich_doi(db, uf)

        attach_meta = self.resolve_fulltext(db, uf, user_id=identity.user_id, work=work)
        self._emit_paper_imported(uf, identity=identity, source=identity.external_provider or identity.metadata_source)
        return {
            "already_exists": False,
            "file": uf,
            "created": True,
            "attach": attach_meta,
            "spine": IMPORT_SPINE_VERSION,
        }

    def import_held_bytes(
        self,
        db,
        identity: ImportIdentity,
        *,
        data: bytes,
        filename: str,
        content_type: str = "application/pdf",
    ) -> dict[str, Any]:
        """Cloud-drive / held-bytes import: dedupe → stub → attach → enqueue."""
        existing = self.find_duplicate(
            db,
            identity.user_id,
            doi=identity.doi or None,
            external_provider=identity.external_provider,
            external_item_id=identity.external_item_id,
        )
        if existing:
            return {
                "already_exists": True,
                "file": existing,
                "created": False,
                "ok": False,
                "error": "already_exists",
                "spine": IMPORT_SPINE_VERSION,
            }

        # Held-bytes stubs start pending until attach fills path/size.
        identity.meta_status = identity.meta_status or "pending"
        uf = self.create_stub(db, identity)
        applied = self.attach_pdf_bytes(
            db,
            uf,
            data=data,
            filename=filename,
            user_id=identity.user_id,
            content_type=content_type,
        )
        if applied.get("ok"):
            self._emit_paper_imported(
                uf,
                identity=identity,
                source=identity.external_provider or identity.metadata_source or "held_bytes",
            )
        return {
            "already_exists": False,
            "file": uf,
            "created": True,
            "ok": bool(applied.get("ok")),
            "queued": bool(applied.get("queued")),
            "attach": applied,
            "spine": IMPORT_SPINE_VERSION,
            "error": applied.get("error"),
        }

    def _emit_paper_imported(self, uf, *, identity: ImportIdentity, source: str) -> None:
        """Domain event — sync bus; never fails the import path."""
        try:
            from backend.domain_events import paper_imported, publish

            publish(
                paper_imported(
                    user_id=int(identity.user_id),
                    file_id=int(uf.id),
                    project_id=getattr(uf, "project_id", None) or identity.project_id,
                    source=source or "",
                    already_exists=False,
                )
            )
        except Exception:
            logger.warning("PaperImported domain event failed", exc_info=True)
