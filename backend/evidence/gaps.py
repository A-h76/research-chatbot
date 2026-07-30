"""Research Gap Engine (RI-006) — coverage gaps from themes + matrix (+ conflict).

Deterministic. Statements and questions are templated from project signals —
never invents literature or evidence ids.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from backend.evidence.matrix import build_evidence_matrix
from backend.evidence.themes import discover_themes, reconstruct_fingerprint

GAPS_VERSION = "1.0.0"

_COLUMN_QUESTIONS = {
    "method": "What study designs are still missing for this paper/topic?",
    "dataset": "Which populations or datasets are underrepresented here?",
    "findings": "What claims lack page-anchored evidence for this paper?",
    "limitations": "What limitations are documented in the source papers?",
}


def _stable_id(*parts: str) -> str:
    raw = "|".join(parts)
    return "gap_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _density(n: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(min(1.0, max(0.0, n / total)), 4)


def discover_gaps(
    *,
    project_id: int,
    papers: list[dict[str, Any]],
    evidence_objects: list[dict[str, Any]],
    analysis_by_file: dict[int, dict[str, Any]] | None = None,
    themes_payload: dict[str, Any] | None = None,
    matrix_payload: dict[str, Any] | None = None,
    conflict_payload: dict[str, Any] | None = None,
    consensus_payload: dict[str, Any] | None = None,
    min_theme_papers: int = 2,
    max_gaps: int = 40,
) -> dict[str, Any]:
    """Emit research gaps grounded in themes/matrix/conflict coverage."""
    objs = [o for o in evidence_objects if o.get("id") is not None]
    total_ev = len(objs)
    by_file: dict[int, list[dict[str, Any]]] = {}
    for o in objs:
        if o.get("file_id") is None:
            continue
        by_file.setdefault(int(o["file_id"]), []).append(o)

    themes_payload = themes_payload or discover_themes(objs, project_id=project_id)
    if matrix_payload is None:
        matrix_payload = build_evidence_matrix(
            project_id=project_id,
            papers=papers,
            evidence_by_file=by_file,
            analysis_by_file=analysis_by_file or {},
        )

    gaps: list[dict[str, Any]] = []

    # 1) Thin themes — few papers
    for theme in themes_payload.get("themes") or []:
        file_ids = list(theme.get("file_ids") or [])
        eids = [int(x) for x in (theme.get("evidence_ids") or [])]
        if len(file_ids) >= min_theme_papers and theme.get("size", 0) >= 3:
            continue
        terms = ", ".join((theme.get("key_terms") or [])[:3]) or "this theme"
        label = theme.get("label") or theme.get("id")
        gaps.append(
            {
                "id": _stable_id("thin_theme", str(theme.get("id")), ",".join(map(str, eids))),
                "type": "thin_theme",
                "statement": (
                    f"{label} is thinly covered "
                    f"({len(file_ids)} paper(s), {len(eids)} evidence). "
                    f"Most project evidence does not yet cluster on {terms}."
                ),
                "evidence_density": _density(len(eids), total_ev),
                "suggested_questions": [
                    f"Which additional papers address {terms}?",
                    f"Are there conflicting findings under {terms} not yet extracted?",
                ],
                "evidence_ids": eids,
                "theme_id": theme.get("id"),
                "file_ids": file_ids,
            }
        )

    # 2) High unassigned / low theme coverage
    unassigned = themes_payload.get("unassigned") or {}
    u_ids = [int(x) for x in (unassigned.get("evidence_ids") or [])]
    cov = (themes_payload.get("metrics") or {}).get("coverage")
    if u_ids and (cov is None or cov < 0.7):
        gaps.append(
            {
                "id": _stable_id("coverage", "themes", ",".join(map(str, sorted(u_ids)[:20]))),
                "type": "coverage",
                "statement": (
                    f"{len(u_ids)} evidence objects remain unassigned to a theme "
                    f"(theme coverage {cov if cov is not None else 'n/a'}). "
                    "The corpus may contain fragmented or one-off findings."
                ),
                "evidence_density": _density(len(u_ids), total_ev),
                "suggested_questions": [
                    "Do unassigned claims share a population or method not yet labeled?",
                    "Should extraction be re-run on papers with sparse theme membership?",
                ],
                "evidence_ids": u_ids[:40],
                "file_ids": sorted(
                    {
                        int(o["file_id"])
                        for o in objs
                        if int(o["id"]) in set(u_ids[:40]) and o.get("file_id") is not None
                    }
                ),
            }
        )

    # 3) Missing matrix cells
    for row in matrix_payload.get("rows") or []:
        fid = int(row["file_id"])
        title = row.get("paper_title") or f"Paper #{fid}"
        for col in ("method", "dataset", "findings", "limitations"):
            cell = row.get(col) or {}
            if cell.get("status") != "unknown":
                continue
            # Prefer rows that have some evidence (gap = missing facet) or none
            eids = [int(o["id"]) for o in by_file.get(fid, [])]
            gaps.append(
                {
                    "id": _stable_id("missing_matrix_cell", str(fid), col),
                    "type": "missing_matrix_cell",
                    "statement": (
                        f"“{title}” has unknown {col} in the evidence matrix "
                        f"({len(eids)} linked evidence)."
                    ),
                    "evidence_density": _density(len(eids), max(total_ev, 1)),
                    "suggested_questions": [
                        _COLUMN_QUESTIONS[col],
                        f"Can {col} be filled from accepted evidence or paper analysis for this paper?",
                    ],
                    "evidence_ids": eids[:20],
                    "file_ids": [fid],
                    "matrix": {"file_id": fid, "column": col},
                }
            )

    # 4) Weak consensus (project-level if provided)
    consensus = consensus_payload or {}
    product = consensus.get("product_label") or ""
    label = consensus.get("label") or ""
    if product == "Weak evidence" or label == "none":
        eids = sorted(
            set(int(x) for x in (consensus.get("supporting_ids") or []))
            | set(int(x) for x in (consensus.get("contradicting_ids") or []))
            | set(int(x) for x in (consensus.get("neutral_ids") or []))
        )
        gaps.append(
            {
                "id": _stable_id("weak_consensus", product or label, ",".join(map(str, eids[:20]))),
                "type": "weak_consensus",
                "statement": (
                    f"Project consensus is weak ({product or label}): "
                    "supporting evidence is thin relative to the corpus."
                ),
                "evidence_density": _density(len(eids), total_ev),
                "suggested_questions": [
                    "Which claims need higher-confidence accepted evidence?",
                    "Is the research question underspecified for this corpus?",
                ],
                "evidence_ids": eids[:40],
            }
        )

    # 5) Unexplained conflicts
    conflict = conflict_payload or {}
    for link in conflict.get("links") or []:
        if not link.get("unexplained"):
            continue
        try:
            a = int(link["a_id"])
            b = int(link["b_id"])
        except (KeyError, TypeError, ValueError):
            continue
        gaps.append(
            {
                "id": _stable_id("unexplained_conflict", str(a), str(b)),
                "type": "unexplained_conflict",
                "statement": (
                    f"Evidence #{a} and #{b} conflict without a coded mediator "
                    "(population/method/outcome/statistics unexplained)."
                ),
                "evidence_density": _density(2, max(total_ev, 1)),
                "suggested_questions": [
                    "Do the studies differ in sample, dose, method, or outcome definition?",
                    "What additional extraction would explain this disagreement?",
                ],
                "evidence_ids": [a, b],
                "conflict_link": {"a_id": a, "b_id": b},
            }
        )

    # Stable sort then cap
    gaps.sort(key=lambda g: (g["type"], g["id"]))
    if len(gaps) > max_gaps:
        # Prefer unexplained_conflict and thin_theme, then missing cells
        priority = {
            "unexplained_conflict": 0,
            "thin_theme": 1,
            "weak_consensus": 2,
            "coverage": 3,
            "missing_matrix_cell": 4,
        }
        gaps.sort(key=lambda g: (priority.get(g["type"], 9), g["id"]))
        gaps = gaps[:max_gaps]
        gaps.sort(key=lambda g: (g["type"], g["id"]))

    by_type: dict[str, int] = {}
    for g in gaps:
        by_type[g["type"]] = by_type.get(g["type"], 0) + 1
    densities = [g["evidence_density"] for g in gaps]
    mean_density = round(sum(densities) / len(densities), 4) if densities else None

    theme_fp = reconstruct_fingerprint(themes_payload)
    matrix_cov = (matrix_payload.get("metrics") or {}).get("coverage")
    run_hash = hashlib.sha256(
        json.dumps(
            {
                "theme_fp": theme_fp,
                "matrix_coverage": matrix_cov,
                "gap_ids": [g["id"] for g in gaps],
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    return {
        "stage": "gaps",
        "gaps_version": GAPS_VERSION,
        "project_id": int(project_id),
        "run": {
            "input_hash": run_hash,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "params": {
                "min_theme_papers": min_theme_papers,
                "max_gaps": max_gaps,
            },
            "sources": ["themes", "matrix"]
            + (["consensus"] if consensus_payload else [])
            + (["conflict"] if conflict_payload else []),
            "themes_fingerprint": theme_fp,
            "matrix_coverage": matrix_cov,
        },
        "gaps": gaps,
        "metrics": {
            "gap_count": len(gaps),
            "by_type": by_type,
            "mean_density": mean_density,
            "evidence_count": total_ev,
            "paper_count": len(papers),
        },
    }


def gaps_to_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Research Gaps (project {payload.get('project_id')})",
        "",
        f"_gaps_version {payload.get('gaps_version')} · "
        f"{(payload.get('metrics') or {}).get('gap_count', 0)} gaps · "
        f"hash `{(payload.get('run') or {}).get('input_hash', '')[:12]}…`_",
        "",
    ]
    for g in payload.get("gaps") or []:
        lines.append(f"## [{g.get('type')}] {g.get('id')}")
        lines.append("")
        lines.append(g.get("statement") or "")
        lines.append("")
        lines.append(f"- Evidence density: {g.get('evidence_density')}")
        lines.append(f"- Evidence ids: {g.get('evidence_ids')}")
        qs = g.get("suggested_questions") or []
        if qs:
            lines.append("- Questions:")
            for q in qs:
                lines.append(f"  - {q}")
        lines.append("")
    return "\n".join(lines)
