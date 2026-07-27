"""Phase 1b sync helpers — conflict-safe metadata merge + sync orchestration."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Callable

from .normalize import LibraryRecord, normalize_doi, title_year_key

logger = logging.getLogger(__name__)

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


def _norm_title(t: str) -> str:
    return _PUNCT.sub("", _WS.sub(" ", (t or "").strip().lower())).strip()


def title_similarity(a: str, b: str) -> float:
    na, nb = _norm_title(a), _norm_title(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def has_research_asset(uf) -> bool:
    """True when a real PDF / analysis pipeline is already attached."""
    path = (getattr(uf, "path", None) or "").strip()
    size = int(getattr(uf, "size", 0) or 0)
    meta = (getattr(uf, "meta_status", None) or "").lower()
    return bool(path) or size > 0 or meta in {"running", "pending"}


def merge_metadata_into_existing(
    uf,
    rec: LibraryRecord,
    *,
    protect_asset: bool,
) -> tuple[list[str], list[str]]:
    """Fill empty fields; optionally soft-update stub titles.

    Returns (updated_fields, conflict_fields).
    Never clears or rewrites path/size/checksum/content. Never touches
    analysis outputs — only bibliographic columns on the file row.
    """
    updated: list[str] = []
    conflicts: list[str] = []

    def _set_if_empty(attr: str, value: str, maxlen: int):
        nonlocal updated
        value = (value or "").strip()
        if not value:
            return
        existing = (getattr(uf, attr, None) or "").strip()
        if not existing:
            setattr(uf, attr, value[:maxlen])
            updated.append(attr)

    doi = rec.normalized_doi()
    _set_if_empty("doi", doi, 200)
    _set_if_empty("authors", rec.authors or "", 1000)
    _set_if_empty("year", rec.year or "", 10)
    _set_if_empty("venue", rec.venue or "", 300)
    _set_if_empty("abstract", rec.abstract or "", 8000)
    url = (rec.url or rec.pdf_url or "").strip()
    if url and not (getattr(uf, "source_url", None) or "").strip():
        uf.source_url = url[:500]
        updated.append("source_url")

    # external identity — always fill if empty
    if rec.external_id and not (getattr(uf, "external_item_id", None) or "").strip():
        uf.external_provider = (rec.source or "")[:30]
        uf.external_item_id = rec.external_id[:120]
        updated.append("external_item_id")

    remote_title = (rec.title or "").strip()
    existing_title = (getattr(uf, "title", None) or "").strip()
    if remote_title:
        if not existing_title:
            uf.title = remote_title[:500]
            if not (uf.name or "").strip() or uf.name == "imported-paper":
                uf.name = remote_title[:300]
            updated.append("title")
        elif not protect_asset:
            sim = title_similarity(existing_title, remote_title)
            if sim >= 0.85:
                if remote_title != existing_title:
                    uf.title = remote_title[:500]
                    updated.append("title")
            elif sim < 0.6:
                conflicts.append("title")
                logger.info(
                    "library sync title conflict file_id=%s sim=%.2f existing=%r remote=%r",
                    getattr(uf, "id", None),
                    sim,
                    existing_title[:60],
                    remote_title[:60],
                )
        else:
            # Research asset: never overwrite title; only note conflict
            if title_similarity(existing_title, remote_title) < 0.6:
                conflicts.append("title")

    return updated, conflicts


class LibrarySyncService:
    """Incremental sync orchestrator on top of LibraryImportService."""

    def __init__(
        self,
        SessionLocal,
        UserFile,
        LibraryConnection,
        LibrarySyncRun,
        select_fn,
        import_service,
        *,
        enrich_file_from_doi: Callable[..., Any] | None = None,
    ):
        self.SessionLocal = SessionLocal
        self.UserFile = UserFile
        self.LibraryConnection = LibraryConnection
        self.LibrarySyncRun = LibrarySyncRun
        self.select = select_fn
        self.import_service = import_service
        self.enrich_file_from_doi = enrich_file_from_doi

    def _find_existing(self, db, user_id: int, rec: LibraryRecord):
        ext = (rec.external_id or "").strip()
        src = (rec.source or "").strip()
        if ext and src:
            hit = (
                db.execute(
                    self.select(self.UserFile).where(
                        self.UserFile.user_id == user_id,
                        self.UserFile.external_provider == src,
                        self.UserFile.external_item_id == ext,
                    )
                )
                .scalars()
                .first()
            )
            if hit:
                return hit, "external_id"

        existing, reason = self.import_service._find_existing(db, user_id, rec)
        return existing, reason

    def apply_sync_records(
        self,
        user_id: int,
        records: list[LibraryRecord],
        *,
        enrich: bool = True,
        source_tag: str | None = None,
    ) -> dict[str, Any]:
        """Create new stubs; conflict-safe update existing; never touch PDFs/analysis."""
        created_ids: list[int] = []
        updated_ids: list[int] = []
        skipped: list[dict] = []
        conflicts: list[dict] = []

        db = self.SessionLocal()
        try:
            seen: set[str] = set()
            for rec in records:
                key = rec.dedupe_key() or f"ext:{rec.source}:{rec.external_id}"
                if key in seen:
                    skipped.append({"title": rec.title, "reason": "duplicate_in_batch"})
                    continue
                seen.add(key)

                existing, reason = self._find_existing(db, user_id, rec)
                if existing:
                    protect = has_research_asset(existing)
                    updated_fields, conflict_fields = merge_metadata_into_existing(
                        existing, rec, protect_asset=protect
                    )
                    if conflict_fields:
                        conflicts.append(
                            {
                                "file_id": existing.id,
                                "fields": conflict_fields,
                                "title": existing.title or rec.title,
                            }
                        )
                    if updated_fields:
                        updated_ids.append(existing.id)
                    else:
                        skipped.append(
                            {
                                "title": rec.title or existing.title,
                                "reason": f"unchanged:{reason}",
                                "file_id": existing.id,
                            }
                        )
                    continue

                # New record — reuse one-shot create path via mini batch
                tags = list(rec.tags or [])
                if source_tag and source_tag not in tags:
                    tags.append(source_tag)
                tags.append(f"import:{rec.source}")
                doi = rec.normalized_doi()
                uf = self.UserFile(
                    user_id=user_id,
                    project_id=None,
                    conversation_id=None,
                    name=rec.display_name(),
                    mime="",
                    kind="document",
                    path="",
                    size=0,
                    title=(rec.title or rec.display_name())[:500],
                    authors=(rec.authors or "")[:1000],
                    year=(rec.year or "")[:10],
                    venue=(rec.venue or "")[:300],
                    doi=doi[:200],
                    abstract=(rec.abstract or "")[:8000],
                    reading_status="unread",
                    tags=json.dumps(tags[:40]),
                    meta_status="done",
                    metadata_source=rec.source
                    if rec.source in {"bibtex", "ris", "zotero", "mendeley", "openalex"}
                    else "user",
                    source_url=(rec.url or rec.pdf_url or "")[:500],
                    doi_verified=False,
                    external_provider=(rec.source or "")[:30],
                    external_item_id=(rec.external_id or "")[:120],
                )
                db.add(uf)
                db.flush()
                if enrich and doi and self.enrich_file_from_doi:
                    try:
                        self.enrich_file_from_doi(db, uf.id)
                        db.refresh(uf)
                    except Exception as exc:
                        logger.warning("sync enrich skipped file_id=%s: %s", uf.id, exc)
                created_ids.append(uf.id)

            # Attach external collections for new + updated
            if self.import_service.collection_service:
                source = (records[0].source if records else "zotero") or "zotero"
                coll_ids = self.import_service._resolve_collection_ids(
                    user_id,
                    collection_id=None,
                    create_collection_name=None,
                    records=records,
                    source=source,
                )
                all_ids = created_ids + updated_ids
                db.commit()
                for cid in coll_ids:
                    if all_ids:
                        self.import_service.collection_service.add_papers(user_id, cid, all_ids)
            else:
                db.commit()
        except Exception:
            db.rollback()
            logger.exception("library sync apply failed")
            return {"error": "sync_failed"}
        finally:
            db.close()

        return {
            "ok": True,
            "created": len(created_ids),
            "updated": len(updated_ids),
            "skipped": len(skipped),
            "conflicts": len(conflicts),
            "created_ids": created_ids,
            "updated_ids": updated_ids,
            "skipped_items": skipped[:100],
            "conflict_items": conflicts[:50],
        }

    def start_run(self, user_id: int, connection_id: int | None, provider: str, cursor_before: str) -> int:
        db = self.SessionLocal()
        try:
            run = self.LibrarySyncRun(
                user_id=user_id,
                connection_id=connection_id,
                provider=provider,
                status="running",
                cursor_before=cursor_before or "",
            )
            db.add(run)
            db.commit()
            return run.id
        finally:
            db.close()

    def finish_run(
        self,
        run_id: int,
        *,
        status: str,
        created: int = 0,
        updated: int = 0,
        skipped: int = 0,
        conflicts: int = 0,
        cursor_after: str = "",
        error_text: str = "",
        detail: dict | None = None,
    ) -> None:
        db = self.SessionLocal()
        try:
            run = db.get(self.LibrarySyncRun, run_id)
            if not run:
                return
            run.status = status
            run.finished_at = datetime.now(timezone.utc)
            run.created_count = created
            run.updated_count = updated
            run.skipped_count = skipped
            run.conflict_count = conflicts
            run.cursor_after = cursor_after or ""
            run.error_text = (error_text or "")[:2000]
            run.detail_json = json.dumps(detail or {})[:8000]
            db.commit()
        finally:
            db.close()

    def list_runs(self, user_id: int, *, provider: str | None = None, limit: int = 20) -> list[dict]:
        db = self.SessionLocal()
        try:
            stmt = self.select(self.LibrarySyncRun).where(self.LibrarySyncRun.user_id == user_id)
            if provider:
                stmt = stmt.where(self.LibrarySyncRun.provider == provider)
            rows = (
                db.execute(stmt.order_by(self.LibrarySyncRun.started_at.desc()).limit(limit))
                .scalars()
                .all()
            )
            out = []
            for r in rows:
                out.append(
                    {
                        "id": r.id,
                        "provider": r.provider,
                        "status": r.status,
                        "started_at": r.started_at.isoformat() if r.started_at else None,
                        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                        "created": r.created_count or 0,
                        "updated": r.updated_count or 0,
                        "skipped": r.skipped_count or 0,
                        "conflicts": r.conflict_count or 0,
                        "error": r.error_text or "",
                    }
                )
            return out
        finally:
            db.close()
