"""Scientific Structure profile (Paper Analysis 2.1 / SUE).

Additive, heuristic extraction of framing fields from Phase 1.1
document_understanding output. Never invents — empty lists / null when
signals are weak.

Cost: pure regex/string work over already-extracted abstract + section
text (no extra LLM, no re-parse of the PDF).
"""

from __future__ import annotations

import re
from typing import Any, Optional

SCHEMA_VERSION = "1.0.0"

# Minimum confidence to keep a hit (honest empty preferred over noise).
_MIN_CONF = 0.55
_MAX_ITEMS = 5
_MAX_TEXT = 500

_CORE_SECTIONS = (
    "abstract",
    "introduction",
    "methods",
    "results",
    "discussion",
    "references",
    "acknowledgments",
    "appendix",
)

# Dedicated heading titles (raw) that often hold framing content.
_HEADING_OBJECTIVES = re.compile(
    r"^\s*(?:\d+[\.\)]\s*)?(objectives?|aims?(?:\s+and\s+objectives)?|study\s+aims?)\s*$",
    re.I,
)
_HEADING_RQ = re.compile(
    r"^\s*(?:\d+[\.\)]\s*)?(research\s+questions?|questions?)\s*$",
    re.I,
)
_HEADING_HYP = re.compile(
    r"^\s*(?:\d+[\.\)]\s*)?(hypothes[ei]s|null\s+hypothes[ei]s)\s*$",
    re.I,
)
_HEADING_PROBLEM = re.compile(
    r"^\s*(?:\d+[\.\)]\s*)?(problem\s+statement|problem\s+definition)\s*$",
    re.I,
)

# In-prose patterns — keep conservative.
_OBJ_SENT = re.compile(
    r"(?P<sent>[^.!?\n]{0,80}?\b(?:the\s+)?(?:primary\s+|main\s+)?"
    r"(?:aim|aims|aimed|objective|objectives|purpose)\b[^.!?\n]{8,350}[.!?])",
    re.I,
)
_RQ_SENT = re.compile(
    r"(?P<sent>(?:(?:the\s+)?(?:primary\s+)?research\s+question(?:s)?\s*(?:is|are|was|were)?[:\s]+|"
    r"we\s+(?:ask|asked|investigate|investigated)\s*(?:whether|if|how|what)?\s*)"
    r"[^.!?\n?]{15,350}\?)",
    re.I,
)
_RQ_MARKED = re.compile(
    r"(?:^|\n)\s*(?:RQ\s*\d+|Research\s+Question\s*\d*)[:.\s]+(?P<q>[^\n?]{15,350}\?)",
    re.I,
)
_HYP_SENT = re.compile(
    r"(?P<sent>[^.!?\n]{0,80}?\b(?:we\s+)?hypothes(?:i[sz]e|i[sz]ed|is|es)\b[^.!?\n]{8,300}[.!?])",
    re.I,
)
_PROBLEM_SENT = re.compile(
    r"(?P<sent>[^.!?\n]{0,100}?\b(?:little\s+is\s+known|poorly\s+understood|"
    r"remains?\s+unclear|knowledge\s+gap|this\s+problem)\b[^.!?\n]{8,280}[.!?])",
    re.I,
)


def extract_scientific_structure(document_payload: dict[str, Any]) -> dict[str, Any]:
    """Build scientific_structure from a serialized document_understanding dict."""
    metadata = document_payload.get("metadata") or {}
    structure = document_payload.get("structure") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    if not isinstance(structure, dict):
        structure = {}

    abstract = str(metadata.get("abstract") or "").strip()
    section_texts = _collect_section_texts(structure)
    intro = section_texts.get("introduction") or ""
    # Prefer dedicated framing headings over scanning whole paper.
    heading_hits = _from_dedicated_headings(structure)

    objectives = list(heading_hits["objectives"])
    research_questions = list(heading_hits["research_questions"])
    hypotheses = list(heading_hits["hypotheses"])
    problem = heading_hits.get("problem_statement")

    # Abstract + introduction prose (high signal, low cost).
    corpus_parts = []
    if abstract:
        corpus_parts.append(("abstract", abstract, 0.72))
    if intro:
        corpus_parts.append(("introduction", intro[:6000], 0.65))

    for source, text, base_conf in corpus_parts:
        if len(objectives) < _MAX_ITEMS:
            objectives.extend(_extract_pattern(text, _OBJ_SENT, "objectives", source, base_conf))
        if len(research_questions) < _MAX_ITEMS:
            research_questions.extend(
                _extract_pattern(text, _RQ_SENT, "research_questions", source, base_conf + 0.05)
            )
            research_questions.extend(
                _extract_marked(text, _RQ_MARKED, "research_questions", source, base_conf + 0.1)
            )
        if len(hypotheses) < _MAX_ITEMS:
            hypotheses.extend(_extract_pattern(text, _HYP_SENT, "hypotheses", source, base_conf))
        if problem is None:
            problem = _first_pattern(text, _PROBLEM_SENT, "problem_statement", source, base_conf - 0.05)

    return {
        "schema_version": SCHEMA_VERSION,
        "section_skeleton": _section_skeleton(structure),
        "objectives": _dedupe_items(objectives)[:_MAX_ITEMS],
        "research_questions": _dedupe_items(research_questions)[:_MAX_ITEMS],
        "hypotheses": _dedupe_items(hypotheses)[:_MAX_ITEMS],
        "problem_statement": problem,
    }


def _norm_type(t: Any) -> str:
    """SectionType is a str Enum — str(enum) is 'SectionType.METHODS', not 'methods'."""
    if t is None:
        return ""
    if hasattr(t, "value"):
        return str(getattr(t, "value")).lower()
    s = str(t).lower()
    if s.startswith("sectiontype."):
        return s.split(".", 1)[-1]
    return s


def _collect_section_texts(structure: dict[str, Any]) -> dict[str, str]:
    """Map normalized section_type → content (from normalized_headings or reverse)."""
    out: dict[str, str] = {}
    normalized = structure.get("normalized_headings") or {}
    if isinstance(normalized, dict):
        for k, v in normalized.items():
            key = _norm_type(k)
            if isinstance(v, str) and v.strip():
                out[key] = v.strip()
    raw = structure.get("raw_headings") or {}
    types = structure.get("section_types") or {}
    if isinstance(raw, dict) and isinstance(types, dict):
        for heading, content in raw.items():
            st = _norm_type(types.get(heading)) or "other"
            if not isinstance(content, str) or not content.strip():
                continue
            if st in out:
                out[st] = out[st] + "\n\n" + content.strip()
            else:
                out[st] = content.strip()
    return out


def _section_skeleton(structure: dict[str, Any]) -> list[dict[str, Any]]:
    types = structure.get("section_types") or {}
    order = structure.get("heading_order") or []
    raw = structure.get("raw_headings") or {}
    present_types: set[str] = set()
    if isinstance(types, dict):
        for _h, t in types.items():
            nt = _norm_type(t)
            if nt:
                present_types.add(nt)

    skeleton: list[dict[str, Any]] = []
    for st in _CORE_SECTIONS:
        heading = None
        conf = 0.0
        if isinstance(order, list) and isinstance(types, dict):
            for h in order:
                if _norm_type(types.get(h)) == st:
                    heading = str(h)
                    conf = 0.85 if (isinstance(raw, dict) and raw.get(h)) else 0.7
                    break
        skeleton.append(
            {
                "section_type": st,
                "present": st in present_types,
                "heading": heading,
                "confidence": conf if st in present_types else 0.0,
            }
        )
    return skeleton


def _from_dedicated_headings(structure: dict[str, Any]) -> dict[str, Any]:
    order = structure.get("heading_order") or []
    raw = structure.get("raw_headings") or {}
    if not isinstance(order, list) or not isinstance(raw, dict):
        return {
            "objectives": [],
            "research_questions": [],
            "hypotheses": [],
            "problem_statement": None,
        }

    objectives: list[dict[str, Any]] = []
    rqs: list[dict[str, Any]] = []
    hyps: list[dict[str, Any]] = []
    problem: Optional[dict[str, Any]] = None

    for heading in order:
        content = raw.get(heading)
        if not isinstance(content, str) or len(content.strip()) < 12:
            continue
        text = _clip(content.strip())
        item = {
            "text": text,
            "source": "heading",
            "confidence": 0.88,
            "locator": {"heading": str(heading)},
        }
        if _HEADING_OBJECTIVES.match(str(heading)):
            objectives.append({**item, "kind": "objectives"})
        elif _HEADING_RQ.match(str(heading)):
            # Split RQ-like lines
            for line in content.splitlines():
                line = line.strip()
                if len(line) < 12:
                    continue
                rqs.append(
                    {
                        "text": _clip(line),
                        "source": "heading",
                        "confidence": 0.9,
                        "locator": {"heading": str(heading)},
                        "kind": "research_questions",
                    }
                )
        elif _HEADING_HYP.match(str(heading)):
            for line in content.splitlines():
                line = line.strip()
                if len(line) < 12:
                    continue
                hyps.append(
                    {
                        "text": _clip(line),
                        "source": "heading",
                        "confidence": 0.9,
                        "locator": {"heading": str(heading)},
                        "kind": "hypotheses",
                    }
                )
        elif _HEADING_PROBLEM.match(str(heading)) and problem is None:
            problem = {
                "text": text,
                "source": "heading",
                "confidence": 0.88,
                "locator": {"heading": str(heading)},
                "kind": "problem_statement",
            }

    return {
        "objectives": objectives,
        "research_questions": rqs,
        "hypotheses": hyps,
        "problem_statement": problem,
    }


def _extract_pattern(
    text: str,
    pattern: re.Pattern[str],
    kind: str,
    source: str,
    confidence: float,
) -> list[dict[str, Any]]:
    if confidence < _MIN_CONF:
        return []
    out: list[dict[str, Any]] = []
    for m in pattern.finditer(text):
        sent = (m.groupdict().get("sent") or m.group(0) or "").strip()
        if len(sent) < 20:
            continue
        out.append(
            {
                "text": _clip(sent),
                "source": source,
                "confidence": round(min(confidence, 0.95), 2),
                "locator": {"section": source},
                "kind": kind,
            }
        )
        if len(out) >= _MAX_ITEMS:
            break
    return out


def _extract_marked(
    text: str,
    pattern: re.Pattern[str],
    kind: str,
    source: str,
    confidence: float,
) -> list[dict[str, Any]]:
    if confidence < _MIN_CONF:
        return []
    out: list[dict[str, Any]] = []
    for m in pattern.finditer(text):
        q = (m.groupdict().get("q") or "").strip()
        if len(q) < 12:
            continue
        if not q.endswith("?"):
            q = q + "?"
        out.append(
            {
                "text": _clip(q),
                "source": source,
                "confidence": round(min(confidence, 0.95), 2),
                "locator": {"section": source},
                "kind": kind,
            }
        )
    return out


def _first_pattern(
    text: str,
    pattern: re.Pattern[str],
    kind: str,
    source: str,
    confidence: float,
) -> Optional[dict[str, Any]]:
    items = _extract_pattern(text, pattern, kind, source, confidence)
    return items[0] if items else None


def _dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        key = re.sub(r"\s+", " ", str(item.get("text") or "").lower()).strip()
        if not key or key in seen:
            continue
        if float(item.get("confidence") or 0) < _MIN_CONF:
            continue
        seen.add(key)
        out.append(item)
    return out


def _clip(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= _MAX_TEXT:
        return text
    return text[: _MAX_TEXT - 1].rstrip() + "…"
