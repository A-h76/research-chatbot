"""Inspectable quality assessment (Paper Analysis 2.7 / SUE).

Deterministic checklist over already-stored SUE profiles (methodology,
statistics, limitations/novelty, scientific entities). Explains *why*
with ✓ / • / — items — never an opaque numeric score like 8.9/10.

Cost: pure aggregation; 0 extra LLM / PDF parse.
"""

from __future__ import annotations

from typing import Any, Optional

SCHEMA_VERSION = "1.0.0"

# Categorical bands only — not a continuous score for UI headline.
_BANDS = ("strong", "partial", "weak", "unknown")


def extract_quality_assessment_profile(document_payload: dict[str, Any]) -> dict[str, Any]:
    """Build quality_assessment_profile from additive SUE profiles on DU."""
    methodology = _as_dict(document_payload.get("methodology_profile"))
    statistics = _as_dict(document_payload.get("statistics_profile"))
    limitations = _as_dict(document_payload.get("limitations_novelty_profile"))
    entities = _as_dict(document_payload.get("scientific_entities_profile"))

    sections = [
        _methodology_section(methodology, entities),
        _evidence_section(statistics, methodology, entities),
        _limitations_section(limitations),
        _availability_section(methodology),
    ]

    has_content = any(s.get("items") for s in sections) or any(
        s.get("band") != "unknown" for s in sections
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "sections": sections,
        "has_content": has_content,
        # Explicit non-goal: no overall_score / stars / 8.9/10.
        "scoring": "inspectable_checklist",
    }


def _methodology_section(methodology: dict[str, Any], entities: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []

    design = methodology.get("study_design")
    if _filled(design):
        label = _label(design) or _text(design)
        items.append(
            _item(
                "pass",
                label.replace("_", " "),
                source="methodology_profile",
                reason="Study design extracted from methods/classification",
            )
        )
    else:
        items.append(
            _item(
                "missing",
                "Study design not reliably extractable",
                source="methodology_profile",
                reason="No study_design signal in methodology profile",
            )
        )

    if _filled(methodology.get("sample_size")) or _entity_type(entities, "sample_size"):
        items.append(
            _item(
                "pass",
                _text(methodology.get("sample_size")) or "Sample size reported",
                source="methodology_profile",
                reason="Sample size field present",
            )
        )
    elif _filled(methodology.get("population")):
        items.append(
            _item(
                "note",
                "Population described; sample size not extracted",
                source="methodology_profile",
                reason="population present without sample_size",
            )
        )

    if _filled(methodology.get("dataset")) or _entity_type(entities, "dataset"):
        items.append(
            _item(
                "pass",
                _text(methodology.get("dataset")) or "Dataset identified",
                source="methodology_profile",
                reason="Dataset field present",
            )
        )

    if methodology.get("metrics") or _entity_type(entities, "metric"):
        items.append(
            _item(
                "pass",
                "Evaluation metrics reported",
                source="methodology_profile",
                reason="One or more metrics present",
            )
        )

    if _filled(methodology.get("controls")):
        items.append(
            _item(
                "pass",
                "Controls / comparison group described",
                source="methodology_profile",
                reason="controls field present",
            )
        )

    pass_n = sum(1 for i in items if i["status"] == "pass")
    missing_design = any(
        i["status"] == "missing" and "design" in i["text"].lower() for i in items
    )
    band = _band_from_counts(pass_n, missing_critical=missing_design, total_signals=max(pass_n, 1))

    return {
        "id": "methodology",
        "label": "Methodology",
        "band": band,
        "items": items,
    }


def _evidence_section(
    statistics: dict[str, Any],
    methodology: dict[str, Any],
    entities: dict[str, Any],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []

    if _filled(methodology.get("sample_size")):
        text = _text(methodology.get("sample_size"))
        # Light heuristic for "large sample" — only when N is explicit and >= 100.
        n_label = None
        if isinstance(methodology.get("sample_size"), dict):
            n_label = methodology["sample_size"].get("label")
        try:
            n = int(str(n_label).replace(",", "")) if n_label else None
        except (TypeError, ValueError):
            n = None
        if n is not None and n >= 100:
            items.append(
                _item(
                    "pass",
                    f"Large sample ({text})",
                    source="methodology_profile",
                    reason=f"sample_size label N={n} ≥ 100",
                )
            )
        else:
            items.append(
                _item(
                    "note",
                    f"Sample size reported ({text})",
                    source="methodology_profile",
                    reason="sample_size present; not classified as large",
                )
            )

    if statistics.get("tests") or _entity_type(entities, "statistic"):
        items.append(
            _item(
                "pass",
                "Statistical analysis reported",
                source="statistics_profile",
                reason="Named tests or statistic entities present",
            )
        )
    if statistics.get("p_values"):
        items.append(
            _item(
                "pass",
                "P-values explicitly reported",
                source="statistics_profile",
                reason="p_values list non-empty",
            )
        )
    if statistics.get("confidence_intervals"):
        items.append(
            _item(
                "pass",
                "Confidence intervals reported",
                source="statistics_profile",
                reason="confidence_intervals list non-empty",
            )
        )
    if statistics.get("effect_sizes"):
        items.append(
            _item(
                "pass",
                "Effect sizes reported",
                source="statistics_profile",
                reason="effect_sizes list non-empty",
            )
        )
    for interp in (statistics.get("interpretations") or [])[:2]:
        if isinstance(interp, dict) and interp.get("author_stated"):
            items.append(
                _item(
                    "note",
                    _text(interp),
                    source="statistics_profile",
                    reason="Author-stated statistical interpretation",
                )
            )

    if not items:
        items.append(
            _item(
                "missing",
                "No explicit statistical findings extracted",
                source="statistics_profile",
                reason="statistics_profile empty or weak",
            )
        )

    pass_n = sum(1 for i in items if i["status"] == "pass")
    band = _band_from_counts(
        pass_n,
        missing_critical=any(i["status"] == "missing" for i in items) and pass_n == 0,
        total_signals=max(pass_n, 1),
    )

    return {
        "id": "evidence",
        "label": "Evidence",
        "band": band,
        "items": items,
    }


def _limitations_section(limitations: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for lim in (limitations.get("limitations") or [])[:6]:
        if not isinstance(lim, dict):
            continue
        if lim.get("author_stated") is False:
            continue
        text = _text(lim)
        if not text:
            continue
        items.append(
            _item(
                "note",
                text,
                source="limitations_novelty_profile",
                reason="Author-stated limitation",
            )
        )

    if not items:
        items.append(
            _item(
                "missing",
                "No author-stated limitations extracted",
                source="limitations_novelty_profile",
                reason="limitations list empty",
            )
        )
        band = "unknown"
    else:
        band = "partial"  # Having limitations listed is informative, not "strong quality"

    return {
        "id": "limitations",
        "label": "Limitations",
        "band": band,
        "items": items,
    }


def _availability_section(methodology: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    code = methodology.get("code_available")
    data = methodology.get("dataset_available")

    if _filled(code):
        label = str((code or {}).get("label") or "").lower() if isinstance(code, dict) else ""
        status = "pass" if label == "available" else "note"
        items.append(
            _item(
                status,
                f"Code · {_text(code)}",
                source="methodology_profile",
                reason="Author-stated code availability",
            )
        )
    else:
        items.append(
            _item(
                "missing",
                "Code availability not stated",
                source="methodology_profile",
                reason="code_available empty",
            )
        )

    if _filled(data):
        label = str((data or {}).get("label") or "").lower() if isinstance(data, dict) else ""
        status = "pass" if label == "available" else "note"
        items.append(
            _item(
                status,
                f"Dataset · {_text(data)}",
                source="methodology_profile",
                reason="Author-stated dataset availability",
            )
        )
    else:
        items.append(
            _item(
                "missing",
                "Dataset availability not stated",
                source="methodology_profile",
                reason="dataset_available empty",
            )
        )

    pass_n = sum(1 for i in items if i["status"] == "pass")
    if pass_n == 2:
        band = "strong"
    elif pass_n == 1:
        band = "partial"
    elif any(i["status"] == "note" for i in items):
        band = "weak"
    else:
        band = "unknown"

    return {
        "id": "availability",
        "label": "Availability",
        "band": band,
        "items": items,
    }


def _band_from_counts(pass_n: int, *, missing_critical: bool, total_signals: int) -> str:
    if missing_critical and pass_n == 0:
        return "unknown"
    if pass_n >= 3:
        return "strong"
    if pass_n >= 1:
        return "partial"
    if total_signals == 0:
        return "unknown"
    return "weak"


def _item(status: str, text: str, *, source: str, reason: str) -> dict[str, Any]:
    return {
        "status": status,  # pass | note | missing
        "text": (text or "").strip()[:400],
        "source": source,
        "reason": reason,
    }


def _as_dict(v: Any) -> dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _filled(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, dict):
        return bool(str(v.get("text") or v.get("label") or v.get("value") or "").strip())
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, list):
        return len(v) > 0
    return bool(v)


def _text(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, dict):
        return str(v.get("text") or v.get("label") or v.get("value") or "").strip()
    return str(v).strip()


def _label(v: Any) -> str:
    if isinstance(v, dict):
        return str(v.get("label") or "").strip()
    return ""


def _entity_type(entities: dict[str, Any], entity_type: str) -> bool:
    for e in entities.get("entities") or []:
        if isinstance(e, dict) and str(e.get("entity_type") or "").lower() == entity_type:
            return True
    return False
