"""Scientific entities profile (Paper Analysis 2.6 / SUE).

Paper-scoped entities + local relations projected from already-extracted
methodology / statistics profiles (and optional medical PICO when present).

Never invents entities — only lifts filled profile fields.
Paper Graph stays file-scoped JSON elsewhere; this profile is the Entities-tab
bridge for non-medical papers (0 extra LLM).
"""

from __future__ import annotations

import re
from typing import Any, Optional

SCHEMA_VERSION = "1.0.0"
_MAX_ENTITIES = 40
_MAX_RELATIONS = 24
_MAX_TEXT = 300


def extract_scientific_entities_profile(
    document_payload: dict[str, Any],
    *,
    medical: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build scientific_entities_profile from DU profiles (+ optional medical)."""
    methodology = document_payload.get("methodology_profile")
    statistics = document_payload.get("statistics_profile")
    if not isinstance(methodology, dict):
        methodology = {}
    if not isinstance(statistics, dict):
        statistics = {}

    entities: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _add(
        *,
        value: str,
        entity_type: str,
        source: str,
        confidence: float,
        text: str = "",
        label: Optional[str] = None,
    ) -> None:
        v = _clip(value)
        if len(v) < 2:
            return
        key = f"{entity_type}:{v.lower()}"
        if key in seen:
            return
        seen.add(key)
        entities.append(
            {
                "value": v,
                "entity_type": entity_type,
                "label": label or v,
                "text": _clip(text or v),
                "source": source,
                "confidence": round(min(max(confidence, 0.0), 0.95), 2),
                "author_stated": True,
            }
        )

    # --- Methodology projection ---
    _from_field(methodology.get("study_design"), "method", "methodology_profile", _add)
    _from_field(methodology.get("experimental_setup"), "method", "methodology_profile", _add)
    _from_field(methodology.get("dataset"), "dataset", "methodology_profile", _add)
    _from_field(methodology.get("population"), "population", "methodology_profile", _add)
    _from_field(methodology.get("intervention"), "intervention", "methodology_profile", _add)
    _from_field(methodology.get("controls"), "comparator", "methodology_profile", _add)
    _from_field(methodology.get("sample_size"), "sample_size", "methodology_profile", _add)

    for item in methodology.get("metrics") or []:
        _from_field(item, "metric", "methodology_profile", _add)
    for item in methodology.get("variables") or []:
        _from_field(item, "variable", "methodology_profile", _add)

    # --- Statistics projection ---
    for item in statistics.get("tests") or []:
        _from_field(item, "statistic", "statistics_profile", _add, prefer_label=True)
    for item in statistics.get("effect_sizes") or []:
        _from_field(item, "statistic", "statistics_profile", _add)
    for item in statistics.get("metrics") or []:
        _from_field(item, "metric", "statistics_profile", _add)

    # --- Optional medical enrich (when phase ran) ---
    if isinstance(medical, dict) and not medical.get("skipped"):
        _from_medical(medical, _add)

    entities = entities[:_MAX_ENTITIES]
    relations = _local_relations(entities)[:_MAX_RELATIONS]

    return {
        "schema_version": SCHEMA_VERSION,
        "entities": entities,
        "relations": relations,
        "has_content": bool(entities),
        "entity_count": len(entities),
        "relation_count": len(relations),
        "by_type": _count_by_type(entities),
    }


def _from_field(
    raw: Any,
    entity_type: str,
    source: str,
    add_fn,
    *,
    prefer_label: bool = False,
) -> None:
    if raw is None:
        return
    if isinstance(raw, list):
        for item in raw:
            _from_field(item, entity_type, source, add_fn, prefer_label=prefer_label)
        return
    text = ""
    label = None
    conf = 0.75
    if isinstance(raw, dict):
        label = raw.get("label")
        text = str(raw.get("text") or raw.get("value") or label or "").strip()
        try:
            conf = float(raw.get("confidence") or conf)
        except (TypeError, ValueError):
            conf = 0.75
    elif isinstance(raw, str):
        text = raw.strip()
    if not text:
        return
    value = str(label).replace("_", " ").strip() if prefer_label and label else text
    if prefer_label and label:
        value = str(label).replace("_", " ").strip() or text
    add_fn(
        value=value,
        entity_type=entity_type,
        source=source,
        confidence=conf,
        text=text,
        label=str(label).replace("_", " ") if label else None,
    )


def _from_medical(medical: dict[str, Any], add_fn) -> None:
    pico = medical.get("pico_elements") or medical.get("pico") or {}
    if isinstance(pico, dict):
        for key, etype in (
            ("population", "population"),
            ("intervention", "intervention"),
            ("comparator", "comparator"),
            ("outcome", "outcome"),
        ):
            _from_field(pico.get(key), etype, "medical_understanding", add_fn)

    for ent in medical.get("clinical_entities") or []:
        if not isinstance(ent, dict):
            continue
        et = str(ent.get("entity_type") or "other").lower()
        val = str(ent.get("value") or ent.get("raw_text") or "").strip()
        if not val:
            continue
        try:
            conf = float(ent.get("confidence") or 0.7)
        except (TypeError, ValueError):
            conf = 0.7
        add_fn(
            value=val,
            entity_type=et if et else "other",
            source="medical_understanding",
            confidence=conf,
            text=str(ent.get("raw_text") or val),
        )


def _local_relations(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Emit local edges only when both ends exist — invent-nothing."""
    by_type: dict[str, list[dict[str, Any]]] = {}
    for e in entities:
        by_type.setdefault(str(e.get("entity_type") or "other"), []).append(e)

    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _rel(subj: dict[str, Any], predicate: str, obj: dict[str, Any]) -> None:
        s = str(subj.get("value") or "")
        o = str(obj.get("value") or "")
        if not s or not o or s.lower() == o.lower():
            return
        key = f"{s.lower()}|{predicate}|{o.lower()}"
        if key in seen:
            return
        seen.add(key)
        out.append(
            {
                "subject": s,
                "predicate": predicate,
                "object": o,
                "confidence": round(
                    min(
                        float(subj.get("confidence") or 0.7),
                        float(obj.get("confidence") or 0.7),
                    ),
                    2,
                ),
                "source": "scientific_entities_profile",
            }
        )

    methods = by_type.get("method") or []
    datasets = by_type.get("dataset") or []
    metrics = by_type.get("metric") or []
    interventions = by_type.get("intervention") or []
    outcomes = [*(by_type.get("outcome") or []), *(by_type.get("metric") or [])]
    populations = by_type.get("population") or []
    statistics = by_type.get("statistic") or []

    for m in methods[:3]:
        for d in datasets[:3]:
            _rel(m, "uses", d)
        for met in metrics[:4]:
            _rel(m, "measures", met)
        for st in statistics[:4]:
            _rel(m, "reports", st)

    for inter in interventions[:3]:
        for outc in outcomes[:4]:
            _rel(inter, "targets", outc)
        for pop in populations[:2]:
            _rel(inter, "applied_to", pop)

    return out


def _count_by_type(entities: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for e in entities:
        t = str(e.get("entity_type") or "other")
        counts[t] = counts.get(t, 0) + 1
    return counts


def _clip(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(text) <= _MAX_TEXT:
        return text
    return text[: _MAX_TEXT - 1].rstrip() + "…"
