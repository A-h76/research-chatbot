"""Citation Binder — resolve ``[#id]`` markers to EvidenceObject bindings.

Sprint B: stable marker order, orphan detection, every ok paragraph grounded.
"""

from __future__ import annotations

import re
from typing import Any

MARKER_RE = re.compile(r"\[#(\d+)\]")
BINDER_VERSION = "1.1.0"


def parse_marker_ids(text: str | None) -> list[int]:
    """Return unique evidence ids in first-appearance order."""
    ordered: list[int] = []
    seen: set[int] = set()
    for match in MARKER_RE.finditer(text or ""):
        eid = int(match.group(1))
        if eid in seen:
            continue
        seen.add(eid)
        ordered.append(eid)
    return ordered


def _binding_row(
    eid: int,
    *,
    cite: dict[str, Any] | None,
    obj: dict[str, Any] | None,
) -> dict[str, Any]:
    cite = cite or {}
    obj = obj or {}
    return {
        "evidence_id": eid,
        "file_id": cite.get("file_id") or obj.get("file_id"),
        "page": cite.get("page") if cite.get("page") is not None else obj.get("page"),
        "claim": (cite.get("claim") or obj.get("claim") or "")[:500],
        "quote": (cite.get("quote") or obj.get("quote") or "")[:500],
        "confidence_band": cite.get("confidence_band")
        or obj.get("confidence_band")
        or "low",
        "study_type": cite.get("study_type") or obj.get("study_type") or "",
    }


def bind_citations_to_sections(
    *,
    sections: list[dict[str, Any]],
    objects: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Enrich sections with stable citation bindings from markers + citations.

    Does not invent EvidenceObjects. Unknown ``[#id]`` markers become orphans.
    """
    by_id = {
        int(o["id"]): o
        for o in (objects or [])
        if o.get("id") is not None
    }
    out: list[dict[str, Any]] = []
    for sec in sections:
        citations = list(sec.get("citations") or [])
        cite_by_id = {
            int(c["evidence_id"]): c
            for c in citations
            if c.get("evidence_id") is not None
        }

        marker_ids = parse_marker_ids(sec.get("paragraph"))
        declared_ids = [int(x) for x in (sec.get("evidence_ids") or [])]
        citation_ids = [
            int(c["evidence_id"])
            for c in citations
            if c.get("evidence_id") is not None
        ]

        # Stable order: markers first (prose order), then remaining citations/declared.
        ordered_ids: list[int] = []
        seen: set[int] = set()
        for eid in marker_ids + citation_ids + declared_ids:
            if eid in seen:
                continue
            seen.add(eid)
            ordered_ids.append(eid)

        orphan_ids = [eid for eid in marker_ids if eid not in by_id]
        resolvable = [eid for eid in ordered_ids if eid in by_id]

        bindings: list[dict[str, Any]] = [
            _binding_row(eid, cite=cite_by_id.get(eid), obj=by_id.get(eid))
            for eid in resolvable
        ]

        # Keep citations aligned to binding order for downstream flatten/metrics.
        ordered_citations = [
            cite_by_id[eid] if eid in cite_by_id else _binding_row(eid, cite=None, obj=by_id.get(eid))
            for eid in resolvable
        ]

        enriched = dict(sec)
        enriched["evidence_ids"] = resolvable
        enriched["marker_ids"] = marker_ids
        enriched["orphan_ids"] = orphan_ids
        enriched["bindings"] = bindings
        enriched["binding_count"] = len(bindings)
        enriched["citations"] = ordered_citations
        enriched["binder_version"] = BINDER_VERSION
        if orphan_ids:
            warnings = list(sec.get("warnings") or [])
            warnings.append(
                f"Orphan citation markers (no EvidenceObject): {', '.join(f'#{i}' for i in orphan_ids)}"
            )
            enriched["warnings"] = warnings
        out.append(enriched)
    return out


def flatten_bindings(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduped bibliography-style list across sections (stable first-seen order)."""
    flat: list[dict[str, Any]] = []
    seen: set[int] = set()
    for sec in sections:
        for b in sec.get("bindings") or []:
            eid = b.get("evidence_id")
            if eid is None or int(eid) in seen:
                continue
            seen.add(int(eid))
            flat.append(b)
    return flat
