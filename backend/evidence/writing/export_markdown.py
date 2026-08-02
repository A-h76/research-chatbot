"""Literature Review Markdown + BibTeX export (Sprint C / V1 #18).

Body + Evidence Appendix + Bibliography + Generation metadata.
Server-side export gate mirrors FE ``canExportGroundedLitReview``.
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


def review_has_severity_error(review: dict[str, Any] | None) -> bool:
    if not review:
        return False
    return any(
        str(i.get("severity") or "").lower() == "error"
        for i in (review.get("issues") or [])
    )


def can_export_grounded_lit_review(
    writing: dict[str, Any] | None,
) -> tuple[bool, str | None]:
    """Refuse lit-review export when grounding / Reviewer bar is not met (#18)."""
    if not writing:
        return False, "No grounded export payload — generate and accept a review first"
    if writing.get("status") == "blocked":
        return False, "Draft is blocked — insufficient evidence"
    if writing.get("accept_allowed") is False:
        return (
            False,
            "Research Reviewer blocked Accept/export — revise unbound or unsupported claims",
        )
    review = writing.get("review") or {}
    if review_has_severity_error(review):
        return False, "Research Reviewer has error-severity findings — fix before export"
    if review.get("status") == "fail":
        return False, "Research Reviewer failed — fix issues before export"
    trace = compute_export_traceability(writing)
    if not trace["meets_100"]:
        return False, "Evidence traceability below 100% — every section needs bindings"
    return True, None


def compute_export_traceability(writing: dict[str, Any]) -> dict[str, Any]:
    """Every ok section must have ≥1 EvidenceObject binding (100% target)."""
    sections = [
        s
        for s in (writing.get("sections") or [])
        if s.get("status") == "ok" and (s.get("paragraph") or "").strip()
    ]
    if not sections and (writing.get("paragraph") or "").strip():
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


def _bibliography_line(i: int, b: dict[str, Any]) -> str:
    """Prefer paper metadata when present (FE parity); else claim + page."""
    eid = b.get("evidence_id")
    page = b.get("page")
    title = str(b.get("paper_title") or "").strip()
    authors = str(b.get("authors") or "").strip()
    year = str(b.get("year") or "").strip()
    venue = str(b.get("venue") or "").strip()
    doi = str(b.get("doi") or "").strip()
    claim = str(b.get("claim") or "").strip()
    page_bit = f" (p. {page})" if page is not None else ""
    if title or authors:
        bits = [
            authors or None,
            f"({year})" if year else None,
            title or None,
            venue or None,
            f"https://doi.org/{doi}" if doi else None,
            f"[#{eid}]{page_bit}",
        ]
        return f"{i}. {'. '.join(x for x in bits if x)}"
    claim_bit = claim or "(no claim text)"
    return f"{i}. [#{eid}] {claim_bit}{page_bit}"


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
            lines.append(_bibliography_line(i, b))
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
            f"- reviewer_version: {review.get('reviewer_version') or 'n/a'}",
            f"- reviewer_issue_count: {review.get('issue_count', len(review.get('issues') or []))}",
            f"- evidence_traceability_pct: {_pct(trace['traceability_pct'])}",
            f"- evidence_traceability_100: {'yes' if trace['meets_100'] else 'no'}",
            f"- unique_evidence_cited: {metrics.get('unique_evidence_cited', len(bindings))}",
            f"- disclaimer: {(writing.get('disclaimer') or '').strip()}",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_bibtex_from_writing(writing: dict[str, Any] | None) -> str:
    """BibTeX from Evidence → Paper metadata (never invent literature)."""
    bindings = _bindings_from_writing(writing or {})
    if not bindings:
        return ""

    seen_files: set[int] = set()
    entries: list[str] = []

    for b in bindings:
        fid_raw = b.get("file_id")
        fid = int(fid_raw) if fid_raw is not None else None
        if fid is not None:
            if fid in seen_files:
                continue
            seen_files.add(fid)
        authors = str(b.get("authors") or "").strip() or "Unknown"
        title = str(b.get("paper_title") or "").strip() or f"Evidence {b.get('evidence_id')}"
        year = str(b.get("year") or "").strip() or "nd"
        venue = str(b.get("venue") or "").strip()
        doi = str(b.get("doi") or "").strip()
        eid = b.get("evidence_id")
        first_author = authors.split(";")[0].split(",")[0].strip() or "anon"
        key_base = "".join(c for c in first_author if c.isalnum()).lower() or "ref"
        key = f"{key_base}{'' if year == 'nd' else year}_e{eid}"

        fields = [
            f"  author = {{{authors.replace(';', ' and ')}}}",
            f"  title = {{{title}}}",
            f"  year = {{{year}}}",
        ]
        if venue:
            fields.append(f"  journal = {{{venue}}}")
        if doi:
            fields.append(f"  doi = {{{doi}}}")
        fields.append(f"  note = {{Dhund evidence #{eid}}}")
        entries.append("@article{" + key + ",\n" + ",\n".join(fields) + "\n}")

    return "\n\n".join(entries) + "\n"


def merge_persisted_review_into_writing(
    writing: dict[str, Any],
    review: dict[str, Any] | None,
) -> dict[str, Any]:
    """Apply latest persisted Reviewer run onto a client snapshot for gating."""
    if not review:
        return writing
    out = dict(writing)
    out["review"] = review
    has_error = review_has_severity_error(review) or review.get("status") == "fail"
    if writing.get("accept_allowed") is False:
        out["accept_allowed"] = False
    elif has_error:
        out["accept_allowed"] = False
    return out
