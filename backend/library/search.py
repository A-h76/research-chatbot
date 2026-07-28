"""SQL-backed library search & filters (Phase 1.5).

Portable across SQLite (dev) and Postgres (prod). Never ``import server``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import case, func, or_, select

from .normalize import normalize_doi

# Field-prefix syntax: doi:10.1234 author:smith title:foo year:2024 venue:nature tag:ml
_FIELD_RE = re.compile(
    r"(doi|author|authors|title|year|venue|journal|tag):(\S+)",
    re.IGNORECASE,
)


@dataclass
class LibrarySearchParams:
    user_id: int
    project_id: int | None = None  # None = all; 0 = unassigned only
    collection_id: int | None = None
    kind: str | None = None
    reading_status: str | None = None
    meta_status: str | None = None
    tags: list[str] = field(default_factory=list)
    q: str | None = None
    title: str | None = None
    author: str | None = None
    doi: str | None = None
    year: str | None = None
    year_from: str | None = None
    year_to: str | None = None
    venue: str | None = None
    import_source: str | None = None  # zotero|bibtex|ris|discover|upload|openalex
    recent_days: int | None = None
    sort: str = "recent"
    order: str | None = None
    limit: int = 50
    offset: int = 0
    # Pre-resolved when filtering by collection (avoids circular model deps)
    file_ids: list[int] | None = None


def parse_field_query(raw: str | None) -> tuple[str, dict[str, str]]:
    """Extract field:token pairs from q; return remainder + fields dict."""
    if not raw:
        return "", {}
    fields: dict[str, str] = {}
    remainder_parts: list[str] = []

    for token in raw.split():
        m = _FIELD_RE.match(token)
        if m:
            key = m.group(1).lower()
            if key == "authors":
                key = "author"
            if key == "journal":
                key = "venue"
            fields[key] = m.group(2)
        else:
            remainder_parts.append(token)

    return " ".join(remainder_parts).strip(), fields


def params_from_request(args, user_id: int) -> LibrarySearchParams:
    """Build LibrarySearchParams from Flask request.args."""
    q_raw = (args.get("q") or "").strip() or None
    remainder, parsed = parse_field_query(q_raw)

    def _int(name, default=None):
        v = args.get(name)
        if v in (None, ""):
            return default
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    project_id_raw = args.get("project_id")
    project_id = None
    if project_id_raw is not None and project_id_raw != "":
        try:
            project_id = int(project_id_raw)
        except (TypeError, ValueError):
            project_id = None

    tags = [t for t in args.getlist("tag") if t]
    if parsed.get("tag") and parsed["tag"] not in tags:
        tags.append(parsed["tag"])
    sort = (args.get("sort") or "recent").strip().lower()
    order = (args.get("order") or "").strip().lower() or None

    return LibrarySearchParams(
        user_id=user_id,
        project_id=project_id,
        collection_id=_int("collection_id"),
        kind=(args.get("kind") or "").strip().lower() or None,
        reading_status=(args.get("reading_status") or "").strip().lower() or None,
        meta_status=(args.get("meta_status") or "").strip().lower() or None,
        tags=tags,
        q=remainder or None,
        title=(args.get("title") or parsed.get("title") or "").strip() or None,
        author=(args.get("author") or parsed.get("author") or "").strip() or None,
        doi=normalize_doi(args.get("doi") or parsed.get("doi") or "") or None,
        year=(args.get("year") or parsed.get("year") or "").strip()[:10] or None,
        year_from=(args.get("year_from") or "").strip()[:10] or None,
        year_to=(args.get("year_to") or "").strip()[:10] or None,
        venue=(args.get("venue") or args.get("journal") or parsed.get("venue") or "").strip() or None,
        import_source=(args.get("import_source") or args.get("source") or "").strip().lower() or None,
        recent_days=_int("recent_days"),
        sort=sort,
        order=order,
        limit=max(1, min(500, _int("limit", 50) or 50)),
        offset=max(0, _int("offset", 0) or 0),
    )


def _ilike(col, needle: str):
    pattern = f"%{needle.strip()}%"
    return col.ilike(pattern)


def _tag_contains(UserFile, tag: str):
    """JSON tags Text column — match quoted tag token."""
    safe = tag.replace('"', "")
    return UserFile.tags.contains(f'"{safe}"')


def _apply_import_source(UserFile, source: str):
    source = source.lower()
    if source == "upload":
        return or_(UserFile.path != "", UserFile.size > 0)
    meta_map = {
        "zotero": "zotero",
        "bibtex": "bibtex",
        "ris": "ris",
        "discover": "openalex",
        "openalex": "openalex",
        "mendeley": "mendeley",
    }
    tag_map = {
        "zotero": "from-zotero",
        "bibtex": "from-bibtex",
        "ris": "from-ris",
        "discover": "from-discover",
        "mendeley": "from-mendeley",
    }
    clauses = []
    if source in meta_map:
        clauses.append(UserFile.metadata_source == meta_map[source])
    if source in tag_map:
        clauses.append(_tag_contains(UserFile, tag_map[source]))
    if source == "import":
        clauses.append(
            or_(
                UserFile.metadata_source.in_(("bibtex", "ris", "zotero", "mendeley", "openalex")),
                UserFile.tags.contains("from-"),
            )
        )
    if not clauses:
        return None
    return or_(*clauses)


def build_filtered_query(UserFile, params: LibrarySearchParams):
    """Return (count_stmt, page_stmt) SQLAlchemy selects."""
    base = select(UserFile).where(UserFile.user_id == params.user_id)

    if params.file_ids is not None:
        if not params.file_ids:
            # Empty collection → no matches
            base = base.where(UserFile.id == -1)
        else:
            base = base.where(UserFile.id.in_(params.file_ids))

    if params.project_id is not None:
        if params.project_id == 0:
            base = base.where(UserFile.project_id.is_(None))
        else:
            base = base.where(UserFile.project_id == params.project_id)

    if params.kind in ("document", "image"):
        base = base.where(UserFile.kind == params.kind)

    if params.reading_status in ("unread", "reading", "read"):
        base = base.where(UserFile.reading_status == params.reading_status)

    if params.meta_status in ("pending", "running", "done", "failed"):
        base = base.where(UserFile.meta_status == params.meta_status)

    for tag in params.tags:
        base = base.where(_tag_contains(UserFile, tag))

    if params.title:
        base = base.where(_ilike(UserFile.title, params.title))

    if params.author:
        base = base.where(_ilike(UserFile.authors, params.author))

    if params.doi:
        base = base.where(_ilike(UserFile.doi, params.doi))

    if params.venue:
        base = base.where(_ilike(UserFile.venue, params.venue))

    if params.year:
        base = base.where(UserFile.year == params.year)

    if params.year_from:
        base = base.where(UserFile.year >= params.year_from)
    if params.year_to:
        base = base.where(UserFile.year <= params.year_to)

    if params.import_source:
        clause = _apply_import_source(UserFile, params.import_source)
        if clause is not None:
            base = base.where(clause)

    if params.recent_days and params.recent_days > 0:
        since = datetime.now(timezone.utc) - timedelta(days=params.recent_days)
        # SQLite stores naive UTC from ORM defaults
        since_cmp = since.replace(tzinfo=None)
        base = base.where(UserFile.created_at >= since_cmp)

    if params.q:
        words = params.q.split()
        for word in words:
            pattern = f"%{word.lower()}%"
            base = base.where(
                or_(
                    func.lower(UserFile.name).like(pattern),
                    func.lower(UserFile.title).like(pattern),
                    func.lower(UserFile.authors).like(pattern),
                    func.lower(UserFile.venue).like(pattern),
                    func.lower(UserFile.doi).like(pattern),
                    func.lower(UserFile.year).like(pattern),
                    func.lower(UserFile.tags).like(pattern),
                    func.lower(func.coalesce(UserFile.abstract, "")).like(pattern),
                )
            )

    sort = params.sort if params.sort in SORT_KEYS else "recent"
    order_col = SORT_KEYS[sort]
    reverse = (params.order == "desc") if params.order else sort in ("recent", "size")
    if reverse:
        base = base.order_by(order_col.desc())
    else:
        base = base.order_by(order_col.asc())

    count_stmt = select(func.count()).select_from(base.subquery())
    page_stmt = base.offset(params.offset).limit(params.limit)
    return count_stmt, page_stmt


# Sort column mapping — defined after UserFile is known at call site
SORT_KEYS: dict[str, Any] = {}


def init_sort_keys(UserFile):
    global SORT_KEYS
    SORT_KEYS = {
        "recent": UserFile.created_at,
        "title": func.lower(func.coalesce(UserFile.title, UserFile.name, "")),
        "authors": func.lower(func.coalesce(UserFile.authors, "")),
        "year": func.coalesce(UserFile.year, ""),
        "reading_status": case(
            (UserFile.reading_status == "reading", 0),
            (UserFile.reading_status == "unread", 1),
            else_=2,
        ),
        "size": UserFile.size,
    }


def search_library(db, UserFile, params: LibrarySearchParams) -> tuple[int, list]:
    """Execute search; return (total, rows)."""
    if not SORT_KEYS:
        init_sort_keys(UserFile)
    count_stmt, page_stmt = build_filtered_query(UserFile, params)
    total = db.execute(count_stmt).scalar() or 0
    rows = db.execute(page_stmt).scalars().all()
    return int(total), list(rows)


def facets_for_user(db, UserFile, user_id: int, *, project_id: int | None = None) -> dict:
    """Lightweight facet counts for filter UI."""
    base = select(UserFile).where(UserFile.user_id == user_id, UserFile.kind == "document")
    if project_id is not None and project_id != 0:
        base = base.where(UserFile.project_id == project_id)
    elif project_id == 0:
        base = base.where(UserFile.project_id.is_(None))

    files = db.execute(base).scalars().all()
    by_status = {"unread": 0, "reading": 0, "read": 0}
    by_source: dict[str, int] = {}
    years: dict[str, int] = {}

    for f in files:
        rs = f.reading_status or "unread"
        if rs in by_status:
            by_status[rs] += 1
        src = (getattr(f, "metadata_source", None) or "upload").lower()
        if f.path or (f.size or 0) > 0:
            src_key = "upload"
        elif src in ("bibtex", "ris", "zotero", "openalex"):
            src_key = src if src != "openalex" else "discover"
        else:
            src_key = src
        by_source[src_key] = by_source.get(src_key, 0) + 1
        y = (f.year or "").strip()[:4]
        if y.isdigit():
            years[y] = years.get(y, 0) + 1

    top_years = sorted(years.items(), key=lambda x: x[0], reverse=True)[:12]
    return {
        "reading_status": by_status,
        "import_source": by_source,
        "years": [{"year": y, "count": c} for y, c in top_years],
        "total": len(files),
    }
