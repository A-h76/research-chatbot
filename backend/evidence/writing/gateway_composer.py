"""Gateway-backed grounded section composer (Sprint A).

Uses AI Gateway task ``section_generator`` / ``literature_review`` with
EvidenceObject-only context. Requires in-text ``[#id]`` markers. Falls back to
heuristic paste composition if the gateway is unavailable or returns unusable text.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable

log = logging.getLogger(__name__)

MARKER_RE = re.compile(r"\[#(\d+)\]")

_SYSTEM = (
    "You are Dhund's grounded literature-review writer. "
    "Write ONLY from the EvidenceObjects provided. "
    "Do not invent facts, studies, statistics, or citations. "
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
    consensus = argument.get("consensus") or {}
    conflict = argument.get("conflict") or {}
    methods = argument.get("methodology") or []
    chrono = argument.get("chronology") or []
    return (
        f"themes: {'; '.join(theme_bits) or 'none'}\n"
        f"consensus: label={consensus.get('label')} "
        f"supporting={consensus.get('supporting_ids')}\n"
        f"conflict: has_conflict={conflict.get('has_conflict')} "
        f"mediators={conflict.get('mediators')}\n"
        f"methodology: "
        + ", ".join(
            f"{m.get('study_type')}→{m.get('evidence_ids')}" for m in methods[:6]
        )
        + "\n"
        f"chronology: "
        + ", ".join(
            f"{c.get('evidence_id')}@{c.get('year')}" for c in chrono[:8]
        )
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
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """Gateway synthesis. Raises on transport/model failure (caller may fallback)."""
    ctx = context or {}
    allowed_ids = {int(o["id"]) for o in supporting if o.get("id") is not None}
    if not allowed_ids:
        return "", [], ["No EvidenceObjects for gateway composition."]

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

    result = ai_gateway.call(
        model_registry=model_registry,
        task=task,
        mode=mode,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        user_id=user_id,
    )
    raw = (result or {}).get("content") or ""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("empty_gateway_content")

    cleaned, marker_ids = extract_allowed_markers(raw.strip(), allowed_ids)
    if not marker_ids:
        raise ValueError("no_valid_citation_markers")

    citations = _citations_for_ids(marker_ids, supporting)
    warnings: list[str] = ["gateway_synthesis"]
    if len(supporting) > max_claims:
        warnings.append(f"Prompt truncated to {max_claims} EvidenceObjects.")
    return cleaned, citations, warnings


def make_gateway_composer(
    *,
    ai_gateway: Any,
    model_registry: Any,
    mode: str = "balanced",
    user_id: int | None = None,
    task: str = "section_generator",
) -> Callable[..., tuple[str, list[dict[str, Any]], list[str]]]:
    """Return a composer compatible with ``generate_sections`` / Writing Intelligence."""

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
            return compose_via_gateway(
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
            )
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

    return composer
