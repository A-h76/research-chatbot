"""Writing Intelligence stage (Phase 2.3 + Milestone 1 + Sprint A).

Generation is LAST: consumes Reasoning (and prior RI stages).
Grounded composition from EvidenceObject claims only — never invents facts/objects.

Pipeline:
  Planner → Context Builder (structured argument) → Section Generator
  → Citation Binder → Research Reviewer → metrics

Sprint A: Gateway synthesis via injectable composer (``make_gateway_composer``);
heuristic ``compose_grounded_paragraph`` remains the fail-closed fallback.
"""

from __future__ import annotations

from typing import Any, Callable

from backend.evidence.writing.citation_binder import bind_citations_to_sections, flatten_bindings
from backend.evidence.writing.context_builder import build_section_contexts
from backend.evidence.writing.metrics import compute_writing_metrics
from backend.evidence.writing.planner import plan_sections
from backend.evidence.writing.reviewer import review_grounded_draft
from backend.evidence.writing.section_generator import generate_sections

WRITING_VERSION = "2.0.0"
WRITING_MODE = "grounded_v1"

DISCLAIMER = (
    "Generated from Evidence Layer objects only; verify against source papers. "
    "Not a substitute for reading the cited evidence. "
    "Writing Intelligence v2 consumes project themes, consensus, and coverage gaps "
    "but never invents literature."
)

_BLOCK_INSUFFICIENT = "insufficient_evidence"
_BLOCK_OPPOSED = "opposed_evidence"
_BLOCK_NO_SUPPORT = "no_supporting_evidence"


def _by_id(objects: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {int(o["id"]): o for o in objects if o.get("id") is not None}


def _supporting_objects(
    objects: list[dict[str, Any]],
    consensus: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Preserve ranking order; prefer consensus supporting_ids."""
    ids = list((consensus or {}).get("supporting_ids") or [])
    index = _by_id(objects)
    if ids:
        return [index[i] for i in ids if i in index]
    out: list[dict[str, Any]] = []
    for obj in objects:
        rel = str(obj.get("relation") or "").lower()
        supports = obj.get("supports") or []
        if rel == "supports" or (isinstance(supports, list) and supports):
            out.append(obj)
    return out


def decide_generation_gate(
    *,
    reasoning: dict[str, Any] | None,
    consensus: dict[str, Any] | None,
    supporting: list[dict[str, Any]],
) -> tuple[str, str | None]:
    """Return (status, blocked_reason). status is ok|blocked."""
    sufficiency = (reasoning or {}).get("sufficiency") or "insufficient"
    summary = (reasoning or {}).get("summary_code") or "insufficient"
    label = (consensus or {}).get("label") or "none"

    if sufficiency == "insufficient" or summary in {"insufficient", "none"} or not supporting:
        if label == "opposed" or summary == "opposed":
            return "blocked", _BLOCK_OPPOSED
        if not supporting:
            return "blocked", _BLOCK_NO_SUPPORT
        return "blocked", _BLOCK_INSUFFICIENT
    if summary == "opposed" or label == "opposed":
        return "blocked", _BLOCK_OPPOSED
    return "ok", None


def compose_grounded_paragraph(
    *,
    query: dict[str, Any],
    supporting: list[dict[str, Any]],
    conflict: dict[str, Any] | None,
    max_claims: int = 5,
    context: dict[str, Any] | None = None,
    **_: Any,
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """Heuristic assemble paragraph + ``[#id]`` markers from EvidenceObjects only."""
    warnings: list[str] = []
    citations: list[dict[str, Any]] = []
    sentences: list[str] = []

    selected_text = ((query.get("anchors") or {}).get("selected_text") or "").strip()
    query_text = (query.get("query_text") or "").strip()
    focus = selected_text or query_text
    ctx = context or {}
    argument = ctx.get("structured_argument") if isinstance(ctx.get("structured_argument"), dict) else {}
    slot_id = str(ctx.get("slot_id") or "").lower()

    chosen = supporting[:max_claims]
    if len(supporting) > max_claims:
        warnings.append(f"Truncated to {max_claims} supporting EvidenceObjects.")

    for obj in chosen:
        claim = (obj.get("claim") or obj.get("quote") or "").strip()
        if not claim:
            continue
        eid = int(obj["id"])
        page = obj.get("page")
        page_bit = f" (page {page})" if page is not None else ""
        # One sentence per claim ending with [#id] so Research Reviewer can verify.
        claim_one = claim.rstrip(".!?")
        sentences.append(f"{claim_one}{page_bit} [#{eid}].")
        citations.append(
            {
                "evidence_id": eid,
                "file_id": obj.get("file_id"),
                "page": page,
                "claim": claim,
                "quote": (obj.get("quote") or "")[:500],
                "confidence_band": obj.get("confidence_band"),
                "study_type": obj.get("study_type") or "",
            }
        )

    if not sentences:
        return "", [], ["No usable claim/quote text on supporting EvidenceObjects."]

    # RI-009: gap / theme framing from structured argument (still Evidence-only body)
    lead = ""
    if slot_id in {"themes", "overview", "covered"} and (argument.get("theme_clusters") or []):
        labels = [
            str(t.get("theme") or "")
            for t in (argument.get("theme_clusters") or [])[:3]
            if t.get("theme")
        ]
        if labels:
            lead = f"Major themes in the evidence include {'; '.join(labels)}."
            warnings.append("Theme framing from RI-001 clusters.")
    if slot_id in {"undercovered", "next_questions", "tensions"} and (
        argument.get("research_gaps") or []
    ):
        gap0 = (argument.get("research_gaps") or [])[0]
        stmt = (gap0.get("statement") or "").strip()
        if stmt:
            lead = f"Coverage note: {stmt[:280]}"
            warnings.append("Gap framing from RI-006 (evidence-anchored).")
        qs = list(gap0.get("suggested_questions") or [])[:1]
        if qs and slot_id == "next_questions":
            lead = (lead + " " if lead else "") + f"Open question suggested by coverage: {qs[0][:200]}"

    # Anchor framing to first citation id so reviewer stays Evidence-first
    if lead and citations:
        lead = f"{lead.rstrip()} [#{int(citations[0]['evidence_id'])}] "

    if focus:
        sentences[0] = f"Regarding “{focus[:240]}”: {lead}{sentences[0]}"
    elif lead:
        sentences[0] = f"{lead}{sentences[0]}"
    else:
        sentences[0] = f"Based on stored evidence, {sentences[0]}"

    paragraph = " ".join(sentences)

    mediators = list((conflict or {}).get("mediators") or [])
    if (conflict or {}).get("has_conflict") and mediators:
        labels = {
            "population_differs": "population",
            "dosage_differs": "dosage",
            "method_differs": "method",
            "outcome_differs": "outcome",
            "timeframe_differs": "timeframe",
            "statistics_differs": "statistics",
        }
        pretty = [labels.get(m, m) for m in mediators]
        marker_tail = " ".join(
            f"[#{int(c['evidence_id'])}]" for c in citations if c.get("evidence_id") is not None
        )
        paragraph += (
            " Conflicting evidence is present; coded differences include: "
            + ", ".join(pretty)
            + f" {marker_tail}."
        )
        warnings.append("Conflict mediators appended; review contradicting EvidenceObjects.")
    elif (conflict or {}).get("has_conflict"):
        marker_tail = " ".join(
            f"[#{int(c['evidence_id'])}]" for c in citations if c.get("evidence_id") is not None
        )
        paragraph += f" Conflicting evidence is present; mediators were not fully coded. {marker_tail}"
        warnings.append("Conflict present without coded mediators.")

    return paragraph.strip(), citations, warnings


def build_writing_intelligence(
    *,
    query: dict[str, Any],
    objects: list[dict[str, Any]],
    reasoning: dict[str, Any] | None,
    consensus: dict[str, Any] | None,
    conflict: dict[str, Any] | None,
    composer: Callable[..., tuple[str, list[dict[str, Any]], list[str]]] | None = None,
    consensus_version: str | None = None,
    conflict_version: str | None = None,
    used_gateway: bool = False,
) -> dict[str, Any]:
    """Research → Writing bridge: RI context → outline → grounded sections → reviewer."""
    from backend.evidence.writing.ri_depth import (
        build_draft_metadata,
        build_ri_writing_context,
        build_theme_outline,
    )

    supporting = _supporting_objects(objects, consensus)
    status, blocked_reason = decide_generation_gate(
        reasoning=reasoning, consensus=consensus, supporting=supporting
    )

    section_type = (query.get("section_type") or "support_sentence").strip().lower()
    topic = (
        ((query.get("anchors") or {}).get("selected_text") or "").strip()
        or (query.get("query_text") or "").strip()
    )
    project_id = (query.get("scope") or {}).get("project_id")

    ri_context = build_ri_writing_context(
        project_id=int(project_id) if project_id is not None else None,
        objects=objects,
        consensus=consensus,
        conflict=conflict,
    )

    payload: dict[str, Any] = {
        "status": status,
        "blocked_reason": blocked_reason,
        "mode": WRITING_MODE,
        "writing_version": WRITING_VERSION,
        "section_type": section_type or "support_sentence",
        "paragraph": None,
        "sections": [],
        "plan": None,
        "outline": [],
        "citations": [],
        "bibliography": [],
        "review": None,
        "warnings": [],
        "disclaimer": DISCLAIMER,
        "supporting_count": len(supporting),
        "metrics": None,
        "ri_context": ri_context,
        "draft_metadata": None,
    }

    if status == "blocked":
        payload["warnings"] = [
            "Generation blocked: Research Intelligence did not find adequate supporting evidence."
        ]
        payload["metrics"] = compute_writing_metrics(
            sections=[], supporting_count=len(supporting), citations=[]
        )
        payload["draft_metadata"] = build_draft_metadata(
            writing_version=WRITING_VERSION,
            ri_context=ri_context,
            citations=[],
            sections=[],
            consensus=consensus,
            conflict=conflict,
            consensus_version=consensus_version,
            conflict_version=conflict_version,
            used_gateway=used_gateway,
        )
        return payload

    fn = composer or compose_grounded_paragraph
    plan = plan_sections(
        section_type=section_type or "support_sentence",
        topic=topic,
        themes=list(ri_context.get("themes") or []),
    )
    contexts = build_section_contexts(
        plan=plan,
        supporting=supporting,
        consensus=consensus,
        conflict=conflict,
        ri_context=ri_context,
    )
    outline = build_theme_outline(plan=plan, contexts=contexts, ri_context=ri_context)
    sections = generate_sections(contexts=contexts, conflict=conflict, composer=fn)
    sections = bind_citations_to_sections(sections=sections, objects=objects)
    payload["outline"] = outline
    payload["plan"] = plan

    ok_sections = [s for s in sections if s.get("status") == "ok" and s.get("paragraph")]
    if not ok_sections:
        payload["status"] = "blocked"
        payload["blocked_reason"] = _BLOCK_NO_SUPPORT
        payload["plan"] = plan
        payload["sections"] = sections
        payload["review"] = review_grounded_draft(
            sections=sections,
            consensus=consensus,
            conflict=conflict,
            supporting_count=len(supporting),
        )
        payload["warnings"] = [
            "Generation blocked: supporting objects lacked claim/quote text."
        ]
        payload["metrics"] = compute_writing_metrics(
            sections=sections,
            supporting_count=len(supporting),
            citations=[],
            review=payload["review"],
        )
        payload["draft_metadata"] = build_draft_metadata(
            writing_version=WRITING_VERSION,
            ri_context=ri_context,
            citations=[],
            sections=sections,
            consensus=consensus,
            conflict=conflict,
            consensus_version=consensus_version,
            conflict_version=conflict_version,
            used_gateway=used_gateway,
        )
        return payload

    # Flat citations (dedupe by evidence_id, preserve order)
    citations: list[dict[str, Any]] = []
    seen: set[int] = set()
    warnings: list[str] = []
    for sec in ok_sections:
        warnings.extend(list(sec.get("warnings") or []))
        for c in sec.get("citations") or []:
            eid = c.get("evidence_id")
            if eid is None or int(eid) in seen:
                continue
            seen.add(int(eid))
            citations.append(c)

    paragraph = "\n\n".join(str(s["paragraph"]) for s in ok_sections)
    bibliography = flatten_bindings(sections)
    review = review_grounded_draft(
        sections=sections, consensus=consensus, conflict=conflict, supporting_count=len(supporting)
    )

    summary = (reasoning or {}).get("summary_code") or ""
    if summary in {"contested", "contested_with_mediators"}:
        warnings.append("Consensus is contested; treat the draft as provisional.")
    if ri_context.get("themes"):
        warnings.append(
            f"RI depth: {len(ri_context['themes'])} theme(s) informed section allocation."
        )
    if ri_context.get("gaps"):
        warnings.append(
            f"RI depth: {len(ri_context['gaps'])} coverage gap(s) available for gap/tension slots."
        )
    if review.get("status") == "fail":
        warnings.append("Reviewer failed: one or more sections lack EvidenceObject bindings.")
    for issue in review.get("issues") or []:
        if issue.get("severity") == "warning":
            warnings.append(str(issue.get("message") or ""))

    payload["paragraph"] = paragraph
    payload["sections"] = sections
    payload["plan"] = plan
    payload["outline"] = outline
    payload["citations"] = citations
    payload["bibliography"] = bibliography
    payload["review"] = review
    payload["warnings"] = [w for w in warnings if w]
    payload["metrics"] = compute_writing_metrics(
        sections=sections,
        supporting_count=len(supporting),
        citations=citations,
        review=review,
    )
    payload["draft_metadata"] = build_draft_metadata(
        writing_version=WRITING_VERSION,
        ri_context=ri_context,
        citations=citations,
        sections=sections,
        consensus=consensus,
        conflict=conflict,
        consensus_version=consensus_version,
        conflict_version=conflict_version,
        used_gateway=used_gateway,
    )
    return payload


def apply_writing_intelligence_stage(
    reasoning_result: dict[str, Any],
    *,
    composer: Callable[..., tuple[str, list[dict[str, Any]], list[str]]] | None = None,
) -> dict[str, Any]:
    """Compose Writing Intelligence on a Reasoning-stage envelope."""
    writing = build_writing_intelligence(
        query=reasoning_result.get("query") or {},
        objects=list(reasoning_result.get("objects") or []),
        reasoning=reasoning_result.get("reasoning"),
        consensus=reasoning_result.get("consensus"),
        conflict=reasoning_result.get("conflict"),
        composer=composer,
        consensus_version=reasoning_result.get("consensus_version"),
        conflict_version=reasoning_result.get("conflict_version"),
        used_gateway=composer is not None,
    )
    return {
        "query": reasoning_result.get("query") or {},
        "objects": list(reasoning_result.get("objects") or []),
        "total": reasoning_result.get("total", 0),
        "truncated": bool(reasoning_result.get("truncated")),
        "stage": "writing",
        "writing_version": WRITING_VERSION,
        "writing": writing,
        "reasoning": reasoning_result.get("reasoning"),
        "reasoning_version": reasoning_result.get("reasoning_version"),
        "conflict": reasoning_result.get("conflict"),
        "conflict_version": reasoning_result.get("conflict_version"),
        "consensus": reasoning_result.get("consensus"),
        "consensus_version": reasoning_result.get("consensus_version"),
        "ranking_version": reasoning_result.get("ranking_version"),
        "ranking_strategy": reasoning_result.get("ranking_strategy"),
        "retrieval_version": reasoning_result.get("retrieval_version"),
    }
