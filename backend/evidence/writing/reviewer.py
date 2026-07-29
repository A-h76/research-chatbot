"""Research Reviewer — grounding / citation coverage / unsupported claims.

Sprint B (BETA_EXECUTION_PLAN_v0.2.1): not a grammar checker — research quality.
Primary metrics: Grounding %, Citation Coverage %, Unsupported Claims.
"""

from __future__ import annotations

import re
from typing import Any

REVIEWER_VERSION = "1.1.0"
# Avoid splitting on common abbreviations (esp. "p. 12" page anchors).
_SENTENCE_RE = re.compile(
    r"(?<!\bp)(?<!Mr)(?<!Mrs)(?<!Ms)(?<!Dr)(?<!vs)(?<=[.!?])\s+(?=[A-Z“\"(\\[*])"
)
_MARKER_RE = re.compile(r"\[#(\d+)\]")


def _split_sentences(paragraph: str) -> list[str]:
    chunks: list[str] = []
    for block in (paragraph or "").split("\n"):
        block = block.strip()
        if not block:
            continue
        parts = [p.strip() for p in _SENTENCE_RE.split(block) if p and p.strip()]
        chunks.extend(parts or [block])
    return chunks


def _is_heading_only(sentence: str) -> bool:
    s = sentence.strip()
    return bool(re.match(r"^\*\*[^*]+\.\*\*\s*$", s)) or len(re.sub(r"\[#\d+\]", "", s).strip()) < 12


def review_grounded_draft(
    *,
    sections: list[dict[str, Any]],
    consensus: dict[str, Any] | None = None,
    conflict: dict[str, Any] | None = None,
    supporting_count: int | None = None,
) -> dict[str, Any]:
    """Pass/fail + Research Reviewer issues; never invents EvidenceObjects or prose."""
    issues: list[dict[str, Any]] = []
    checked = 0
    passed = 0
    unsupported_claims = 0
    linked_sections = 0
    cited_ids: set[int] = set()

    for sec in sections:
        checked += 1
        sid = sec.get("id") or ""
        status = sec.get("status")
        paragraph = (sec.get("paragraph") or "").strip()
        bindings = list(sec.get("bindings") or [])
        evidence_ids = list(sec.get("evidence_ids") or [])
        orphan_ids = list(sec.get("orphan_ids") or [])
        title = sec.get("title") or sid

        if status == "empty" or not paragraph:
            issues.append(
                {
                    "code": "empty_section",
                    "severity": "error",
                    "section_id": sid,
                    "message": f"Section “{title}” has no grounded text.",
                }
            )
            continue

        if orphan_ids:
            issues.append(
                {
                    "code": "orphan_citation",
                    "severity": "error",
                    "section_id": sid,
                    "message": (
                        f"Section “{title}” cites unknown EvidenceObject ids: "
                        + ", ".join(f"#{i}" for i in orphan_ids)
                    ),
                }
            )

        if not bindings and not evidence_ids:
            issues.append(
                {
                    "code": "unbound_paragraph",
                    "severity": "error",
                    "section_id": sid,
                    "message": f"Section “{title}” has no EvidenceObject bindings.",
                }
            )
            continue

        if paragraph and not bindings:
            issues.append(
                {
                    "code": "missing_bindings",
                    "severity": "warning",
                    "section_id": sid,
                    "message": "Paragraph text present but citation bindings empty.",
                }
            )

        # Unsupported claims: factual sentences without [#id] markers.
        for sentence in _split_sentences(paragraph):
            if _is_heading_only(sentence):
                continue
            if _MARKER_RE.search(sentence):
                continue
            unsupported_claims += 1
            issues.append(
                {
                    "code": "unsupported_claim",
                    "severity": "error",
                    "section_id": sid,
                    "message": f"Unsupported claim (no [#id] marker): “{sentence[:160]}”",
                }
            )

        # Weak evidence: low-confidence bindings.
        weak = [
            b
            for b in bindings
            if str(b.get("confidence_band") or "").lower() in {"low", "candidate"}
        ]
        if weak:
            ids = ", ".join(f"#{int(b['evidence_id'])}" for b in weak if b.get("evidence_id") is not None)
            issues.append(
                {
                    "code": "weak_evidence",
                    "severity": "warning",
                    "section_id": sid,
                    "message": f"Weak-evidence bindings in “{title}”: {ids}",
                }
            )

        section_errors = [
            i
            for i in issues
            if i.get("section_id") == sid and i.get("severity") == "error"
        ]
        if not section_errors:
            passed += 1
            linked_sections += 1
            for b in bindings:
                if b.get("evidence_id") is not None:
                    cited_ids.add(int(b["evidence_id"]))

    if (consensus or {}).get("label") in {"contested", "weak"}:
        issues.append(
            {
                "code": "contested_consensus",
                "severity": "warning",
                "section_id": None,
                "message": "Consensus is weak or contested; treat Lit Review as provisional.",
            }
        )

    if (conflict or {}).get("has_conflict"):
        mediators = list((conflict or {}).get("mediators") or [])
        issues.append(
            {
                "code": "conflict_present",
                "severity": "warning",
                "section_id": None,
                "message": (
                    "Conflicting evidence present"
                    + (f" ({', '.join(mediators)})" if mediators else "")
                    + "; verify conflicted paragraphs before export."
                ),
            }
        )

    errors = [i for i in issues if i.get("severity") == "error"]
    pass_rate = round(passed / checked, 4) if checked else 0.0
    status = "pass" if not errors else "fail"
    support_n = supporting_count if supporting_count is not None else max(len(cited_ids), 1)
    grounding_pct = round(linked_sections / checked, 4) if checked else 0.0
    citation_coverage_pct = (
        round(len(cited_ids) / support_n, 4) if support_n > 0 else 0.0
    )

    return {
        "reviewer_version": REVIEWER_VERSION,
        "name": "research_reviewer",
        "status": status,
        "pass_rate": pass_rate,
        "sections_checked": checked,
        "sections_passed": passed,
        "issue_count": len(issues),
        "issues": issues,
        "metrics": {
            "grounding_pct": grounding_pct,
            "citation_coverage_pct": citation_coverage_pct,
            "unsupported_claims": unsupported_claims,
        },
    }
