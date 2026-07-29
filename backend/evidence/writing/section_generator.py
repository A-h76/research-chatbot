"""Section Generator — write grounded paragraphs for each context slot."""

from __future__ import annotations

from typing import Any, Callable

Composer = Callable[..., tuple[str, list[dict[str, Any]], list[str]]]


def _band_confidence(objs: list[dict[str, Any]]) -> str:
    order = {"high": 3, "moderate": 2, "low": 1}
    best = 0
    label = "low"
    for obj in objs:
        band = str(obj.get("confidence_band") or "low").lower()
        score = order.get(band, 0)
        if score > best:
            best = score
            label = band
    return label if objs else "none"


def generate_sections(
    *,
    contexts: list[dict[str, Any]],
    conflict: dict[str, Any] | None,
    composer: Composer,
    attach_conflict_on_last: bool = True,
) -> list[dict[str, Any]]:
    """Produce one grounded section payload per context (ids from objects only)."""
    sections: list[dict[str, Any]] = []
    last_idx = len(contexts) - 1

    for i, ctx in enumerate(contexts):
        objs = list(ctx.get("evidence_objects") or [])
        topic = (ctx.get("topic") or "").strip()
        purpose = (ctx.get("purpose") or "").strip()
        title = ctx.get("title") or ""

        # Synthetic query so composer lead-in reflects the section purpose.
        focus = purpose or topic
        query = {
            "query_text": focus,
            "anchors": {"selected_text": topic[:2000] if topic else ""},
        }

        # Only append conflict note on the last slot to avoid repetition.
        conflict_arg = conflict if (attach_conflict_on_last and i == last_idx) else {
            "has_conflict": False,
            "mediators": [],
        }

        if not objs:
            sections.append(
                {
                    "id": ctx.get("slot_id"),
                    "title": title,
                    "purpose": purpose,
                    "paragraph": None,
                    "citations": [],
                    "evidence_ids": [],
                    "confidence": "none",
                    "status": "empty",
                    "warnings": ["No EvidenceObjects allocated to this section slot."],
                }
            )
            continue

        paragraph, citations, warnings = composer(
            query=query,
            supporting=objs,
            conflict=conflict_arg,
            max_claims=4,
            context=ctx,
        )
        # Prefixed heading line for multi-section drafts (readable insert).
        headed = f"**{title}.** {paragraph}" if paragraph and title else paragraph

        sections.append(
            {
                "id": ctx.get("slot_id"),
                "title": title,
                "purpose": purpose,
                "paragraph": headed,
                "citations": citations,
                "evidence_ids": list(ctx.get("evidence_ids") or []),
                "confidence": _band_confidence(objs),
                "status": "ok" if paragraph and citations else "empty",
                "warnings": warnings,
            }
        )

    return sections
