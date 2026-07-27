"""Library health + duplicate discovery for Phase 1c."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .normalize import LibraryRecord, normalize_doi, title_year_key
from .readiness import READINESS_ORDER, research_readiness
from .sync import merge_metadata_into_existing


def build_library_health(
    db,
    UserFile,
    select_fn,
    user_id: int,
    *,
    project_id: int | None = None,
    LibrarySyncRun=None,
    LibraryConnection=None,
) -> dict[str, Any]:
    stmt = select_fn(UserFile).where(
        UserFile.user_id == user_id,
        UserFile.kind == "document",
    )
    if project_id is not None:
        stmt = stmt.where(UserFile.project_id == project_id)
    files = db.execute(stmt).scalars().all()

    counts = {k: 0 for k in READINESS_ORDER}
    processing = 0
    need_pdf = 0
    for f in files:
        try:
            n_chunks = len(f.chunks) if getattr(f, "chunks", None) is not None else 0
        except Exception:
            n_chunks = 0
        state = research_readiness(f, chunk_count=n_chunks)
        counts[state] = counts.get(state, 0) + 1
        if state == "metadata_only":
            need_pdf += 1
        meta = (f.meta_status or "").lower()
        if (f.path or "").strip() and meta in {"pending", "running"}:
            processing += 1

    total = len(files)
    stub_ratio = (need_pdf / total) if total else 0.0

    sync: dict[str, Any] = {"runs": [], "connections": []}
    if LibraryConnection is not None:
        rows = (
            db.execute(
                select_fn(LibraryConnection).where(
                    LibraryConnection.user_id == user_id,
                    LibraryConnection.status == "active",
                )
            )
            .scalars()
            .all()
        )
        for r in rows:
            sync["connections"].append(
                {
                    "provider": r.provider,
                    "last_synced_at": r.last_synced_at.isoformat() if r.last_synced_at else None,
                    "has_cursor": bool((r.sync_cursor or "").strip()),
                }
            )
    if LibrarySyncRun is not None:
        runs = (
            db.execute(
                select_fn(LibrarySyncRun)
                .where(LibrarySyncRun.user_id == user_id)
                .order_by(LibrarySyncRun.started_at.desc())
                .limit(5)
            )
            .scalars()
            .all()
        )
        for r in runs:
            sync["runs"].append(
                {
                    "id": r.id,
                    "provider": r.provider,
                    "status": r.status,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "created": r.created_count or 0,
                    "updated": r.updated_count or 0,
                    "conflicts": r.conflict_count or 0,
                    "error": r.error_text or "",
                }
            )

    return {
        "total": total,
        "by_readiness": counts,
        "need_pdf": need_pdf,
        "stub_ratio": round(stub_ratio, 3),
        "processing": processing,
        "research_ready": counts.get("research_ready", 0),
        "sync": sync,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def find_duplicate_groups(
    db,
    UserFile,
    select_fn,
    user_id: int,
    *,
    project_id: int | None = None,
    limit_groups: int = 50,
) -> list[dict[str, Any]]:
    """Group papers by DOI, then title+year, then checksum."""
    stmt = select_fn(UserFile).where(
        UserFile.user_id == user_id,
        UserFile.kind == "document",
    )
    if project_id is not None:
        stmt = stmt.where(UserFile.project_id == project_id)
    files = db.execute(stmt).scalars().all()

    by_doi: dict[str, list] = defaultdict(list)
    by_ty: dict[str, list] = defaultdict(list)
    by_checksum: dict[str, list] = defaultdict(list)

    for f in files:
        doi = normalize_doi(getattr(f, "doi", "") or "")
        if doi:
            by_doi[doi.lower()].append(f)
        ty = title_year_key(getattr(f, "title", "") or "", getattr(f, "year", "") or "")
        if ty:
            by_ty[ty].append(f)
        cs = (getattr(f, "checksum_sha256", None) or "").strip()
        if cs:
            by_checksum[cs].append(f)

    seen_ids: set[int] = set()
    groups: list[dict[str, Any]] = []

    def _add_group(reason: str, key: str, members: list):
        if len(members) < 2:
            return
        ids = {m.id for m in members}
        if ids & seen_ids and reason != "checksum":
            # Prefer DOI groups; skip overlapping title groups later
            if reason == "title_year" and ids.issubset(seen_ids):
                return
        seen_ids.update(ids)
        # Prefer keep = has PDF, else earliest id
        ranked = sorted(
            members,
            key=lambda m: (
                0 if ((m.path or "").strip() or int(m.size or 0) > 0) else 1,
                m.id,
            ),
        )
        groups.append(
            {
                "reason": reason,
                "key": key[:200],
                "keep_id": ranked[0].id,
                "file_ids": [m.id for m in ranked],
                "titles": [(m.title or m.name or "")[:120] for m in ranked],
                "has_pdf": [
                    bool((m.path or "").strip() or int(m.size or 0) > 0) for m in ranked
                ],
            }
        )

    for doi, members in by_doi.items():
        _add_group("doi", doi, members)
    for ty, members in by_ty.items():
        _add_group("title_year", ty, members)
    for cs, members in by_checksum.items():
        _add_group("checksum", cs, members)

    groups.sort(key=lambda g: (-len(g["file_ids"]), g["reason"]))
    return groups[:limit_groups]


def merge_duplicate_files(
    db,
    UserFile,
    user_id: int,
    *,
    keep_id: int,
    merge_ids: list[int],
    delete_merged: bool = True,
) -> dict[str, Any]:
    """Merge bibliographic empties into keep; optionally delete losers.

    Never deletes the keep row. Never clears PDF/path on keep.
    """
    keep = db.get(UserFile, keep_id)
    if not keep or keep.user_id != user_id:
        return {"error": "keep_not_found"}

    merged: list[int] = []
    skipped: list[dict] = []
    for mid in merge_ids:
        if mid == keep_id:
            continue
        other = db.get(UserFile, mid)
        if not other or other.user_id != user_id:
            skipped.append({"id": mid, "reason": "not_found"})
            continue
        rec = LibraryRecord(
            title=other.title or "",
            authors=other.authors or "",
            year=other.year or "",
            venue=other.venue or "",
            doi=other.doi or "",
            abstract=other.abstract or "",
            url=getattr(other, "source_url", "") or "",
            source=getattr(other, "metadata_source", "") or "library",
            external_id=getattr(other, "external_item_id", "") or "",
        )
        protect = bool((keep.path or "").strip() or int(keep.size or 0) > 0)
        merge_metadata_into_existing(keep, rec, protect_asset=protect)
        # Prefer other's PDF if keep has none
        if not ((keep.path or "").strip() or int(keep.size or 0) > 0):
            if (other.path or "").strip() or int(other.size or 0) > 0:
                keep.path = other.path
                keep.size = other.size
                keep.mime = other.mime or keep.mime
                keep.checksum_sha256 = getattr(other, "checksum_sha256", None) or keep.checksum_sha256
                keep.meta_status = other.meta_status or keep.meta_status
                other.path = ""
                other.size = 0

        if delete_merged:
            # Clear path so storage GC isn't surprised; leave storage key orphan
            # only if we moved it to keep above.
            db.delete(other)
        merged.append(mid)

    db.commit()
    return {
        "ok": True,
        "keep_id": keep_id,
        "merged_ids": merged,
        "skipped": skipped,
    }
