"""Citation Binder — resolve ``[#id]`` markers to EvidenceObject bindings.

Sprint B: stable marker order, orphan detection, every ok paragraph grounded.
V1: claim/sentence alignment — drop or rebind markers that do not overlap the cited claim.
"""

from __future__ import annotations

import re
from typing import Any

MARKER_RE = re.compile(r"\[#(\d+)\]")
BINDER_VERSION = "1.2.0"
_SENTENCE_SPLIT = re.compile(
    r"(?<!\bp)(?<!Mr)(?<!Mrs)(?<!Ms)(?<!Dr)(?<!vs)(?<=[.!?])\s+(?=[A-Z“\"(\\[*])"
)
_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")


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
        "paper_title": cite.get("paper_title")
        or cite.get("file_title")
        or obj.get("file_title")
        or "",
        "authors": cite.get("authors") or obj.get("authors") or "",
        "year": cite.get("year") or obj.get("year") or "",
        "venue": cite.get("venue") or obj.get("venue") or "",
        "doi": cite.get("doi") or obj.get("doi") or "",
    }


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or "").lower()))


def _claim_text(obj: dict[str, Any] | None) -> str:
    if not obj:
        return ""
    return (obj.get("claim") or obj.get("quote") or "").strip()


def _overlap_score(sentence: str, claim: str) -> float:
    st = _tokens(MARKER_RE.sub(" ", sentence))
    ct = _tokens(claim)
    if not st or not ct:
        # Too little claim text to judge — treat as aligned if id exists.
        return 1.0 if claim.strip() and len(claim.strip()) < 12 else 0.0
    return len(st & ct) / float(len(ct))


def _best_align_id(
    sentence: str,
    *,
    candidates: list[int],
    by_id: dict[int, dict[str, Any]],
    min_score: float = 0.15,
) -> int | None:
    best_id: int | None = None
    best_score = 0.0
    for eid in candidates:
        score = _overlap_score(sentence, _claim_text(by_id.get(eid)))
        if score > best_score:
            best_score = score
            best_id = eid
    if best_id is None or best_score < min_score:
        return None
    return best_id


def align_paragraph_markers(
    paragraph: str,
    *,
    by_id: dict[int, dict[str, Any]],
    candidate_ids: list[int],
) -> tuple[str, list[str]]:
    """Rebind or strip ``[#id]`` markers that do not overlap the cited claim.

    Prefer rebinding to the best-overlap candidate among ``candidate_ids``.
    Returns (cleaned_paragraph, warnings).
    """
    warnings: list[str] = []
    if not (paragraph or "").strip() or not candidate_ids:
        return paragraph or "", warnings

    chunks: list[str] = []
    for block in paragraph.split("\n"):
        if not block.strip():
            chunks.append(block)
            continue
        parts = [p for p in _SENTENCE_SPLIT.split(block) if p is not None]
        rebuilt: list[str] = []
        for sentence in parts:
            markers = [int(m.group(1)) for m in MARKER_RE.finditer(sentence)]
            if not markers:
                rebuilt.append(sentence)
                continue
            new_sentence = sentence
            for eid in markers:
                claim = _claim_text(by_id.get(eid)) if eid in by_id else ""
                score = _overlap_score(sentence, claim) if claim else 0.0
                if eid in by_id and score >= 0.15:
                    continue
                if eid not in by_id:
                    # Keep unknown markers so orphan detection / Reviewer can fail-closed.
                    continue
                alt = _best_align_id(sentence, candidates=candidate_ids, by_id=by_id)
                if alt is not None and alt != eid:
                    new_sentence = re.sub(rf"\[#{eid}\]", f"[#{alt}]", new_sentence, count=1)
                    warnings.append(f"Rebound citation [#{eid}] → [#{alt}] (claim alignment).")
                else:
                    new_sentence = re.sub(rf"\s*\[#{eid}\]", "", new_sentence, count=1)
                    warnings.append(
                        f"Removed misaligned citation [#{eid}] (no overlapping claim)."
                    )
            rebuilt.append(new_sentence)
        # Preserve single-space joins between split sentences.
        joined = rebuilt[0] if rebuilt else ""
        for part in rebuilt[1:]:
            if joined and not joined.endswith((" ", "\n")) and part and not part.startswith(" "):
                joined = f"{joined} {part}"
            else:
                joined = f"{joined}{part}"
        chunks.append(joined)
    return "\n".join(chunks), warnings


def bind_citations_to_sections(
    *,
    sections: list[dict[str, Any]],
    objects: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Enrich sections with stable citation bindings from markers + citations.

    Does not invent EvidenceObjects. Unknown ``[#id]`` markers become orphans.
    Misaligned markers are rebound or stripped before binding (V1 quality loop).
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

        declared_ids = [int(x) for x in (sec.get("evidence_ids") or [])]
        citation_ids = [
            int(c["evidence_id"])
            for c in citations
            if c.get("evidence_id") is not None
        ]
        candidate_ids = []
        seen_c: set[int] = set()
        for eid in declared_ids + citation_ids + list(by_id.keys()):
            if eid in seen_c or eid not in by_id:
                continue
            seen_c.add(eid)
            candidate_ids.append(eid)

        paragraph = sec.get("paragraph") or ""
        aligned_para, align_warnings = align_paragraph_markers(
            paragraph, by_id=by_id, candidate_ids=candidate_ids
        )

        marker_ids = parse_marker_ids(aligned_para)

        # Stable order: markers first (prose order). After alignment, do not re-attach
        # declared ids that were rebound away from the paragraph.
        ordered_ids: list[int] = []
        seen: set[int] = set()
        for eid in marker_ids:
            if eid in seen:
                continue
            seen.add(eid)
            ordered_ids.append(eid)
        if not marker_ids:
            for eid in citation_ids + declared_ids:
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
        enriched["paragraph"] = aligned_para
        enriched["evidence_ids"] = resolvable
        enriched["marker_ids"] = marker_ids
        enriched["orphan_ids"] = orphan_ids
        enriched["bindings"] = bindings
        enriched["binding_count"] = len(bindings)
        enriched["citations"] = ordered_citations
        enriched["binder_version"] = BINDER_VERSION
        warnings = list(sec.get("warnings") or []) + align_warnings
        if orphan_ids:
            warnings.append(
                f"Orphan citation markers (no EvidenceObject): {', '.join(f'#{i}' for i in orphan_ids)}"
            )
        if warnings:
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
