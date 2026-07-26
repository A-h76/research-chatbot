"""Phase 1 ``phase_results`` JSON → pure fields for ``RetrievedBundle``.

Input is the persistence JSON object keyed by phase name (same shape as
``analysis_pipeline_results.phase_results``). Output never includes ORM models.
"""

from __future__ import annotations

from typing import Any

from backend.ai_core.context.bundle import RetrievedBundle


def adapt_phase1(phase_results: dict[str, Any] | None) -> RetrievedBundle:
    """Translate Phase 1 JSON into a ``RetrievedBundle`` (other fields empty)."""
    phases = phase_results or {}
    document = _adapt_document(phases.get("document_understanding") or {})
    classification = _adapt_classification(phases.get("classification") or {})
    entities = _adapt_entities(phases.get("medical_understanding") or {})
    evidence = _adapt_evidence(phases.get("evidence_grading") or {})
    graph = _adapt_graph(phases.get("knowledge_graph") or {})
    narrative = _adapt_narrative(phases.get("prompt_assembly") or {})
    passages = _passages_from_document(document)

    return RetrievedBundle(
        document=document,
        classification=classification,
        entities=entities,
        evidence=evidence,
        graph=graph,
        narrative=narrative,
        passages=passages,
        meta={
            "phases_present": sorted(k for k, v in phases.items() if v),
            "adapter": "phase1",
        },
    )


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _adapt_document(du: dict[str, Any]) -> dict[str, Any]:
    meta = _as_dict(du.get("metadata") or du.get("bibliographic") or {})
    doc_meta = du.get("document_metadata")
    doc_meta_d = _as_dict(doc_meta) if isinstance(doc_meta, dict) else {}
    title = meta.get("title") or du.get("title") or doc_meta_d.get("title")
    sections = du.get("sections") or du.get("section_tree") or []
    stats = _as_dict(du.get("statistics") or du.get("document_statistics") or {})
    out: dict[str, Any] = {}
    if title:
        out["title"] = title
    if meta:
        out["metadata"] = {
            k: meta[k]
            for k in ("title", "authors", "year", "venue", "doi", "abstract")
            if meta.get(k) not in (None, "")
        }
    if sections:
        out["sections"] = sections if isinstance(sections, list) else []
    if stats:
        out["statistics"] = stats
    if du.get("warnings"):
        out["warnings"] = list(du["warnings"])
    return out


def _adapt_classification(clf: dict[str, Any]) -> dict[str, Any]:
    if not clf:
        return {}
    out: dict[str, Any] = {}
    for key in ("document_type", "domain", "study_design", "reporting_guideline"):
        decision = clf.get(key)
        if isinstance(decision, dict) and decision.get("label") is not None:
            out[key] = {
                "label": decision.get("label"),
                "confidence": decision.get("confidence"),
            }
        elif decision is not None and not isinstance(decision, dict):
            out[key] = {"label": decision}
    if clf.get("keywords"):
        out["keywords"] = list(clf["keywords"])
    return out


def _adapt_entities(medical: dict[str, Any]) -> list[dict[str, Any]]:
    if not medical or medical.get("skipped"):
        return []
    entities: list[dict[str, Any]] = []
    for i, raw in enumerate(medical.get("clinical_entities") or []):
        if not isinstance(raw, dict):
            continue
        name = raw.get("value") or raw.get("name") or raw.get("display_name")
        if not name:
            continue
        entities.append(
            {
                "id": str(raw.get("id") or f"entity-{i}"),
                "name": str(name),
                "entity_type": raw.get("entity_type") or raw.get("type"),
                "confidence": raw.get("confidence"),
                "source": "medical_understanding.clinical_entities",
            }
        )
    pico = medical.get("pico_elements") or {}
    if isinstance(pico, dict):
        entities.extend(_pico_entities(pico))
    return entities


def _pico_entities(pico: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    pop = pico.get("population") or {}
    if isinstance(pop, dict) and pop.get("description"):
        items.append(
            {
                "id": "pico-population",
                "name": str(pop["description"]),
                "entity_type": "population",
                "source": "medical_understanding.pico",
            }
        )
    for key, ent_type in (
        ("interventions", "intervention"),
        ("comparators", "comparator"),
        ("outcomes", "outcome"),
    ):
        for i, raw in enumerate(pico.get(key) or []):
            if not isinstance(raw, dict):
                continue
            name = raw.get("name") or raw.get("description") or raw.get("value")
            if not name:
                continue
            items.append(
                {
                    "id": f"pico-{ent_type}-{i}",
                    "name": str(name),
                    "entity_type": ent_type,
                    "source": "medical_understanding.pico",
                }
            )
    return items


def _adapt_evidence(grades: dict[str, Any]) -> list[dict[str, Any]]:
    if not grades or grades.get("skipped"):
        return []
    evidence: list[dict[str, Any]] = []
    overall = grades.get("overall_grade") or {}
    if isinstance(overall, dict) and overall.get("grade_value"):
        evidence.append(
            {
                "id": "evidence-overall",
                "label": f"Overall {overall.get('grade_value')}",
                "grade_value": overall.get("grade_value"),
                "confidence": overall.get("confidence"),
                "framework": overall.get("framework") or overall.get("grade_type"),
                "source": "evidence_grading.overall_grade",
            }
        )
    outcome_grades = grades.get("outcome_grades") or {}
    if isinstance(outcome_grades, dict):
        for name, og in outcome_grades.items():
            block = og if isinstance(og, dict) else {}
            g = block.get("grade") if isinstance(block.get("grade"), dict) else block
            grade_value = g.get("grade_value") if isinstance(g, dict) else None
            evidence.append(
                {
                    "id": f"evidence-outcome-{name}",
                    "label": str(name),
                    "grade_value": grade_value,
                    "confidence": block.get("confidence") if isinstance(block, dict) else None,
                    "source": "evidence_grading.outcome_grades",
                }
            )
    frameworks = grades.get("framework_grades") or grades.get("grades_by_framework") or {}
    if isinstance(frameworks, dict):
        for fw, block in frameworks.items():
            if not isinstance(block, dict):
                continue
            g = block.get("grade") if isinstance(block.get("grade"), dict) else block
            if not isinstance(g, dict):
                continue
            if g.get("grade_value") is None:
                continue
            evidence.append(
                {
                    "id": f"evidence-framework-{fw}",
                    "label": str(fw),
                    "grade_value": g.get("grade_value"),
                    "confidence": block.get("confidence"),
                    "framework": str(fw),
                    "source": "evidence_grading.framework",
                }
            )
    return evidence


def _adapt_graph(kg: dict[str, Any]) -> dict[str, Any]:
    if not kg or kg.get("skipped"):
        return {}
    out: dict[str, Any] = {}
    if kg.get("nodes") is not None:
        out["nodes"] = kg["nodes"] if isinstance(kg["nodes"], list) else []
    if kg.get("edges") is not None:
        out["edges"] = kg["edges"] if isinstance(kg["edges"], list) else []
    stats = kg.get("statistics")
    if isinstance(stats, dict):
        out["statistics"] = stats
    return out


def _adapt_narrative(prompt_assembly: dict[str, Any]) -> dict[str, Any]:
    if not prompt_assembly:
        return {}
    out: dict[str, Any] = {}
    if prompt_assembly.get("full_prompt"):
        out["assembled_prompt_excerpt"] = str(prompt_assembly["full_prompt"])[:2000]
    if prompt_assembly.get("summary"):
        out["summary"] = prompt_assembly["summary"]
    return out


def _passages_from_document(document: dict[str, Any]) -> list[dict[str, Any]]:
    passages: list[dict[str, Any]] = []
    for i, section in enumerate(document.get("sections") or []):
        if not isinstance(section, dict):
            continue
        title = section.get("title") or section.get("heading") or f"section-{i}"
        text = section.get("text") or section.get("content") or ""
        if not text and not title:
            continue
        passages.append(
            {
                "id": str(section.get("id") or f"section-{i}"),
                "title": title,
                "text": str(text)[:1500] if text else "",
                "source": "document_understanding.sections",
            }
        )
    return passages
