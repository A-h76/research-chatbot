"""Gateway-backed grounded section composer (Sprint A).

Uses AI Capability Router (ADR-0016) → AI Gateway → AI Ledger for writing /
literature_review research jobs. Falls back to heuristic paste composition if
the gateway is unavailable or returns unusable text.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any, Callable

log = logging.getLogger(__name__)

MARKER_RE = re.compile(r"\[#(\d+)\]")

# Formal prompt versions (job@semver) — reproducible artifacts (ADR-0016).
PROMPT_VERSION_WRITING = "writing@5.4"
PROMPT_VERSION_LIT_REVIEW = "literature_review@2.0"

_SYSTEM = (
    "You are Dhund's grounded literature-review writer (Writing Intelligence v2). "
    "Write ONLY from the EvidenceObjects provided. "
    "You may use the structured Research Intelligence context (themes, consensus, "
    "coverage gaps) only to organize the draft — never invent papers, statistics, "
    "or citations. "
    "Every factual sentence must end with one or more [#id] markers "
    "using only ids from the provided list (example: [#12][#17]). "
    "Do not use markdown headings. Do not wrap the answer in quotes. "
    "If evidence is thin, write cautiously and still cite what exists."
)


def _citations_for_ids(
    ids: list[int], supporting: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_id = {int(o["id"]): o for o in supporting if o.get("id") is not None}
    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for eid in ids:
        if eid in seen or eid not in by_id:
            continue
        seen.add(eid)
        obj = by_id[eid]
        claim = (obj.get("claim") or obj.get("quote") or "").strip()
        out.append(
            {
                "evidence_id": eid,
                "file_id": obj.get("file_id"),
                "page": obj.get("page"),
                "claim": claim,
                "quote": (obj.get("quote") or "")[:500],
                "confidence_band": obj.get("confidence_band"),
                "study_type": obj.get("study_type") or "",
            }
        )
    return out


def _format_evidence_block(objs: list[dict[str, Any]], *, max_claims: int) -> str:
    lines: list[str] = []
    for obj in objs[:max_claims]:
        eid = obj.get("id")
        if eid is None:
            continue
        claim = (obj.get("claim") or obj.get("quote") or "").strip()
        quote = (obj.get("quote") or "").strip()
        page = obj.get("page")
        band = obj.get("confidence_band") or "low"
        st = obj.get("study_type") or ""
        page_bit = f" page={page}" if page is not None else ""
        lines.append(
            f"- id={int(eid)} confidence={band} study_type={st}{page_bit}\n"
            f"  claim: {claim[:500]}\n"
            f"  quote: {quote[:400]}"
        )
    return "\n".join(lines)


def _format_argument(argument: dict[str, Any] | None) -> str:
    if not argument:
        return "(none)"
    themes = argument.get("theme_clusters") or []
    theme_bits = [
        f"{t.get('theme')}→{t.get('evidence_ids')}" for t in themes[:6]
    ]
    consensus = argument.get("consensus") or argument.get("ri_consensus") or {}
    conflict = argument.get("conflict") or {}
    gaps = argument.get("research_gaps") or []
    gap_bits = [
        f"{g.get('type')}:{str(g.get('statement') or '')[:80]}" for g in gaps[:4]
    ]
    methods = argument.get("methodology") or []
    meth_ri = (argument.get("ri_methodology") or {}).get("cards") or []
    meth_bits = [
        f"{m.get('kind')}:{m.get('title')}" for m in meth_ri[:4]
    ] or [
        f"{m.get('study_type')}→{m.get('evidence_ids')}" for m in methods[:6]
    ]
    chrono = argument.get("chronology") or []
    tl = (argument.get("ri_timeline") or {}).get("entries") or []
    chrono_bits = [
        f"{e.get('year')}(n={e.get('evidence_count')})" for e in tl[:6]
    ] or [
        f"{c.get('evidence_id')}@{c.get('year')}" for c in chrono[:8]
    ]
    return (
        f"themes_source: {argument.get('themes_source') or 'unknown'}\n"
        f"themes: {'; '.join(theme_bits) or 'none'}\n"
        f"research_gaps: {'; '.join(gap_bits) or 'none'}\n"
        f"consensus: label={consensus.get('label')} "
        f"product={consensus.get('product_label')} "
        f"supporting={consensus.get('supporting_ids')}\n"
        f"conflict: has_conflict={conflict.get('has_conflict')} "
        f"mediators={conflict.get('mediators')}\n"
        f"methodology: {'; '.join(meth_bits) or 'none'}\n"
        f"timeline: {'; '.join(chrono_bits) or 'none'}"
    )


def extract_allowed_markers(text: str, allowed_ids: set[int]) -> tuple[str, list[int]]:
    """Keep only ``[#id]`` markers in allowed_ids; strip unknown markers."""
    found: list[int] = []
    seen: set[int] = set()

    def repl(match: re.Match[str]) -> str:
        eid = int(match.group(1))
        if eid not in allowed_ids:
            return ""
        if eid not in seen:
            seen.add(eid)
            found.append(eid)
        return f"[#{eid}]"

    cleaned = MARKER_RE.sub(repl, text or "")
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r" *\n[ \t]*", "\n", cleaned).strip()
    return cleaned, found


def _research_job_for_task(task: str):
    from backend.ai.capability_router import ResearchJob

    if (task or "").strip().lower() == "literature_review":
        return ResearchJob.LITERATURE_REVIEW
    return ResearchJob.WRITING


def _prompt_version_for_job(job) -> str:
    from backend.ai.capability_router import ResearchJob

    if job == ResearchJob.LITERATURE_REVIEW:
        return PROMPT_VERSION_LIT_REVIEW
    return PROMPT_VERSION_WRITING


def compose_via_gateway(
    *,
    ai_gateway: Any,
    model_registry: Any,
    query: dict[str, Any],
    supporting: list[dict[str, Any]],
    conflict: dict[str, Any] | None,
    max_claims: int = 5,
    context: dict[str, Any] | None = None,
    mode: str = "balanced",
    user_id: int | None = None,
    task: str = "section_generator",
    project_id: int | None = None,
) -> tuple[str, list[dict[str, Any]], list[str], dict[str, Any] | None]:
    """Gateway synthesis via Capability Router + Ledger.

    Returns ``(paragraph, citations, warnings, provenance_dict_or_none)``.
    Raises on transport/model failure (caller may fallback).
    """
    from backend.ai.ai_ledger import AILedgerEntry, hash_output, record_execution
    from backend.ai.capability_router import resolve_execution
    from backend.ai.capability_router.resolve import execution_policy_from_mode

    ctx = context or {}
    allowed_ids = {int(o["id"]) for o in supporting if o.get("id") is not None}
    if not allowed_ids:
        return "", [], ["No EvidenceObjects for gateway composition."], None

    focus = (query.get("query_text") or "").strip()
    topic = (ctx.get("topic") or focus or "").strip()
    purpose = (ctx.get("purpose") or "").strip()
    title = (ctx.get("title") or "").strip()
    facet = (ctx.get("facet") or "").strip()
    argument = ctx.get("structured_argument")

    user_prompt = (
        f"Section title: {title or '(untitled)'}\n"
        f"Section purpose: {purpose or focus or '(synthesize supporting evidence)'}\n"
        f"Topic: {topic}\n"
        f"Argument facet for this slot: {facet or 'consensus'}\n"
        f"Structured argument:\n{_format_argument(argument)}\n\n"
        f"EvidenceObjects (cite ONLY these ids):\n"
        f"{_format_evidence_block(supporting, max_claims=max_claims)}\n\n"
        "Write 1 short paragraph (3–6 sentences) of literature-review prose. "
        "After each factual sentence, append [#id] markers for the evidence used."
    )
    if (conflict or {}).get("has_conflict"):
        user_prompt += (
            "\nConflict is present; acknowledge tensions only using provided mediators "
            f"and evidence: {list((conflict or {}).get('mediators') or [])}."
        )

    job = _research_job_for_task(task)
    policy = execution_policy_from_mode(mode)
    plan = resolve_execution(job, execution_policy=policy)
    prompt_version = _prompt_version_for_job(job)
    execution_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    evidence_ids = [str(i) for i in sorted(allowed_ids)]

    started = time.perf_counter()
    result = ai_gateway.call(
        model_registry=model_registry,
        task=task,
        mode=mode,
        model=plan.model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        user_id=user_id,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)

    raw = (result or {}).get("content") or ""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("empty_gateway_content")

    cleaned, marker_ids = extract_allowed_markers(raw.strip(), allowed_ids)
    if not marker_ids:
        raise ValueError("no_valid_citation_markers")

    citations = _citations_for_ids(marker_ids, supporting)
    tokens = int((result or {}).get("total_tokens") or 0) or None
    cost = float((result or {}).get("cost") or 0.0)
    # Evidence-first validation signals (not LLM-as-judge).
    evaluation = {
        "citation_markers_ok": True,
        "marker_count": len(marker_ids),
        "schema": "grounded_paragraph_v1",
    }

    entry = AILedgerEntry.from_plan(
        plan,
        prompt_version=prompt_version,
        tools_used=[],
        evidence_source_ids=evidence_ids,
        tokens_in=None,
        tokens_out=tokens,
        cost_usd=cost if cost else None,
        latency_ms=latency_ms,
        output_hash=hash_output(cleaned),
        evaluation=evaluation,
        execution_id=execution_id,
        trace_id=trace_id,
        status="completed",
        extra={
            "user_id": user_id,
            "project_id": project_id,
            "validation_status": "cited",
            "legacy_gateway_task": task,
        },
    )
    record_execution(entry)

    provenance = plan.to_provenance(
        tokens=tokens,
        cost_usd=cost if cost else None,
        duration_ms=latency_ms,
        prompt_version=prompt_version,
        execution_id=execution_id,
    ).to_dict()

    warnings: list[str] = ["gateway_synthesis", "acr_routed"]
    if len(supporting) > max_claims:
        warnings.append(f"Prompt truncated to {max_claims} EvidenceObjects.")
    return cleaned, citations, warnings, provenance


def make_gateway_composer(
    *,
    ai_gateway: Any,
    model_registry: Any,
    mode: str = "balanced",
    user_id: int | None = None,
    task: str = "section_generator",
    project_id: int | None = None,
) -> Callable[..., tuple[str, list[dict[str, Any]], list[str]]]:
    """Return a composer compatible with ``generate_sections`` / Writing Intelligence.

    After runs, inspect ``composer.acr_provenances`` / ``acr_last_provenance`` for
    artifact embedding (ledger remains system of record).
    """

    provenances: list[dict[str, Any]] = []

    def composer(
        *,
        query: dict[str, Any],
        supporting: list[dict[str, Any]],
        conflict: dict[str, Any] | None,
        max_claims: int = 5,
        context: dict[str, Any] | None = None,
        **_: Any,
    ) -> tuple[str, list[dict[str, Any]], list[str]]:
        try:
            paragraph, citations, warnings, provenance = compose_via_gateway(
                ai_gateway=ai_gateway,
                model_registry=model_registry,
                query=query,
                supporting=supporting,
                conflict=conflict,
                max_claims=max_claims,
                context=context,
                mode=mode,
                user_id=user_id,
                task=task,
                project_id=project_id,
            )
            if provenance:
                provenances.append(provenance)
                composer.acr_last_provenance = provenance  # type: ignore[attr-defined]
            return paragraph, citations, warnings
        except Exception as exc:
            log.warning("gateway_composer_fallback reason=%s", str(exc)[:200])
            from backend.evidence.writing_intelligence import compose_grounded_paragraph

            paragraph, citations, warnings = compose_grounded_paragraph(
                query=query,
                supporting=supporting,
                conflict=conflict,
                max_claims=max_claims,
            )
            warnings = list(warnings) + [f"gateway_fallback:{type(exc).__name__}"]
            return paragraph, citations, warnings

    composer.acr_provenances = provenances  # type: ignore[attr-defined]
    composer.acr_last_provenance = None  # type: ignore[attr-defined]
    return composer
