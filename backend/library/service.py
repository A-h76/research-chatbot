"""Import LibraryRecords into UserFile rows with DOI / title-year dedup."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from .normalize import LibraryRecord, normalize_doi, title_year_key

logger = logging.getLogger(__name__)


class LibraryImportService:
    """Creates metadata-only library stubs (same shape as Discover import)."""

    def __init__(
        self,
        SessionLocal,
        UserFile,
        Project,
        select_fn,
        *,
        enrich_file_from_doi: Callable[..., Any] | None = None,
        collection_service=None,
        max_records: int = 500,
    ):
        self.SessionLocal = SessionLocal
        self.UserFile = UserFile
        self.Project = Project
        self.select = select_fn
        self.enrich_file_from_doi = enrich_file_from_doi
        self.collection_service = collection_service
        self.max_records = max_records

    def _resolve_project(self, db, user_id: int, project_id: int | None) -> int | None:
        if project_id is None:
            return None
        proj = db.get(self.Project, project_id)
        if not proj or proj.user_id != user_id:
            return None
        return project_id

    def _find_existing(self, db, user_id: int, rec: LibraryRecord):
        doi = rec.normalized_doi()
        if doi:
            hit = (
                db.execute(
                    self.select(self.UserFile).where(
                        self.UserFile.user_id == user_id,
                        self.UserFile.doi == doi,
                    )
                )
                .scalars()
                .first()
            )
            if hit:
                return hit, "doi"

        ty = title_year_key(rec.title, rec.year)
        if ty and rec.title:
            candidates = (
                db.execute(
                    self.select(self.UserFile).where(
                        self.UserFile.user_id == user_id,
                        self.UserFile.kind == "document",
                        self.UserFile.title == rec.title[:500],
                    )
                )
                .scalars()
                .all()
            )
            for c in candidates:
                if title_year_key(c.title, c.year) == ty:
                    return c, "title_year"
        return None, None

    def _resolve_collection_ids(
        self,
        user_id: int,
        *,
        collection_id: int | None,
        create_collection_name: str | None,
        records: list[LibraryRecord],
        source: str,
    ) -> list[int]:
        """Return Dhund collection ids to attach imported papers to."""
        ids: list[int] = []
        if not self.collection_service:
            return ids

        if collection_id:
            coll = self.collection_service.get_collection(user_id, collection_id)
            if coll:
                ids.append(coll["id"])

        if create_collection_name:
            created = self.collection_service.create_collection(
                user_id,
                create_collection_name,
                source="import",
            )
            if created:
                ids.append(created["id"])

        # External collection keys (Zotero) — one folder per distinct key+name
        seen_ext: set[str] = set()
        for rec in records:
            for key in rec.collection_keys or []:
                if not key or key in seen_ext:
                    continue
                seen_ext.add(key)
                name = rec.collection_name or f"Zotero {key[:8]}"
                # Prefer a better name if we only have one key across the batch
                if len(records) and all(
                    key in (r.collection_keys or []) for r in records
                ) and records[0].collection_name:
                    name = records[0].collection_name
                coll = self.collection_service.get_or_create_external(
                    user_id,
                    name=name,
                    external_id=key,
                    source=source if source in {"zotero", "mendeley"} else "import",
                )
                if coll:
                    ids.append(coll["id"])

        # Deduplicate while preserving order
        out: list[int] = []
        for i in ids:
            if i not in out:
                out.append(i)
        return out

    def import_records(
        self,
        user_id: int,
        records: list[LibraryRecord],
        *,
        project_id: int | None = None,
        create_project_name: str | None = None,
        collection_id: int | None = None,
        create_collection_name: str | None = None,
        enrich: bool = True,
        source_tag: str | None = None,
    ) -> dict[str, Any]:
        if len(records) > self.max_records:
            return {
                "error": "too_many_records",
                "detail": f"Max {self.max_records} records per import.",
                "count": len(records),
            }

        source = (records[0].source if records else "bibtex") or "bibtex"
        collection_ids = self._resolve_collection_ids(
            user_id,
            collection_id=collection_id,
            create_collection_name=create_collection_name,
            records=records,
            source=source,
        )

        db = self.SessionLocal()
        created_ids: list[int] = []
        all_file_ids: list[int] = []
        skipped: list[dict] = []
        merged_project_id: int | None = None
        try:
            if create_project_name:
                name = (create_project_name or "Imported library").strip()[:100] or "Imported library"
                proj = self.Project(
                    user_id=user_id,
                    name=name,
                    emoji="📚",
                    description="Created from library import",
                )
                db.add(proj)
                db.flush()
                merged_project_id = proj.id
            else:
                merged_project_id = self._resolve_project(db, user_id, project_id)
                if project_id is not None and merged_project_id is None:
                    db.close()
                    return {"error": "project_not_found"}

            seen_keys: set[str] = set()
            for rec in records:
                key = rec.dedupe_key()
                if key and key in seen_keys:
                    skipped.append({"title": rec.title, "reason": "duplicate_in_batch", "doi": rec.doi})
                    continue
                if key:
                    seen_keys.add(key)

                existing, reason = self._find_existing(db, user_id, rec)
                if existing:
                    if merged_project_id and not existing.project_id:
                        existing.project_id = merged_project_id
                    all_file_ids.append(existing.id)
                    skipped.append(
                        {
                            "title": rec.title or existing.title,
                            "reason": f"already_exists:{reason}",
                            "file_id": existing.id,
                            "doi": rec.normalized_doi() or existing.doi or "",
                        }
                    )
                    continue

                tags = list(rec.tags or [])
                if source_tag and source_tag not in tags:
                    tags.append(source_tag)
                tags.append(f"import:{rec.source}")

                doi = rec.normalized_doi()
                uf = self.UserFile(
                    user_id=user_id,
                    project_id=merged_project_id,
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
                    metadata_source=rec.source if rec.source in {"bibtex", "ris", "zotero", "mendeley", "openalex"} else "user",
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
                        logger.warning("library import enrich skipped file_id=%s: %s", uf.id, exc)

                created_ids.append(uf.id)
                all_file_ids.append(uf.id)

            db.commit()
        except Exception:
            db.rollback()
            logger.exception("library import failed")
            return {"error": "import_failed"}
        finally:
            db.close()

        # Attach to collections after commit (separate sessions in CollectionService)
        for cid in collection_ids:
            if all_file_ids:
                self.collection_service.add_papers(user_id, cid, all_file_ids)

        return {
            "ok": True,
            "created": len(created_ids),
            "skipped": len(skipped),
            "created_ids": created_ids,
            "skipped_items": skipped[:100],
            "project_id": merged_project_id,
            "collection_ids": collection_ids,
        }


def records_from_user_files(files) -> list[LibraryRecord]:
    out: list[LibraryRecord] = []
    for f in files:
        out.append(
            LibraryRecord(
                title=getattr(f, "title", None) or getattr(f, "name", "") or "",
                authors=getattr(f, "authors", "") or "",
                year=getattr(f, "year", "") or "",
                venue=getattr(f, "venue", "") or "",
                doi=normalize_doi(getattr(f, "doi", "") or ""),
                abstract=getattr(f, "abstract", "") or "",
                url=getattr(f, "source_url", "") or "",
                source=getattr(f, "metadata_source", "") or "library",
                external_id=str(getattr(f, "id", "")),
            )
        )
    return out
