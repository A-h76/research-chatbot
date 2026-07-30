"""Methodology Intelligence (RI-008) — advisory cards grounded in Evidence.

Tone is supportive (suggest / consider), never imperative commands.
Never invents literature; every card cites evidence_ids or matrix anchors.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from backend.evidence.gaps import discover_gaps
from backend.evidence.matrix import build_evidence_matrix
from backend.evidence.themes import discover_themes, reconstruct_fingerprint

METHODOLOGY_VERSION = "1.0.0"

# Advisory designs researchers often compare — only suggested when absent.
_COMMON_DESIGNS = (
    "RCT",
    "cohort",
    "case-control",
    "cross-sectional",
    "meta-analysis",
    "qualitative",
)


def _card_id(*parts: str) -> str:
    return "meth_" + hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]


def _norm_design(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    low = s.lower()
    aliases = {
        "randomized controlled trial": "RCT",
        "randomised controlled trial": "RCT",
        "rct": "RCT",
        "meta analysis": "meta-analysis",
        "systematic review": "meta-analysis",
        "case control": "case-control",
        "cross sectional": "cross-sectional",
    }
    return aliases.get(low, s)


def build_methodology_advice(
    *,
    project_id: int,
    papers: list[dict[str, Any]],
    evidence_objects: list[dict[str, Any]],
    analysis_by_file: dict[int, dict[str, Any]] | None = None,
    themes_payload: dict[str, Any] | None = None,
    matrix_payload: dict[str, Any] | None = None,
    gaps_payload: dict[str, Any] | None = None,
    consensus_payload: dict[str, Any] | None = None,
    max_cards: int = 24,
) -> dict[str, Any]:
    objs = [o for o in evidence_objects if o.get("id") is not None]
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
    if gaps_payload is None:
        gaps_payload = discover_gaps(
            project_id=project_id,
            papers=papers,
            evidence_objects=objs,
            analysis_by_file=analysis_by_file,
            themes_payload=themes_payload,
            matrix_payload=matrix_payload,
            consensus_payload=consensus_payload,
        )

    design_counts: Counter[str] = Counter()
    design_eids: dict[str, list[int]] = {}
    limitation_bits: list[tuple[str, int]] = []
    dataset_known: list[tuple[str, list[int]]] = []
    stats_bits: list[tuple[str, int]] = []

    for o in objs:
        eid = int(o["id"])
        st = _norm_design(str(o.get("study_type") or ""))
        if st:
            design_counts[st] += 1
            design_eids.setdefault(st, []).append(eid)
        for lim in o.get("limitations") or []:
            s = str(lim).strip()
            if s:
                limitation_bits.append((s, eid))
        prov = o.get("provenance") if isinstance(o.get("provenance"), dict) else {}
        for key in ("statistics", "analysis", "statistical_test"):
            val = prov.get(key)
            if isinstance(val, str) and val.strip():
                stats_bits.append((val.strip(), eid))
            elif isinstance(val, list):
                for item in val:
                    if str(item).strip():
                        stats_bits.append((str(item).strip(), eid))

    for row in matrix_payload.get("rows") or []:
        cell = row.get("dataset") or {}
        if cell.get("status") == "known" and cell.get("value"):
            dataset_known.append((str(cell["value"]), list(cell.get("evidence_ids") or [])))

    cards: list[dict[str, Any]] = []

    # 1) Design landscape
    if design_counts:
        top = ", ".join(f"{k} ({v})" for k, v in design_counts.most_common(5))
        all_ids = [eid for ids in design_eids.values() for eid in ids]
        cards.append(
            {
                "id": _card_id("design_landscape", top),
                "kind": "study_design",
                "title": "Study designs in this corpus",
                "advice": (
                    f"Current evidence leans on: {top}. "
                    "You may want to weigh findings by design strength when synthesizing."
                ),
                "tone": "advisory",
                "evidence_ids": sorted(set(all_ids))[:40],
                "anchors": {"designs": dict(design_counts)},
            }
        )
    else:
        cards.append(
            {
                "id": _card_id("design_landscape", "empty"),
                "kind": "study_design",
                "title": "Study design not yet coded",
                "advice": (
                    "Few EvidenceObjects carry a study_type. "
                    "Consider extracting or reviewing designs so methodology comparisons stay grounded."
                ),
                "tone": "advisory",
                "evidence_ids": [int(o["id"]) for o in objs[:20]],
                "anchors": {"designs": {}},
            }
        )

    # 2) Missing common designs (only if corpus has some designs already)
    present = {_norm_design(k).lower() for k in design_counts}
    missing = [d for d in _COMMON_DESIGNS if d.lower() not in present]
    if design_counts and missing:
        cards.append(
            {
                "id": _card_id("missing_designs", ",".join(missing[:4])),
                "kind": "study_design",
                "title": "Designs not yet represented",
                "advice": (
                    "This project’s evidence does not yet include: "
                    + ", ".join(missing[:4])
                    + ". If those designs exist in your library, extracting them could "
                    "balance the methodological picture — this is not a requirement to run new studies."
                ),
                "tone": "advisory",
                "evidence_ids": [],
                "anchors": {"missing_designs": missing[:6]},
            }
        )

    # 3) Dataset coverage from matrix
    unknown_dataset_rows = [
        r
        for r in (matrix_payload.get("rows") or [])
        if (r.get("dataset") or {}).get("status") == "unknown"
    ]
    if dataset_known:
        sample = "; ".join(v for v, _ in dataset_known[:3])
        eids = [i for _, ids in dataset_known for i in ids]
        cards.append(
            {
                "id": _card_id("datasets", sample[:80]),
                "kind": "dataset",
                "title": "Datasets / sources observed",
                "advice": (
                    f"Documented datasets include: {sample}. "
                    "You may compare whether outcomes generalize across these sources."
                ),
                "tone": "advisory",
                "evidence_ids": sorted(set(eids))[:30],
                "anchors": {"dataset_count": len(dataset_known)},
            }
        )
    if unknown_dataset_rows:
        fids = [int(r["file_id"]) for r in unknown_dataset_rows[:8]]
        cards.append(
            {
                "id": _card_id("datasets_unknown", ",".join(map(str, fids))),
                "kind": "dataset",
                "title": "Dataset cells still unknown",
                "advice": (
                    f"{len(unknown_dataset_rows)} paper(s) lack a known dataset in the matrix. "
                    "Filling those cells from paper analysis or provenance would clarify sampling coverage."
                ),
                "tone": "advisory",
                "evidence_ids": [],
                "file_ids": fids,
                "anchors": {"unknown_dataset_papers": len(unknown_dataset_rows)},
            }
        )

    # 4) Variables / outcomes from supports arrays
    outcomes: Counter[str] = Counter()
    outcome_eids: dict[str, list[int]] = {}
    for o in objs:
        eid = int(o["id"])
        for s in o.get("supports") or []:
            label = str(s).strip()
            if label:
                outcomes[label] += 1
                outcome_eids.setdefault(label, []).append(eid)
    if outcomes:
        top_out = ", ".join(f"{k}" for k, _ in outcomes.most_common(4))
        cards.append(
            {
                "id": _card_id("variables", top_out[:80]),
                "kind": "variables",
                "title": "Outcomes / variables in evidence",
                "advice": (
                    f"Recurring supported outcomes include: {top_out}. "
                    "Consider whether your research question aligns with these measured variables."
                ),
                "tone": "advisory",
                "evidence_ids": sorted(
                    {i for ids in list(outcome_eids.values())[:4] for i in ids}
                )[:30],
                "anchors": {"top_outcomes": [k for k, _ in outcomes.most_common(6)]},
            }
        )

    # 5) Statistical tests (provenance only — never invent)
    if stats_bits:
        seen = []
        eids = []
        for text, eid in stats_bits:
            if text.lower() not in {s.lower() for s in seen}:
                seen.append(text)
                eids.append(eid)
            if len(seen) >= 4:
                break
        cards.append(
            {
                "id": _card_id("stats", ",".join(seen)[:80]),
                "kind": "statistics",
                "title": "Statistical approaches noted",
                "advice": (
                    "Provenance mentions: "
                    + "; ".join(seen)
                    + ". You may review whether these tests match your planned analysis."
                ),
                "tone": "advisory",
                "evidence_ids": eids,
                "anchors": {"tests": seen},
            }
        )
    else:
        cards.append(
            {
                "id": _card_id("stats", "none"),
                "kind": "statistics",
                "title": "Statistical methods not yet extracted",
                "advice": (
                    "No statistical_test / analysis fields appear in evidence provenance yet. "
                    "When available, they can inform threats-to-validity discussions."
                ),
                "tone": "advisory",
                "evidence_ids": [],
                "anchors": {"tests": []},
            }
        )

    # 6) Threats to validity from limitations + unexplained conflicts in gaps
    lim_sample = []
    lim_eids = []
    for text, eid in limitation_bits:
        if text.lower() not in {t.lower() for t in lim_sample}:
            lim_sample.append(text[:160])
            lim_eids.append(eid)
        if len(lim_sample) >= 3:
            break
    unexplained = [
        g for g in (gaps_payload.get("gaps") or []) if g.get("type") == "unexplained_conflict"
    ]
    if lim_sample or unexplained:
        advice_parts = []
        if lim_sample:
            advice_parts.append(
                "Documented limitations include: " + "; ".join(lim_sample) + "."
            )
        if unexplained:
            advice_parts.append(
                f"{len(unexplained)} unexplained conflict pair(s) may signal "
                "unmeasured mediators (sample, method, or outcome definitions)."
            )
        advice_parts.append(
            "These are prompts for appraisal — not instructions to discard papers."
        )
        cards.append(
            {
                "id": _card_id(
                    "threats",
                    ",".join(lim_sample[:2]),
                    str(len(unexplained)),
                ),
                "kind": "threats_to_validity",
                "title": "Threats to validity to consider",
                "advice": " ".join(advice_parts),
                "tone": "advisory",
                "evidence_ids": sorted(
                    set(lim_eids)
                    | {
                        eid
                        for g in unexplained[:5]
                        for eid in (g.get("evidence_ids") or [])
                    }
                )[:40],
                "anchors": {
                    "limitation_count": len(limitation_bits),
                    "unexplained_conflicts": len(unexplained),
                },
            }
        )

    # 7) Consensus-aware method note
    consensus = consensus_payload or {}
    product = consensus.get("product_label") or ""
    if product in {"Mixed", "Disagree", "Weak evidence"}:
        cards.append(
            {
                "id": _card_id("consensus_method", product),
                "kind": "study_design",
                "title": "Consensus suggests methodological caution",
                "advice": (
                    f"Project consensus is “{product}”. "
                    "When synthesizing, you may separate findings by design, population, "
                    "or outcome definition before drawing a single conclusion."
                ),
                "tone": "advisory",
                "evidence_ids": sorted(
                    set(int(x) for x in (consensus.get("supporting_ids") or []))
                    | set(int(x) for x in (consensus.get("contradicting_ids") or []))
                )[:30],
                "anchors": {"product_label": product},
            }
        )

    cards = cards[:max_cards]
    by_kind: dict[str, int] = {}
    for c in cards:
        by_kind[c["kind"]] = by_kind.get(c["kind"], 0) + 1

    theme_fp = reconstruct_fingerprint(themes_payload)
    run_hash = hashlib.sha256(
        json.dumps(
            {
                "theme_fp": theme_fp,
                "card_ids": [c["id"] for c in cards],
                "designs": dict(design_counts),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    return {
        "stage": "methodology",
        "methodology_version": METHODOLOGY_VERSION,
        "project_id": int(project_id),
        "run": {
            "input_hash": run_hash,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sources": ["evidence_objects", "matrix", "gaps", "themes"],
            "themes_fingerprint": theme_fp,
        },
        "cards": cards,
        "design_summary": {
            "counts": dict(design_counts),
            "evidence_ids_by_design": {k: v[:20] for k, v in design_eids.items()},
        },
        "metrics": {
            "card_count": len(cards),
            "by_kind": by_kind,
            "design_variety": len(design_counts),
            "evidence_count": len(objs),
        },
        "disclaimer": (
            "Advisory only — grounded in project EvidenceObjects and matrix cells. "
            "Does not recommend running new studies or inventing literature."
        ),
    }


def methodology_to_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Methodology Intelligence (project {payload.get('project_id')})",
        "",
        f"_{payload.get('disclaimer')}_",
        "",
    ]
    for card in payload.get("cards") or []:
        lines.append(f"## {card.get('title')} ({card.get('kind')})")
        lines.append("")
        lines.append(card.get("advice") or "")
        lines.append("")
        if card.get("evidence_ids"):
            lines.append(f"- Evidence ids: {card['evidence_ids']}")
        lines.append("")
    return "\n".join(lines)
