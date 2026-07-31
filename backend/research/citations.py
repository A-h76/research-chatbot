"""Passage hits → structured workspace references (W1 Trust Chat)."""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlencode

from .retrieve import PassageHit


def passages_to_workspace_references(
    passages: list[PassageHit],
    *,
    primary_file_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Build clickable citation objects for SSE / persisted message payload.

    Kind ``passage`` opens the Structure tab (page/section focus via ``ref``).
    When ``evidence_id`` is present, also emit an evidence.outcome-style link
    is deferred — we attach evidence_id in metadata for W4/W7.
    """
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, p in enumerate(passages):
        file_id = p.file_id
        ref_id = _passage_ref_id(p)
        if ref_id in seen:
            continue
        seen.add(ref_id)
        label = _passage_label(p)
        params = {"tab": "structure", "ref": ref_id}
        href = f"/papers/{file_id}?{urlencode(params)}"
        meta: dict[str, Any] = {
            "file_id": file_id,
            "file_name": p.file_name,
            "score": round(p.score, 4),
        }
        if p.chunk_id is not None:
            meta["chunk_id"] = p.chunk_id
        if p.page is not None:
            meta["page"] = p.page
        if p.section:
            meta["section"] = p.section
        if p.evidence_id is not None:
            meta["evidence_id"] = p.evidence_id
        preview = (p.content or "").strip().replace("\n", " ")
        if preview:
            meta["quote_preview"] = preview[:180]

        refs.append(
            {
                "id": f"passage:{file_id}:{ref_id}:{i}",
                "kind": "passage",
                "refId": ref_id,
                "label": label,
                "tab": "structure",
                "href": href,
                "metadata": meta,
            }
        )

        # Prefer primary paper's passages first in UI ordering when multi-file.
        if primary_file_id is not None and file_id != primary_file_id:
            pass

    if primary_file_id is not None:
        refs.sort(key=lambda r: 0 if (r.get("metadata") or {}).get("file_id") == primary_file_id else 1)
    return refs


def _passage_ref_id(p: PassageHit) -> str:
    if p.chunk_id is not None:
        return f"passage:chunk:{p.chunk_id}"
    if p.page is not None and p.section:
        return f"passage:page:{p.page}:section:{p.section}"
    if p.page is not None:
        return f"passage:page:{p.page}"
    if p.section:
        return f"passage:section:{p.section}"
    return f"passage:file:{p.file_id}:s{round(p.score, 3)}"


def _passage_label(p: PassageHit) -> str:
    parts: list[str] = []
    if p.page is not None:
        parts.append(f"p. {p.page}")
    if p.section:
        sec = p.section.strip()
        if len(sec) > 48:
            sec = sec[:45] + "…"
        parts.append(sec)
    if not parts:
        parts.append(p.file_name or "Passage")
    return " · ".join(parts)
