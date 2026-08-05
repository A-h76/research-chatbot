"""Unified research retrieval spine (W2).

Prefer this over ad-hoc ``rag_retrieve`` call sites. Chat and (later) writing
skills should share the same PassageHit shape.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Optional

from backend.search.shared import cosine_similarity, keyword_score

from .scope import ResearchScope


@dataclass(frozen=True)
class PassageHit:
    file_id: int
    file_name: str
    content: str
    score: float
    chunk_id: Optional[int] = None
    page: Optional[int] = None
    section: Optional[str] = None
    evidence_id: Optional[int] = None

    def to_prompt_dict(self) -> dict[str, Any]:
        """Compact shape injected into the model prompt (cite-friendly)."""
        entry: dict[str, Any] = {
            "file": self.file_name,
            "file_id": self.file_id,
            "content": self.content[:2000],
        }
        if self.chunk_id is not None:
            entry["chunk_id"] = self.chunk_id
        if self.page is not None:
            entry["page"] = self.page
        if self.section:
            entry["section"] = self.section
        if self.evidence_id is not None:
            entry["evidence_id"] = self.evidence_id
        return entry


EmbedFn = Callable[..., list[Optional[list[float]]]]


def research_retrieve(
    db: Any,
    *,
    UserFile: Any,
    Chunk: Any,
    select: Any,
    scope: ResearchScope,
    query: str,
    embed_texts: EmbedFn,
    top_k: int = 6,
    LibraryCollectionPaper: Any = None,
    EvidenceObject: Any = None,
) -> list[PassageHit]:
    """Retrieve top passages for ``scope`` + ``query``.

    Scoping rules:
    - paper: hard-scoped to ``scope.file_id``
    - collection: membership rows when ``LibraryCollectionPaper`` is provided
    - project / conversation: files owned by user matching project or conversation
    - library: all user documents (explicit mode only)
    """
    files = _resolve_files(
        db,
        UserFile=UserFile,
        select=select,
        scope=scope,
        LibraryCollectionPaper=LibraryCollectionPaper,
    )
    if not files:
        return []

    file_map = {f.id: f for f in files}
    chunks = db.execute(select(Chunk).where(Chunk.file_id.in_(file_map.keys()))).scalars().all()
    if not chunks:
        return []

    q_emb: Optional[list[float]] = None
    try:
        emb_list = embed_texts([query[:500]], scope.user_id)
        if emb_list and emb_list[0]:
            q_emb = emb_list[0]
    except Exception:
        q_emb = None

    scored: list[tuple[float, Any]] = []
    for c in chunks:
        if q_emb and c.embedding:
            try:
                s = cosine_similarity(q_emb, json.loads(c.embedding))
            except Exception:
                s = keyword_score(query, c.content or "")
        else:
            s = keyword_score(query, c.content or "")
        scored.append((s, c))

    scored.sort(key=lambda x: -x[0])
    hits: list[PassageHit] = []
    for s, c in scored[:top_k]:
        if s <= 0:
            continue
        f = file_map.get(c.file_id)
        if not f:
            continue
        hits.append(
            PassageHit(
                file_id=c.file_id,
                file_name=getattr(f, "name", None) or "file",
                chunk_id=getattr(c, "id", None),
                content=(c.content or "")[:2000],
                score=float(s),
                page=getattr(c, "page", None),
                section=getattr(c, "section", None) or None,
            )
        )

    if EvidenceObject is not None and hits:
        hits = _attach_evidence_ids(db, EvidenceObject=EvidenceObject, select=select, hits=hits)
    return hits


def _resolve_files(
    db: Any,
    *,
    UserFile: Any,
    select: Any,
    scope: ResearchScope,
    LibraryCollectionPaper: Any,
) -> list[Any]:
    if scope.file_id is not None:
        row = (
            db.execute(
                select(UserFile).where(
                    UserFile.id == scope.file_id,
                    UserFile.user_id == scope.user_id,
                )
            )
            .scalars()
            .first()
        )
        return [row] if row else []

    if scope.collection_id is not None and LibraryCollectionPaper is not None:
        member_ids = (
            db.execute(
                select(LibraryCollectionPaper.file_id).where(
                    LibraryCollectionPaper.collection_id == scope.collection_id
                )
            )
            .scalars()
            .all()
        )
        if not member_ids:
            return []
        return (
            db.execute(
                select(UserFile).where(
                    UserFile.user_id == scope.user_id,
                    UserFile.id.in_(member_ids),
                )
            )
            .scalars()
            .all()
        )

    files = db.execute(select(UserFile).where(UserFile.user_id == scope.user_id)).scalars().all()
    if scope.mode == "library":
        return list(files)

    out = []
    for f in files:
        if scope.conversation_id and getattr(f, "conversation_id", None) == scope.conversation_id:
            out.append(f)
        elif scope.project_id and getattr(f, "project_id", None) == scope.project_id:
            out.append(f)
    return out


def _attach_evidence_ids(
    db: Any,
    *,
    EvidenceObject: Any,
    select: Any,
    hits: list[PassageHit],
) -> list[PassageHit]:
    """Best-effort: bind an EvidenceObject id when file+page match (EO-first hint)."""
    file_ids = {h.file_id for h in hits}
    try:
        rows = (
            db.execute(select(EvidenceObject).where(EvidenceObject.file_id.in_(file_ids)))
            .scalars()
            .all()
        )
    except Exception:
        return hits

    by_file_page: dict[tuple[int, Optional[int]], int] = {}
    for eo in rows:
        key = (getattr(eo, "file_id", None), getattr(eo, "page", None))
        if key[0] is None:
            continue
        eid = getattr(eo, "id", None)
        if eid is not None and key not in by_file_page:
            by_file_page[key] = eid

    enriched: list[PassageHit] = []
    for h in hits:
        eid = by_file_page.get((h.file_id, h.page))
        if eid is None:
            enriched.append(h)
        else:
            enriched.append(
                PassageHit(
                    file_id=h.file_id,
                    file_name=h.file_name,
                    content=h.content,
                    score=h.score,
                    chunk_id=h.chunk_id,
                    page=h.page,
                    section=h.section,
                    evidence_id=eid,
                )
            )
    return enriched
