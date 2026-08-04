"""Research readiness — derived Library Record → Research Asset ladder.

No new DB column: computed from path/size/meta_status/chunk_count.
"""

from __future__ import annotations

from typing import Any, Literal

ResearchReadiness = Literal[
    "metadata_only",
    "pdf_attached",
    "analysed",
    "indexed",
    "research_ready",
]

READINESS_ORDER: list[ResearchReadiness] = [
    "metadata_only",
    "pdf_attached",
    "analysed",
    "indexed",
    "research_ready",
]

READINESS_LABELS: dict[ResearchReadiness, str] = {
    # Soft UFTR language — machine state stays metadata_only
    "metadata_only": "Full text needed",
    "pdf_attached": "Analyzing",
    "analysed": "Evidence ready",
    "indexed": "Research ready",
    "research_ready": "Research ready",
}


def has_pdf(uf: Any) -> bool:
    path = (getattr(uf, "path", None) or "").strip()
    size = int(getattr(uf, "size", 0) or 0)
    return bool(path) or size > 0


def research_readiness(
    uf: Any,
    *,
    chunk_count: int | None = None,
) -> ResearchReadiness:
    """Derive readiness for a UserFile-like object.

    Rules:
    - No PDF → metadata_only (even if meta_status=done from stub import)
    - PDF + pending/running/failed → pdf_attached (in flight or needs retry)
    - PDF + meta done + no chunks → analysed
    - PDF + meta done + chunks → research_ready (indexed + RAG usable)
    """
    chunks = chunk_count
    if chunks is None:
        raw = getattr(uf, "chunks", None)
        if isinstance(raw, int):
            chunks = raw
        else:
            try:
                chunks = len(raw or [])
            except Exception:
                chunks = 0
    chunks = int(chunks or 0)

    if not has_pdf(uf):
        return "metadata_only"

    meta = (getattr(uf, "meta_status", None) or "").lower()
    if meta in {"pending", "running", "failed", ""}:
        return "pdf_attached"

    if chunks <= 0:
        return "analysed"

    # Chunks present ⇒ indexed + research-ready for Library OS v1
    return "research_ready"


def readiness_payload(uf: Any, *, chunk_count: int | None = None) -> dict[str, Any]:
    state = research_readiness(uf, chunk_count=chunk_count)
    return {
        "research_readiness": state,
        "research_readiness_label": READINESS_LABELS[state],
        "has_pdf": has_pdf(uf),
    }
