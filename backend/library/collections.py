"""Library collections — folders that reference Library papers (many-to-many)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class CollectionService:
    """CRUD + membership for library_collections / library_collection_papers."""

    def __init__(
        self,
        SessionLocal,
        LibraryCollection,
        LibraryCollectionPaper,
        UserFile,
        select_fn,
    ):
        self.SessionLocal = SessionLocal
        self.Collection = LibraryCollection
        self.Membership = LibraryCollectionPaper
        self.UserFile = UserFile
        self.select = select_fn

    def _owned(self, db, user_id: int, collection_id: int):
        row = db.get(self.Collection, collection_id)
        if not row or row.user_id != user_id:
            return None
        return row

    def _paper_count(self, db, collection_id: int) -> int:
        from sqlalchemy import func

        return (
            db.execute(
                self.select(func.count())
                .select_from(self.Membership)
                .where(self.Membership.collection_id == collection_id)
            ).scalar()
            or 0
        )

    def _to_dict(self, row, *, paper_count: int | None = None) -> dict[str, Any]:
        return {
            "id": row.id,
            "name": row.name,
            "description": row.description or "",
            "parent_id": row.parent_id,
            "external_id": row.external_id or "",
            "source": row.source or "manual",
            "sort_order": row.sort_order or 0,
            "paper_count": paper_count if paper_count is not None else 0,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    def list_collections(self, user_id: int) -> list[dict]:
        db = self.SessionLocal()
        try:
            rows = (
                db.execute(
                    self.select(self.Collection)
                    .where(self.Collection.user_id == user_id)
                    .order_by(self.Collection.sort_order, self.Collection.name)
                )
                .scalars()
                .all()
            )
            return [self._to_dict(r, paper_count=self._paper_count(db, r.id)) for r in rows]
        finally:
            db.close()

    def get_collection(self, user_id: int, collection_id: int) -> dict | None:
        db = self.SessionLocal()
        try:
            row = self._owned(db, user_id, collection_id)
            if not row:
                return None
            return self._to_dict(row, paper_count=self._paper_count(db, row.id))
        finally:
            db.close()

    def create_collection(
        self,
        user_id: int,
        name: str,
        *,
        description: str = "",
        parent_id: int | None = None,
        external_id: str = "",
        source: str = "manual",
        sort_order: int = 0,
    ) -> dict | None:
        name = (name or "").strip()[:200]
        if not name:
            return None
        db = self.SessionLocal()
        try:
            if parent_id is not None:
                parent = self._owned(db, user_id, parent_id)
                if not parent:
                    return None
            row = self.Collection(
                user_id=user_id,
                name=name,
                description=(description or "")[:2000],
                parent_id=parent_id,
                external_id=(external_id or "")[:100],
                source=(source or "manual")[:30],
                sort_order=sort_order,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._to_dict(row, paper_count=0)
        except Exception:
            db.rollback()
            logger.exception("create_collection failed")
            return None
        finally:
            db.close()

    def update_collection(
        self,
        user_id: int,
        collection_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
        parent_id: int | None = ...,  # type: ignore[assignment]
        sort_order: int | None = None,
    ) -> dict | None:
        db = self.SessionLocal()
        try:
            row = self._owned(db, user_id, collection_id)
            if not row:
                return None
            if name is not None:
                name = name.strip()[:200]
                if not name:
                    return None
                row.name = name
            if description is not None:
                row.description = description[:2000]
            if parent_id is not ...:
                if parent_id is not None:
                    if parent_id == collection_id:
                        return None
                    parent = self._owned(db, user_id, parent_id)
                    if not parent:
                        return None
                row.parent_id = parent_id
            if sort_order is not None:
                row.sort_order = sort_order
            row.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(row)
            return self._to_dict(row, paper_count=self._paper_count(db, row.id))
        except Exception:
            db.rollback()
            logger.exception("update_collection failed")
            return None
        finally:
            db.close()

    def delete_collection(self, user_id: int, collection_id: int) -> bool:
        """Delete folder only — papers stay in Library."""
        db = self.SessionLocal()
        try:
            row = self._owned(db, user_id, collection_id)
            if not row:
                return False
            # Re-parent children to this collection's parent
            children = (
                db.execute(
                    self.select(self.Collection).where(
                        self.Collection.user_id == user_id,
                        self.Collection.parent_id == collection_id,
                    )
                )
                .scalars()
                .all()
            )
            for child in children:
                child.parent_id = row.parent_id
            from sqlalchemy import delete as sa_delete

            db.execute(sa_delete(self.Membership).where(self.Membership.collection_id == collection_id))
            db.delete(row)
            db.commit()
            return True
        except Exception:
            db.rollback()
            logger.exception("delete_collection failed")
            return False
        finally:
            db.close()

    def get_or_create_external(
        self,
        user_id: int,
        *,
        name: str,
        external_id: str,
        source: str = "zotero",
        parent_id: int | None = None,
        description: str = "",
    ) -> dict | None:
        """Idempotent collection for Connect imports (Zotero key → folder)."""
        external_id = (external_id or "").strip()[:100]
        name = (name or "").strip()[:200] or "Imported"
        if not external_id:
            return self.create_collection(
                user_id, name, description=description, parent_id=parent_id, source=source
            )
        db = self.SessionLocal()
        try:
            existing = (
                db.execute(
                    self.select(self.Collection).where(
                        self.Collection.user_id == user_id,
                        self.Collection.source == source,
                        self.Collection.external_id == external_id,
                    )
                )
                .scalars()
                .first()
            )
            if existing:
                if name and existing.name != name:
                    existing.name = name
                    existing.updated_at = datetime.now(timezone.utc)
                    db.commit()
                    db.refresh(existing)
                return self._to_dict(existing, paper_count=self._paper_count(db, existing.id))
            row = self.Collection(
                user_id=user_id,
                name=name,
                description=description[:2000],
                parent_id=parent_id,
                external_id=external_id,
                source=source,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._to_dict(row, paper_count=0)
        except Exception:
            db.rollback()
            logger.exception("get_or_create_external failed")
            return None
        finally:
            db.close()

    def add_papers(self, user_id: int, collection_id: int, file_ids: list[int]) -> dict:
        db = self.SessionLocal()
        try:
            row = self._owned(db, user_id, collection_id)
            if not row:
                return {"error": "not_found"}
            added = 0
            skipped = 0
            for fid in file_ids:
                uf = db.get(self.UserFile, fid)
                if not uf or uf.user_id != user_id:
                    skipped += 1
                    continue
                exists = (
                    db.execute(
                        self.select(self.Membership).where(
                            self.Membership.collection_id == collection_id,
                            self.Membership.file_id == fid,
                        )
                    )
                    .scalars()
                    .first()
                )
                if exists:
                    skipped += 1
                    continue
                db.add(self.Membership(collection_id=collection_id, file_id=fid))
                added += 1
            db.commit()
            return {
                "ok": True,
                "added": added,
                "skipped": skipped,
                "paper_count": self._paper_count(db, collection_id),
            }
        except Exception:
            db.rollback()
            logger.exception("add_papers failed")
            return {"error": "failed"}
        finally:
            db.close()

    def remove_papers(self, user_id: int, collection_id: int, file_ids: list[int]) -> dict:
        db = self.SessionLocal()
        try:
            row = self._owned(db, user_id, collection_id)
            if not row:
                return {"error": "not_found"}
            removed = 0
            for fid in file_ids:
                mem = (
                    db.execute(
                        self.select(self.Membership).where(
                            self.Membership.collection_id == collection_id,
                            self.Membership.file_id == fid,
                        )
                    )
                    .scalars()
                    .first()
                )
                if mem:
                    db.delete(mem)
                    removed += 1
            db.commit()
            return {
                "ok": True,
                "removed": removed,
                "paper_count": self._paper_count(db, collection_id),
            }
        except Exception:
            db.rollback()
            return {"error": "failed"}
        finally:
            db.close()

    def file_ids_in_collection(self, user_id: int, collection_id: int) -> list[int] | None:
        db = self.SessionLocal()
        try:
            row = self._owned(db, user_id, collection_id)
            if not row:
                return None
            ids = (
                db.execute(
                    self.select(self.Membership.file_id).where(
                        self.Membership.collection_id == collection_id
                    )
                )
                .scalars()
                .all()
            )
            return list(ids)
        finally:
            db.close()
