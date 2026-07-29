"""Literature Review Markdown export (Sprint C).

Body + Evidence Appendix + Bibliography + Generation metadata.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:.0f}%"
    except (TypeError, ValueError):
        return "n/a"


def _bindings_from_writing(writing: dict[str, Any]) -> list[dict[str, Any]]:
    bib = list(writing.get("bibliography") or [])
    if bib:
        return bib
    flat: list[dict[str, Any]] = []
    seen: set[int] = set()
    for sec in writing.get("sections") or []:
        for b in sec.get("bindings") or []:
            eid = b.get("evidence_id")
            if eid is None or int(eid) in seen:
                continue
            seen.add(int(eid))
            flat.append(b)
    if flat:
        return flat
    for c in writing.get("citations") or []:
        eid = c.get("evidence_id")
        if eid is None or int(eid) in seen:
            continue
        seen.add(int(eid))
        flat.append(c)
    return flat


def compute_export_traceability(writing: dict[str, Any]) -> dict[str, Any]:
    """Every ok section must have ≥1 EvidenceObject binding (100% target)."""
    sections = [
        s
        for s in (writing.get("sections") or [])
        if s.get("status") == "ok" and (s.get("paragraph") or "").strip()
    ]
    if not sections and (writing.get("paragraph") or "").strip():
        # Flat paragraph path
        n_bind = len(_bindings_from_writing(writing))
        ok = n_bind >= 1
        return {
            "paragraph_count": 1,
            "paragraphs_with_evidence": 1 if ok else 0,
            "traceability_pct": 1.0 if ok else 0.0,
            "meets_100": ok,
        }
    linked = sum(
        1
        for s in sections
        if (s.get("bindings") or s.get("evidence_ids") or [])
        and not (s.get("orphan_ids") or [])
    )
    total = len(sections)
    pct = round(linked / total, 4) if total else 0.0
    return {
        "paragraph_count": total,
        "paragraphs_with_evidence": linked,
        "traceability_pct": pct,
        "meets_100": total > 0 and linked == total,
    }


def build_literature_review_markdown(
    *,
    title: str,
    body: str,
    writing: dict[str, Any] | None = None,
    writing_version: str | None = None,
    exported_at: str | None = None,
) -> str:
    """Assemble export Markdown for the Evidence-backed Lit Review draft."""
    writing = writing or {}
    when = exported_at or datetime.now(timezone.utc).isoformat()
    bindings = _bindings_from_writing(writing)
    trace = compute_export_traceability(writing)
    metrics = writing.get("metrics") or {}
    review = writing.get("review") or {}
    review_metrics = review.get("metrics") or {}

    lines: list[str] = [
        f"# {(title or 'Literature review').strip()}",
        "",
        "## Literature review",
        "",
        (body or "").strip() or "_No draft body._",
        "",
        "## Evidence appendix",
        "",
    ]

    if not bindings:
        lines.append("_No EvidenceObject bindings available for this export._")
        lines.append("")
    else:
        for b in bindings:
            eid = b.get("evidence_id")
            page = b.get("page")
            claim = (b.get("claim") or "").strip()
            quote = (b.get("quote") or "").strip()
            band = b.get("confidence_band") or ""
            study = b.get("study_type") or ""
            lines.append(f"### Evidence #{eid}")
            meta_bits = []
            if page is not None:
                meta_bits.append(f"page {page}")
            if band:
                meta_bits.append(str(band))
            if study:
                meta_bits.append(str(study))
            if meta_bits:
                lines.append(f"- Provenance: {', '.join(meta_bits)}")
            if claim:
                lines.append(f"- Claim: {claim}")
            if quote:
                lines.append(f"- Quote: “{quote}”")
            lines.append("")

    lines.extend(["## Bibliography", ""])
    if not bindings:
        lines.append("_Empty bibliography._")
        lines.append("")
    else:
        for i, b in enumerate(bindings, start=1):
            eid = b.get("evidence_id")
            page = b.get("page")
            claim = (b.get("claim") or "").strip() or "(no claim text)"
            page_bit = f", page {page}" if page is not None else ""
            lines.append(f"{i}. [#{eid}] {claim}{page_bit}")
        lines.append("")

    lines.extend(
        [
            "## Generation metadata",
            "",
            f"- exported_at: {when}",
            f"- writing_version: {writing_version or writing.get('writing_version') or 'unknown'}",
            f"- mode: {writing.get('mode') or 'unknown'}",
            f"- section_type: {writing.get('section_type') or 'unknown'}",
            f"- status: {writing.get('status') or 'unknown'}",
            f"- grounding_pct: {_pct(metrics.get('grounding_pct', review_metrics.get('grounding_pct')))}",
            f"- citation_coverage: {_pct(metrics.get('citation_coverage', review_metrics.get('citation_coverage_pct')))}",
            f"- unsupported_claims: {metrics.get('unsupported_claims', review_metrics.get('unsupported_claims', 'n/a'))}",
            f"- research_reviewer: {review.get('status') or 'n/a'} (pass_rate={_pct(review.get('pass_rate'))})",
            f"- evidence_traceability_pct: {_pct(trace['traceability_pct'])}",
            f"- evidence_traceability_100: {'yes' if trace['meets_100'] else 'no'}",
            f"- unique_evidence_cited: {metrics.get('unique_evidence_cited', len(bindings))}",
            f"- disclaimer: {(writing.get('disclaimer') or '').strip()}",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"
