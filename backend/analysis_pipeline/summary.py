"""Build compact PromptBuilder / LLM context from persisted Phase 1 JSON."""

from typing import Any, Optional


def build_phase1_prompt_context(phase_results: dict[str, Any], *, max_chars: int = 12_000) -> str:
    """Turn Phase 1 JSON into a single text block for PromptBuilder.

    Prompt Builder remains the LLM consumer; Phase 1.6 AssembledPrompt is
    also available under phase_results['prompt_assembly'] when present.
    """
    parts: list[str] = ["=== Phase 1 Structured Analysis ==="]

    classification = phase_results.get("classification") or {}
    if classification:
        parts.append("## Classification")
        for key in ("document_type", "domain", "study_design", "reporting_guideline"):
            decision = classification.get(key) or {}
            label = decision.get("label")
            conf = decision.get("confidence")
            if label is not None:
                parts.append(f"- {key}: {label} (confidence={conf})")

    context = phase_results.get("analysis_context") or {}
    routing = (context.get("routing_profile") or {}) if context else {}
    if routing:
        parts.append("## Routing")
        parts.append(f"- primary: {routing.get('primary_routing')}")
        parts.append(f"- modules: {routing.get('module_pipeline')}")

    medical = phase_results.get("medical_understanding") or {}
    if medical and not medical.get("skipped"):
        parts.append("## Medical Understanding")
        pico = medical.get("pico_elements") or {}
        if pico:
            pop = pico.get("population") or {}
            if pop.get("description"):
                parts.append(f"- Population: {pop['description']}")
            for interv in pico.get("interventions") or []:
                parts.append(f"- Intervention: {interv.get('name')}")
            for out in pico.get("outcomes") or []:
                parts.append(f"- Outcome: {out.get('name')}")
        entities = medical.get("clinical_entities") or []
        if entities:
            sample = ", ".join(
                f"{e.get('value')} ({e.get('entity_type')})" for e in entities[:12]
            )
            parts.append(f"- Entities: {sample}")

    grades = phase_results.get("evidence_grading") or {}
    if grades and not grades.get("skipped"):
        parts.append("## Evidence Grades")
        overall = grades.get("overall_grade") or {}
        if overall.get("grade_value"):
            parts.append(f"- Overall: {overall.get('grade_value')} (conf={overall.get('confidence')})")
        for name, og in (grades.get("outcome_grades") or {}).items():
            g = (og or {}).get("grade") or {}
            parts.append(f"- Outcome {name}: {g.get('grade_value')} (conf={(og or {}).get('confidence')})")

    prompt_asm = phase_results.get("prompt_assembly") or {}
    if prompt_asm.get("full_prompt"):
        parts.append("## Assembled Research Prompt (excerpt)")
        parts.append(str(prompt_asm["full_prompt"])[:3000])

    graph = phase_results.get("knowledge_graph") or {}
    stats = graph.get("statistics") or {}
    if stats:
        parts.append("## Knowledge Graph")
        parts.append(
            f"- nodes={stats.get('total_nodes')} edges={stats.get('total_edges')} "
            f"avg_degree={stats.get('average_degree')}"
        )

    text = "\n".join(parts)
    if len(text) > max_chars:
        return text[:max_chars] + "\n…[truncated]"
    return text


def classification_domain_hint(phase_results: Optional[dict[str, Any]]) -> Optional[str]:
    """Map Phase 1.2 scientific domain toward Prompt Engine domain keys when obvious."""
    if not phase_results:
        return None
    classification = phase_results.get("classification") or {}
    domain = ((classification.get("domain") or {}).get("label") or "").lower()
    if "medicine" in domain or "health" in domain or "clinical" in domain:
        return "medical"
    if "computer" in domain:
        return "computer_science"
    return None
