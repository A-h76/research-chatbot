"""Persist web sources + structured references in Message.sources (W1).

Backward compatible:
- Legacy rows: JSON list of web sources
- New rows: ``{"web": [...], "references": [...], "scope": {...}}``
"""

from __future__ import annotations

import json
from typing import Any, Optional


def dump_message_sources(
    *,
    web: Optional[list[dict[str, Any]]] = None,
    references: Optional[list[dict[str, Any]]] = None,
    scope: Optional[dict[str, Any]] = None,
    grounding: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    web = web or []
    references = references or []
    if not web and not references and not scope and not grounding:
        return None
    # Legacy-only shape when no structured refs (keeps old clients happy).
    if not references and not scope and not grounding:
        return json.dumps(web) if web else None
    payload: dict[str, Any] = {"web": web, "references": references}
    if scope:
        payload["scope"] = scope
    if grounding:
        payload["grounding"] = grounding
    return json.dumps(payload)


def load_message_sources(
    raw: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    """Return (web, references, scope, grounding)."""
    if raw is None or raw == "":
        return [], [], None, None
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except Exception:
            return [], [], None, None
    else:
        data = raw

    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)], [], None, None

    if isinstance(data, dict):
        web = data.get("web")
        refs = data.get("references")
        scope = data.get("scope") if isinstance(data.get("scope"), dict) else None
        grounding = data.get("grounding") if isinstance(data.get("grounding"), dict) else None
        web_list = [x for x in web if isinstance(x, dict)] if isinstance(web, list) else []
        ref_list = [x for x in refs if isinstance(x, dict)] if isinstance(refs, list) else []
        if not web_list and not ref_list and ("url" in data or "title" in data):
            return [data], [], None, None
        return web_list, ref_list, scope, grounding

    return [], [], None, None


def normalize_sources_for_api(raw: Any) -> dict[str, Any]:
    """API message shape: sources (web) + references + optional scope/grounding."""
    web, references, scope, grounding = load_message_sources(raw)
    out: dict[str, Any] = {"sources": web, "references": references}
    if scope:
        out["scope"] = scope
    if grounding:
        out["grounding"] = grounding
        if "confidence" in grounding:
            out["confidence"] = grounding.get("confidence")
        warnings = grounding.get("warnings")
        if isinstance(warnings, list):
            out["warnings"] = [str(w) for w in warnings if w]
        skill = grounding.get("skill")
        if skill:
            out["skill"] = skill
    return out
