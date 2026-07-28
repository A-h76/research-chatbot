"""Evidence Retrieval stage (Phase 2.3 Sprint 1).

Computes over Evidence Layer objects only — never invents objects or reads PDFs.
Accepts a normalized EvidenceQuery; returns EvidenceObject projections.
"""

from __future__ import annotations

import re
from typing import Any

from backend.evidence.objects import serialize_evidence_object

_TOKEN_RE = re.compile(r"[a-z0-9]{2,}", re.I)


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


def _match_score(row: Any, *, query_text: str, selected_text: str) -> float:
    """Simple lexical overlap — Retrieval implementation detail, not embeddings."""
    needle = _tokens(query_text) | _tokens(selected_text)
    if not needle:
        return 0.0
    hay = _tokens(getattr(row, "claim", "") or "") | _tokens(getattr(row, "quote", "") or "")
    if not hay:
        return 0.0
    overlap = len(needle & hay)
    return overlap / max(len(needle), 1)


def retrieve_evidence_objects(
    db,
    *,
    query: dict[str, Any],
    EvidenceObject: Any,
    WritingSentenceBinding: Any | None = None,
    select: Any,
    fetch_multiplier: int = 5,
) -> dict[str, Any]:
    """Run Retrieval stage for a normalized EvidenceQuery.

    Does not invent EvidenceObjects. Does not apply Ranking stage semantics
    beyond provisional retrieval relevance (binding hit + lexical overlap).
    `ranking_strategy` is echoed for the Ranking stage to consume later.
    """
    scope = query["scope"]
    filters = query["filters"]
    limit = int(query["result_limit"])
    user_id = int(scope["user_id"])
    project_id = int(scope["project_id"])

    stmt = select(EvidenceObject).where(
        EvidenceObject.user_id == user_id,
        EvidenceObject.project_id == project_id,
        EvidenceObject.status.in_(tuple(filters["status"])),
        EvidenceObject.confidence_band.in_(tuple(filters["confidence_bands"])),
    )

    file_ids = scope.get("file_ids")
    if file_ids:
        stmt = stmt.where(EvidenceObject.file_id.in_(list(file_ids)))

    study_types = [s for s in (filters.get("study_types") or []) if s]
    if study_types:
        stmt = stmt.where(EvidenceObject.study_type.in_(tuple(study_types)))

    if filters.get("require_page_anchor", True):
        stmt = stmt.where(EvidenceObject.page.isnot(None))
        stmt = stmt.where(EvidenceObject.quote.isnot(None))
        stmt = stmt.where(EvidenceObject.quote != "")

    # Fetch a wider window so lexical / binding preference can reorder
    fetch_n = max(limit * fetch_multiplier, limit)
    rows = list(db.execute(stmt.order_by(EvidenceObject.updated_at.desc()).limit(fetch_n)).scalars().all())

    # Prefer objects already bound to document/block when anchors present
    preferred_ids: set[int] = set()
    document_id = scope.get("document_id")
    block_id = (query.get("anchors") or {}).get("block_id") or ""
    if WritingSentenceBinding is not None and document_id is not None:
        bstmt = select(WritingSentenceBinding).where(
            WritingSentenceBinding.user_id == user_id,
            WritingSentenceBinding.project_id == project_id,
            WritingSentenceBinding.document_id == int(document_id),
        )
        if block_id:
            bstmt = bstmt.where(WritingSentenceBinding.block_id == block_id)
        bindings = db.execute(bstmt).scalars().all()
        preferred_ids = {int(b.evidence_object_id) for b in bindings}

    query_text = query.get("query_text") or ""
    selected = (query.get("anchors") or {}).get("selected_text") or ""

    scored: list[tuple[float, Any]] = []
    for row in rows:
        score = _match_score(row, query_text=query_text, selected_text=selected)
        if int(row.id) in preferred_ids:
            score += 10.0
        # list_project / empty query: keep chronological via zero score + updated_at order
        scored.append((score, row))

    # If query has text, drop zero-overlap unless list_project or preferred binding
    intent = query.get("intent") or ""
    has_text = bool(_tokens(query_text) or _tokens(selected))
    if has_text and intent != "list_project":
        filtered = [(s, r) for s, r in scored if s > 0]
        if filtered:
            scored = filtered

    scored.sort(key=lambda pair: (pair[0], getattr(pair[1], "updated_at", None) or 0), reverse=True)
    total = len(scored)
    truncated = total > limit
    chosen = [r for _, r in scored[:limit]]

    return {
        "query": query,
        "objects": [serialize_evidence_object(r) for r in chosen],
        "total": total,
        "truncated": truncated,
        "stage": "retrieval",
        "retrieval_version": "1.0.0",
    }
