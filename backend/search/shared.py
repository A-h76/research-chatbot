"""Shared retrieval helpers for session and JWT search entry points."""

from __future__ import annotations

import json
import math
from typing import Any


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def keyword_score(query: str, text: str) -> float:
    words = query.lower().split()
    if not words:
        return 0.0
    t = (text or "").lower()
    return sum(1 for w in words if w in t) / len(words)


def search_user_document_chunks(
    db,
    *,
    UserFile: Any,
    Chunk: Any,
    select: Any,
    user_id: int,
    query_embedding: list[float] | None,
    query_text: str,
    project_id: int | None = None,
    file_id: int | None = None,
    limit: int = 20,
    min_score: float = 0.15,
    allow_keyword_fallback: bool = True,
) -> list[tuple[float, Any, Any]]:
    file_stmt = select(UserFile).where(UserFile.user_id == user_id, UserFile.kind == "document")
    if file_id is not None:
        file_stmt = file_stmt.where(UserFile.id == file_id)
    if project_id is not None:
        file_stmt = file_stmt.where(UserFile.project_id == project_id)
    files = db.execute(file_stmt).scalars().all()
    file_map = {f.id: f for f in files}
    if not file_map:
        return []

    chunks = db.execute(select(Chunk).where(Chunk.file_id.in_(file_map.keys()))).scalars().all()
    scored: list[tuple[float, Any, Any]] = []
    for ch in chunks:
        score = 0.0
        if query_embedding and ch.embedding:
            try:
                emb = json.loads(ch.embedding)
                score = cosine_similarity(query_embedding, emb)
            except Exception:
                score = keyword_score(query_text, ch.content) if allow_keyword_fallback else 0.0
        elif allow_keyword_fallback:
            score = keyword_score(query_text, ch.content)
        if score < min_score:
            continue
        scored.append((score, ch, file_map.get(ch.file_id)))

    scored.sort(key=lambda x: -x[0])
    return scored[:limit]
