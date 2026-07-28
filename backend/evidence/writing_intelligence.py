"""Writing Intelligence stage (Phase 2.3 Sprint 6).

Generation is LAST: consumes Reasoning (and prior RI stages).
Grounded composition from EvidenceObject claims only — never invents facts/objects.
LLM narration may wrap this later; Sprint 6 ships deterministic grounded_v0.
"""

from __future__ import annotations

from typing import Any, Callable

WRITING_VERSION = "1.0.0"
WRITING_MODE = "grounded_v0"

DISCLAIMER = (
    "Generated from Evidence Layer objects only; verify against source papers. "
    "Not a substitute for reading the cited evidence."
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
    # Fallback: objects with relation supports or non-empty supports array
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
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """Assemble paragraph + citations from supporting EvidenceObjects only."""
    warnings: list[str] = []
    citations: list[dict[str, Any]] = []
    sentences: list[str] = []

    selected_text = ((query.get("anchors") or {}).get("selected_text") or "").strip()
    query_text = (query.get("query_text") or "").strip()
    focus = selected_text or query_text

    chosen = supporting[:max_claims]
    if len(supporting) > max_claims:
        warnings.append(f"Truncated to {max_claims} supporting EvidenceObjects.")

    for obj in chosen:
        claim = (obj.get("claim") or obj.get("quote") or "").strip()
        if not claim:
            continue
        page = obj.get("page")
        page_bit = f" (p. {page})" if page is not None else ""
        sentences.append(f"{claim}{page_bit}")
        citations.append(
            {
                "evidence_id": int(obj["id"]),
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

    if focus:
        lead = f"Regarding “{focus[:240]}”: "
    else:
        lead = "Based on stored evidence: "

    body = " ".join(sentences)
    paragraph = f"{lead}{body}"

    mediators = list((conflict or {}).get("mediators") or [])
    if (conflict or {}).get("has_conflict") and mediators:
        labels = {
            "population_differs": "population",
            "dosage_differs": "dosage",
            "method_differs": "method",
            "outcome_differs": "outcome",
        }
        pretty = [labels.get(m, m) for m in mediators]
        paragraph += (
            " Conflicting evidence is present; coded differences include: "
            + ", ".join(pretty)
            + "."
        )
        warnings.append("Conflict mediators appended; review contradicting EvidenceObjects.")
    elif (conflict or {}).get("has_conflict"):
        paragraph += " Conflicting evidence is present; mediators were not fully coded."
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
) -> dict[str, Any]:
    """Generation step — only after reasoning gates pass."""
    supporting = _supporting_objects(objects, consensus)
    status, blocked_reason = decide_generation_gate(
        reasoning=reasoning, consensus=consensus, supporting=supporting
    )

    payload: dict[str, Any] = {
        "status": status,
        "blocked_reason": blocked_reason,
        "mode": WRITING_MODE,
        "paragraph": None,
        "citations": [],
        "warnings": [],
        "disclaimer": DISCLAIMER,
        "supporting_count": len(supporting),
    }

    if status == "blocked":
        payload["warnings"] = [
            "Generation blocked: Research Intelligence did not find adequate supporting evidence."
        ]
        return payload

    fn = composer or compose_grounded_paragraph
    paragraph, citations, warnings = fn(
        query=query, supporting=supporting, conflict=conflict
    )
    if not paragraph or not citations:
        payload["status"] = "blocked"
        payload["blocked_reason"] = _BLOCK_NO_SUPPORT
        payload["warnings"] = warnings or [
            "Generation blocked: supporting objects lacked claim/quote text."
        ]
        return payload

    # Contested: allow generation but warn (still grounded)
    summary = (reasoning or {}).get("summary_code") or ""
    if summary in {"contested", "contested_with_mediators"}:
        warnings.append("Consensus is contested; treat the draft as provisional.")

    payload["paragraph"] = paragraph
    payload["citations"] = citations
    payload["warnings"] = warnings
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
