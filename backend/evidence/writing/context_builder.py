"""Context Builder — structured argument + per-slot EvidenceObject allocation.

Sprint A (BETA_EXECUTION_PLAN_v0.2.1): the generator receives a structured
argument, not a flat paper dump:

  Evidence → Theme clusters → Consensus → Conflict → Methodology → Chronology
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_STOP = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "for",
        "with",
        "from",
        "by",
        "is",
        "are",
        "was",
        "were",
        "that",
        "this",
        "these",
        "those",
        "as",
        "at",
        "be",
        "been",
        "being",
        "it",
        "its",
        "into",
        "than",
        "then",
        "there",
        "their",
        "they",
        "we",
        "our",
        "vs",
        "versus",
    }
)

# Slot id / purpose hints → which argument facet drives allocation.
_SLOT_FACET: dict[str, str] = {
    "themes": "themes",
    "overview": "themes",
    "covered": "themes",
    "key_findings": "consensus",
    "findings": "consensus",
    "supporting_points": "consensus",
    "significance": "consensus",
    "headline": "consensus",
    "problem": "consensus",
    "interpretation": "consensus",
    "implications": "consensus",
    "tensions": "conflict",
    "limitations": "conflict",
    "cautions": "conflict",
    "caveats": "conflict",
    "undercovered": "conflict",
    "next_questions": "conflict",
    "population": "methodology",
    "support": "consensus",
}


def _obj_year(obj: dict[str, Any]) -> int | None:
    prov = obj.get("provenance") if isinstance(obj.get("provenance"), dict) else {}
    for key in ("year", "publication_year", "pub_year"):
        raw = obj.get(key) if key in obj else prov.get(key)
        if raw is None:
            continue
        try:
            y = int(raw)
            if 1900 <= y <= 2100:
                return y
        except (TypeError, ValueError):
            pass
    text = f"{obj.get('claim') or ''} {obj.get('quote') or ''}"
    m = _YEAR_RE.search(text)
    return int(m.group(0)) if m else None


def _theme_key(obj: dict[str, Any]) -> str:
    claim = (obj.get("claim") or obj.get("quote") or "").lower()
    tokens = re.findall(r"[a-z0-9]+", claim)
    keep = [t for t in tokens if t not in _STOP and len(t) > 2][:3]
    if keep:
        return " ".join(keep)
    st = (obj.get("study_type") or "").strip().lower()
    return st or "general"


def _conf_rank(obj: dict[str, Any]) -> int:
    return {"high": 3, "moderate": 2, "low": 1}.get(
        str(obj.get("confidence_band") or "low").lower(), 0
    )


def build_structured_argument(
    *,
    supporting: list[dict[str, Any]],
    consensus: dict[str, Any] | None,
    conflict: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build the structured argument envelope for gateway prompts + allocation."""
    themes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    methods: dict[str, list[dict[str, Any]]] = defaultdict(list)
    chronology: list[dict[str, Any]] = []

    for obj in supporting:
        themes[_theme_key(obj)].append(obj)
        st = (obj.get("study_type") or "").strip() or "unspecified"
        methods[st].append(obj)
        chronology.append({"evidence_id": int(obj["id"]), "year": _obj_year(obj), "object": obj})

    chronology.sort(
        key=lambda row: (row["year"] is None, row["year"] or 0, row["evidence_id"])
    )

    theme_clusters = [
        {
            "theme": key,
            "evidence_ids": [int(o["id"]) for o in objs if o.get("id") is not None],
            "size": len(objs),
        }
        for key, objs in sorted(themes.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    ]

    methodology = [
        {
            "study_type": key,
            "evidence_ids": [int(o["id"]) for o in objs if o.get("id") is not None],
            "size": len(objs),
        }
        for key, objs in sorted(methods.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    ]

    label = (consensus or {}).get("label") or "none"
    supporting_ids = [int(x) for x in (consensus or {}).get("supporting_ids") or []]
    contradicting_ids = [int(x) for x in (consensus or {}).get("contradicting_ids") or []]

    return {
        "theme_clusters": theme_clusters,
        "consensus": {
            "label": label,
            "supporting_ids": supporting_ids,
            "contradicting_ids": contradicting_ids,
        },
        "conflict": {
            "has_conflict": bool((conflict or {}).get("has_conflict")),
            "mediators": list((conflict or {}).get("mediators") or []),
        },
        "methodology": methodology,
        "chronology": [
            {"evidence_id": row["evidence_id"], "year": row["year"]} for row in chronology
        ],
        "argument_version": "1.0.0",
    }


def _facet_for_slot(slot: dict[str, Any]) -> str:
    sid = str(slot.get("id") or "").lower()
    if sid in _SLOT_FACET:
        return _SLOT_FACET[sid]
    purpose = str(slot.get("purpose") or "").lower()
    if any(w in purpose for w in ("conflict", "tension", "gap", "limit", "caution", "caveat")):
        return "conflict"
    if any(w in purpose for w in ("method", "population", "setting", "design")):
        return "methodology"
    if any(w in purpose for w in ("theme", "overview", "recurring", "synthesize")):
        return "themes"
    if any(w in purpose for w in ("chronolog", "timeline", "year", "histor")):
        return "chronology"
    return "consensus"


def _allocate_for_facet(
    facet: str,
    *,
    supporting: list[dict[str, Any]],
    argument: dict[str, Any],
    by_id: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not supporting:
        return []

    if facet == "themes":
        ids: list[int] = []
        for cluster in argument.get("theme_clusters") or []:
            ids.extend(int(x) for x in (cluster.get("evidence_ids") or [])[:2])
        objs = [by_id[i] for i in ids if i in by_id]
        return objs or list(supporting)

    if facet == "consensus":
        ranked = sorted(supporting, key=_conf_rank, reverse=True)
        preferred = [
            o
            for o in ranked
            if str(o.get("confidence_band") or "").lower() in {"high", "moderate"}
        ]
        return preferred or ranked

    if facet == "conflict":
        # Prefer lower-confidence support when conflict is coded; else thin evidence.
        thin = [o for o in supporting if _conf_rank(o) <= 1]
        if argument.get("conflict", {}).get("has_conflict"):
            return thin or list(supporting)
        return thin or list(reversed(sorted(supporting, key=_conf_rank)))

    if facet == "methodology":
        ids = []
        for group in argument.get("methodology") or []:
            ids.extend(int(x) for x in (group.get("evidence_ids") or [])[:3])
        objs = [by_id[i] for i in ids if i in by_id]
        return objs or list(supporting)

    if facet == "chronology":
        ordered = []
        for row in argument.get("chronology") or []:
            eid = row.get("evidence_id")
            if eid is not None and int(eid) in by_id:
                ordered.append(by_id[int(eid)])
        return ordered or list(supporting)

    return list(supporting)


def build_section_contexts(
    *,
    plan: dict[str, Any],
    supporting: list[dict[str, Any]],
    consensus: dict[str, Any] | None,
    conflict: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Allocate supporting objects across plan slots using a structured argument.

    Does not invent EvidenceObjects. Empty support → empty contexts (gate handles block).
    """
    slots = list(plan.get("slots") or [])
    if not slots:
        return []

    argument = build_structured_argument(
        supporting=supporting, consensus=consensus, conflict=conflict
    )
    by_id = {int(o["id"]): o for o in supporting if o.get("id") is not None}
    label = (consensus or {}).get("label") or "none"
    mediators = list((conflict or {}).get("mediators") or [])
    has_conflict = bool((conflict or {}).get("has_conflict"))

    # First pass: facet-based allocation (may overlap across slots — intentional).
    raw_buckets: list[list[dict[str, Any]]] = []
    facets: list[str] = []
    for slot in slots:
        facet = _facet_for_slot(slot)
        facets.append(facet)
        allocated = _allocate_for_facet(
            facet, supporting=supporting, argument=argument, by_id=by_id
        )
        raw_buckets.append(list(allocated))

    # Ensure every supporting id appears in at least one slot when possible.
    covered: set[int] = set()
    for bucket in raw_buckets:
        for o in bucket:
            if o.get("id") is not None:
                covered.add(int(o["id"]))
    missing = [o for o in supporting if o.get("id") is not None and int(o["id"]) not in covered]
    if missing and raw_buckets:
        # Spread leftovers into themes/consensus slots first.
        prefer = [i for i, f in enumerate(facets) if f in {"themes", "consensus"}] or list(
            range(len(raw_buckets))
        )
        for i, obj in enumerate(missing):
            raw_buckets[prefer[i % len(prefer)]].append(obj)

    # Cap per slot so prompts stay bounded (composer also truncates).
    max_per_slot = max(4, (len(supporting) + len(slots) - 1) // max(len(slots), 1) + 2)
    contexts: list[dict[str, Any]] = []
    for i, slot in enumerate(slots):
        objs = raw_buckets[i][:max_per_slot] if i < len(raw_buckets) else []
        # Dedupe preserving order
        seen: set[int] = set()
        deduped: list[dict[str, Any]] = []
        for o in objs:
            eid = o.get("id")
            if eid is None or int(eid) in seen:
                continue
            seen.add(int(eid))
            deduped.append(o)

        contexts.append(
            {
                "slot_id": slot.get("id") or f"slot_{i}",
                "title": slot.get("title") or "",
                "purpose": slot.get("purpose") or "",
                "section_type": plan.get("section_type"),
                "topic": plan.get("topic") or "",
                "facet": facets[i] if i < len(facets) else "consensus",
                "evidence_objects": deduped,
                "evidence_ids": [int(o["id"]) for o in deduped if o.get("id") is not None],
                "consensus_label": label,
                "has_conflict": has_conflict,
                "mediators": mediators,
                "structured_argument": argument,
            }
        )
    return contexts
