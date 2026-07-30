"""RI-009 — Research → Writing bridge (not a separate writing engine).

Builds structured writing context from RI stages so the LLM stays last:
themes, consensus, conflicts, gaps, methods, timeline → outline → draft metadata.
Never invents papers or evidence ids.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from backend.evidence.gaps import discover_gaps
from backend.evidence.methodology import build_methodology_advice
from backend.evidence.themes import discover_themes, reconstruct_fingerprint
from backend.evidence.timeline import build_timeline

RI_DEPTH_VERSION = "1.1.0"
PROMPT_VERSION_HEURISTIC = "heuristic_compose_v1"
PROMPT_VERSION_GATEWAY = "gateway_section_generator_v2"


def _papers_from_objects(objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    papers: list[dict[str, Any]] = []
    seen: set[int] = set()
    for o in objects:
        fid = o.get("file_id")
        if fid is None:
            continue
        fid = int(fid)
        if fid in seen:
            continue
        seen.add(fid)
        papers.append(
            {
                "id": fid,
                "file_id": fid,
                "title": (o.get("file_title") or f"Paper #{fid}"),
                "year": "",
            }
        )
    return papers


def build_ri_writing_context(
    *,
    project_id: int | None,
    objects: list[dict[str, Any]],
    consensus: dict[str, Any] | None,
    conflict: dict[str, Any] | None,
) -> dict[str, Any]:
    """Full RI depth for the writing bridge (themes→gaps→methods→timeline)."""
    objs = [o for o in objects if o.get("id") is not None]
    papers = _papers_from_objects(objs)
    pid = int(project_id) if project_id is not None else 0

    themes_payload = discover_themes(objs, project_id=pid)
    gaps_payload = discover_gaps(
        project_id=pid,
        papers=papers,
        evidence_objects=objs,
        themes_payload=themes_payload,
        consensus_payload=consensus,
        conflict_payload=conflict,
        max_gaps=12,
    )
    timeline_payload = build_timeline(
        project_id=pid,
        papers=papers,
        evidence_objects=objs,
        themes_payload=themes_payload,
    )
    methodology_payload = build_methodology_advice(
        project_id=pid,
        papers=papers,
        evidence_objects=objs,
        themes_payload=themes_payload,
        gaps_payload=gaps_payload,
        consensus_payload=consensus,
        max_cards=8,
    )

    theme_summaries = [
        {
            "id": t.get("id"),
            "label": t.get("label"),
            "key_terms": list(t.get("key_terms") or [])[:5],
            "evidence_ids": list(t.get("evidence_ids") or []),
            "size": t.get("size"),
        }
        for t in (themes_payload.get("themes") or [])[:8]
    ]
    gap_summaries = [
        {
            "id": g.get("id"),
            "type": g.get("type"),
            "statement": g.get("statement"),
            "suggested_questions": list(g.get("suggested_questions") or [])[:2],
            "evidence_ids": list(g.get("evidence_ids") or [])[:20],
        }
        for g in (gaps_payload.get("gaps") or [])[:8]
    ]
    method_cards = [
        {
            "id": c.get("id"),
            "kind": c.get("kind"),
            "title": c.get("title"),
            "advice": (c.get("advice") or "")[:280],
            "evidence_ids": list(c.get("evidence_ids") or [])[:12],
        }
        for c in (methodology_payload.get("cards") or [])[:6]
    ]
    timeline_entries = [
        {
            "year": e.get("year"),
            "evidence_count": e.get("evidence_count"),
            "theme_ids": list(e.get("theme_ids") or [])[:6],
            "sample_evidence_ids": [
                s.get("evidence_id") for s in (e.get("sample_claims") or [])[:3]
            ],
        }
        for e in (timeline_payload.get("entries") or [])[:8]
    ]

    return {
        "ri_depth_version": RI_DEPTH_VERSION,
        "themes": theme_summaries,
        "themes_fingerprint": reconstruct_fingerprint(themes_payload),
        "gaps": gap_summaries,
        "gap_count": len(gaps_payload.get("gaps") or []),
        "methodology": {
            "cards": method_cards,
            "design_counts": (methodology_payload.get("design_summary") or {}).get("counts")
            or {},
        },
        "timeline": {
            "span": timeline_payload.get("span"),
            "entries": timeline_entries,
            "evolution": (timeline_payload.get("evolution") or [])[:6],
        },
        "consensus": {
            "label": (consensus or {}).get("label"),
            "product_label": (consensus or {}).get("product_label"),
            "supporting_ids": list((consensus or {}).get("supporting_ids") or []),
            "contradicting_ids": list((consensus or {}).get("contradicting_ids") or []),
        },
        "conflict": {
            "has_conflict": bool((conflict or {}).get("has_conflict")),
            "mediators": list((conflict or {}).get("mediators") or []),
            "product_summary": (conflict or {}).get("product_summary"),
            "unexplained_pair_count": ((conflict or {}).get("metrics") or {}).get(
                "unexplained_pair_count"
            ),
        },
        "metrics": {
            "theme_count": len(theme_summaries),
            "gap_count": len(gap_summaries),
            "method_card_count": len(method_cards),
            "timeline_year_count": (timeline_payload.get("span") or {}).get("year_count") or 0,
            "object_count": len(objs),
        },
    }


def merge_ri_into_argument(
    argument: dict[str, Any],
    ri_context: dict[str, Any] | None,
) -> dict[str, Any]:
    """Prefer RI theme clusters; attach gaps/methods/timeline for composers."""
    if not ri_context:
        return argument
    out = dict(argument)
    ri_themes = ri_context.get("themes") or []
    if ri_themes:
        out["theme_clusters"] = [
            {
                "theme": t.get("label") or t.get("id"),
                "theme_id": t.get("id"),
                "evidence_ids": list(t.get("evidence_ids") or []),
                "size": t.get("size") or len(t.get("evidence_ids") or []),
                "key_terms": list(t.get("key_terms") or []),
            }
            for t in ri_themes
        ]
        out["themes_source"] = "ri_001"
    else:
        out["themes_source"] = "token_fallback"
    out["research_gaps"] = list(ri_context.get("gaps") or [])
    out["ri_consensus"] = ri_context.get("consensus") or {}
    out["ri_methodology"] = ri_context.get("methodology") or {}
    out["ri_timeline"] = ri_context.get("timeline") or {}
    out["argument_version"] = "1.2.0"
    return out


def build_theme_outline(
    *,
    plan: dict[str, Any],
    contexts: list[dict[str, Any]],
    ri_context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Outline generator — section slots wired to themes/evidence (LLM still last)."""
    themes = list((ri_context or {}).get("themes") or [])
    outline: list[dict[str, Any]] = []
    for i, slot in enumerate(plan.get("slots") or []):
        ctx = contexts[i] if i < len(contexts) else {}
        eids = list(ctx.get("evidence_ids") or [])
        # Map themes that overlap this slot's evidence
        theme_ids = [
            str(t.get("id"))
            for t in themes
            if t.get("id")
            and set(int(x) for x in (t.get("evidence_ids") or [])).intersection(eids)
        ]
        outline.append(
            {
                "slot_id": slot.get("id"),
                "title": slot.get("title"),
                "purpose": slot.get("purpose"),
                "facet": ctx.get("facet"),
                "theme_ids": theme_ids,
                "evidence_ids": eids,
                "paper_ids": sorted(
                    {
                        int(o["file_id"])
                        for o in (ctx.get("evidence_objects") or [])
                        if o.get("file_id") is not None
                    }
                ),
            }
        )
    return outline


def build_draft_metadata(
    *,
    writing_version: str,
    ri_context: dict[str, Any] | None,
    citations: list[dict[str, Any]],
    sections: list[dict[str, Any]],
    consensus: dict[str, Any] | None,
    conflict: dict[str, Any] | None,
    consensus_version: str | None = None,
    conflict_version: str | None = None,
    prompt_version: str | None = None,
    used_gateway: bool = False,
) -> dict[str, Any]:
    """Reproducible draft provenance — evidence/theme/gap versions for export."""
    ri = ri_context or {}
    evidence_ids = sorted(
        {
            int(c["evidence_id"])
            for c in citations
            if c.get("evidence_id") is not None
        }
        | {
            int(eid)
            for sec in sections
            for eid in (sec.get("evidence_ids") or [])
            if eid is not None
        }
    )
    theme_ids = [str(t.get("id")) for t in (ri.get("themes") or []) if t.get("id")]
    gap_ids = [str(g.get("id")) for g in (ri.get("gaps") or []) if g.get("id")]
    pv = prompt_version or (
        PROMPT_VERSION_GATEWAY if used_gateway else PROMPT_VERSION_HEURISTIC
    )
    raw = json.dumps(
        {
            "evidence_ids": evidence_ids,
            "theme_ids": theme_ids,
            "themes_fingerprint": ri.get("themes_fingerprint"),
            "writing_version": writing_version,
            "ri_depth_version": ri.get("ri_depth_version"),
            "prompt_version": pv,
        },
        sort_keys=True,
    )
    return {
        "evidence_ids": evidence_ids,
        "theme_ids": theme_ids,
        "gap_ids": gap_ids,
        "paper_ids": sorted(
            {
                int(c["file_id"])
                for c in citations
                if c.get("file_id") is not None
            }
        ),
        "consensus_label": (consensus or {}).get("label"),
        "product_label": (consensus or {}).get("product_label")
        or (ri.get("consensus") or {}).get("product_label"),
        "consensus_version": consensus_version,
        "conflict_version": conflict_version,
        "has_conflict": bool((conflict or {}).get("has_conflict")),
        "mediators": list((conflict or {}).get("mediators") or []),
        "writing_version": writing_version,
        "ri_depth_version": ri.get("ri_depth_version"),
        "themes_fingerprint": ri.get("themes_fingerprint"),
        "prompt_version": pv,
        "reproducibility_hash": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    }
