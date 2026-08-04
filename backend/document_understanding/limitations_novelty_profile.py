"""Limitations & novelty profile (Paper Analysis 2.5 / SUE).

Heuristic extraction of *author-stated* limitations, novelty/contributions,
future work, and research gaps from discussion / limitations / conclusion /
abstract text.

Never invents critique or hype judgments — every kept item is tagged
`author_stated: true`. Prefer honest empty over AI-scored “breakthrough”.

Cost: regex over already-extracted section text; no extra LLM / PDF parse.
"""

from __future__ import annotations

import re
from typing import Any, Optional

SCHEMA_VERSION = "1.0.0"
_MAX_TEXT = 400
_MAX_LIST = 8

# Dedicated heading titles that often hold framing content.
_HEADING_LIMITATIONS = re.compile(
    r"^\s*(?:\d+[\.\)]\s*)?(?:limitations?|study\s+limitations?|"
    r"threats?\s+to\s+validity|methodological\s+limitations?)\s*$",
    re.I,
)
_HEADING_FUTURE = re.compile(
    r"^\s*(?:\d+[\.\)]\s*)?(?:future\s+work|future\s+directions?|"
    r"further\s+research|recommendations?\s+for\s+future)\s*$",
    re.I,
)
_HEADING_CONTRIB = re.compile(
    r"^\s*(?:\d+[\.\)]\s*)?(?:contributions?|novel(?:ty)?\s+contributions?|"
    r"key\s+contributions?|our\s+contributions?)\s*$",
    re.I,
)
_HEADING_GAPS = re.compile(
    r"^\s*(?:\d+[\.\)]\s*)?(?:research\s+gaps?|knowledge\s+gaps?|open\s+questions?)\s*$",
    re.I,
)

# In-prose patterns — conservative, author voice.
_LIM_SENT = re.compile(
    r"(?P<sent>[^.!?\n]{0,60}?\b(?:limitations?\s+(?:of\s+(?:this|the)\s+study\s+)?"
    r"(?:include|are|include\s+that)|"
    r"(?:a|one|several|important)\s+limitation\s+(?:is|was|of)|"
    r"we\s+acknowledge\s+(?:several\s+)?limitations?|"
    r"should\s+be\s+interpreted\s+with\s+caution|"
    r"findings\s+(?:may|should)\s+(?:not\s+)?(?:be\s+)?generaliz|"
    r"threats?\s+to\s+(?:internal\s+|external\s+)?validity|"
    r"single[- ]center|small\s+sample\s+size|"
    r"selection\s+bias|recall\s+bias|confounding)\b[^.!?\n]{5,320}[.!?])",
    re.I,
)

_NOVELTY_SENT = re.compile(
    r"(?P<sent>[^.!?\n]{0,50}?\b(?:to\s+our\s+knowledge|"
    r"for\s+the\s+first\s+time|"
    r"we\s+(?:present|propose|introduce|develop(?:ed)?)\s+(?:a\s+)?(?:novel|new)|"
    r"(?:a|our)\s+novel\s+(?:approach|method|framework|contribution)|"
    r"key\s+contributions?\s+(?:are|include)|"
    r"this\s+(?:paper|study|work)\s+(?:makes|offers)\s+(?:the\s+following\s+)?"
    r"contributions?|"
    r"unlike\s+(?:prior|previous|existing)\s+(?:work|studies))\b[^.!?\n]{8,320}[.!?])",
    re.I,
)

_FUTURE_SENT = re.compile(
    r"(?P<sent>[^.!?\n]{0,50}?\b(?:future\s+(?:work|research|studies|directions)|"
    r"further\s+(?:research|studies|investigation)|"
    r"we\s+(?:plan|intend|aim)\s+to|"
    r"should\s+be\s+(?:explored|investigated|examined)\s+in\s+future|"
    r"promising\s+avenue(?:s)?\s+for\s+(?:future\s+)?research)\b[^.!?\n]{8,300}[.!?])",
    re.I,
)

_GAP_SENT = re.compile(
    r"(?P<sent>[^.!?\n]{0,50}?\b(?:research\s+gap|knowledge\s+gap|"
    r"little\s+is\s+known|"
    r"remains?\s+(?:poorly\s+)?(?:understood|unclear|unknown)|"
    r"few\s+studies\s+have|"
    r"under[- ]explored|underexplored)\b[^.!?\n]{8,300}[.!?])",
    re.I,
)

_BULLET = re.compile(
    r"(?:^|\n)\s*(?:[-*•]|\d+[\.\)])\s+(?P<item>[^\n]{12,350})",
)


def extract_limitations_novelty_profile(
    document_payload: dict[str, Any],
    *,
    narrative: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build limitations_novelty_profile from DU (+ optional narrative lists)."""
    metadata = document_payload.get("metadata") if isinstance(document_payload.get("metadata"), dict) else {}
    structure = document_payload.get("structure") if isinstance(document_payload.get("structure"), dict) else {}

    section_texts = _section_texts(structure)
    abstract = str(metadata.get("abstract") or "").strip()
    discussion = section_texts.get("discussion") or ""
    conclusion = section_texts.get("conclusion") or ""
    limitations_sec = section_texts.get("limitations") or ""
    intro = section_texts.get("introduction") or ""

    heading_hits = _from_dedicated_headings(structure)

    limitations = list(heading_hits["limitations"])
    novelty = list(heading_hits["novelty"])
    future_work = list(heading_hits["future_work"])
    research_gaps = list(heading_hits["research_gaps"])

    # Prefer limitations section, then discussion/conclusion, then abstract.
    lim_corpus = [
        ("limitations", limitations_sec[:10000]),
        ("discussion", discussion[:10000]),
        ("conclusion", conclusion[:6000]),
        ("abstract", abstract[:4000]),
    ]
    nov_corpus = [
        ("abstract", abstract[:4000]),
        ("introduction", intro[:8000]),
        ("conclusion", conclusion[:6000]),
        ("discussion", discussion[:6000]),
    ]
    fut_corpus = [
        ("discussion", discussion[:8000]),
        ("conclusion", conclusion[:6000]),
        ("abstract", abstract[:3000]),
    ]
    gap_corpus = [
        ("introduction", intro[:8000]),
        ("discussion", discussion[:6000]),
        ("abstract", abstract[:4000]),
    ]

    _extend(limitations, _collect_sents(lim_corpus, _LIM_SENT, "limitation"))
    _extend(novelty, _collect_sents(nov_corpus, _NOVELTY_SENT, "novelty"))
    _extend(future_work, _collect_sents(fut_corpus, _FUTURE_SENT, "future_work"))
    _extend(research_gaps, _collect_sents(gap_corpus, _GAP_SENT, "research_gap"))

    # Optional Narrative enrich (LLM lists) — still author/paper-scoped strings only.
    _merge_narrative_lists(narrative, "limitations", limitations, "limitation")
    _merge_narrative_lists(narrative, "key_contributions", novelty, "novelty")
    _merge_narrative_lists(narrative, "future_work", future_work, "future_work")

    limitations = limitations[:_MAX_LIST]
    novelty = novelty[:_MAX_LIST]
    future_work = future_work[:_MAX_LIST]
    research_gaps = research_gaps[:_MAX_LIST]

    has_content = bool(limitations or novelty or future_work or research_gaps)

    return {
        "schema_version": SCHEMA_VERSION,
        "limitations": limitations,
        "novelty": novelty,
        "future_work": future_work,
        "research_gaps": research_gaps,
        "has_content": has_content,
        "limitations_section_present": bool(limitations_sec.strip()),
        "field_count": len(limitations) + len(novelty) + len(future_work) + len(research_gaps),
    }


def _section_texts(structure: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    normalized = structure.get("normalized_headings") or {}
    if isinstance(normalized, dict):
        for k, v in normalized.items():
            key = _norm_key(k)
            if isinstance(v, str) and v.strip():
                out[key] = v.strip()
    raw = structure.get("raw_headings") or {}
    types = structure.get("section_types") or {}
    if isinstance(raw, dict) and isinstance(types, dict):
        for heading, content in raw.items():
            st = _norm_key(types.get(heading)) or "other"
            if not isinstance(content, str) or not content.strip():
                continue
            out[st] = (out.get(st, "") + "\n\n" + content.strip()).strip()
            # Promote dedicated limitation-like headings even if typed as discussion.
            if _HEADING_LIMITATIONS.match(str(heading or "")):
                out["limitations"] = (out.get("limitations", "") + "\n\n" + content.strip()).strip()
    return out


def _norm_key(t: Any) -> str:
    if t is None:
        return ""
    if hasattr(t, "value"):
        return str(getattr(t, "value")).lower()
    s = str(t).lower()
    if "." in s and s.split(".", 1)[0].endswith("type"):
        return s.split(".", 1)[-1]
    return s


def _field(
    text: str,
    *,
    kind: str,
    source: str,
    confidence: float,
    label: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "text": _clip(text),
        "label": label,
        "kind": kind,
        "source": source,
        "confidence": round(min(max(confidence, 0.0), 0.95), 2),
        "author_stated": True,
        "locator": {"section": source},
    }


def _from_dedicated_headings(structure: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {
        "limitations": [],
        "novelty": [],
        "future_work": [],
        "research_gaps": [],
    }
    raw = structure.get("raw_headings") or {}
    if not isinstance(raw, dict):
        return out
    for heading, content in raw.items():
        if not isinstance(content, str) or not content.strip():
            continue
        h = str(heading or "")
        body = content.strip()
        if _HEADING_LIMITATIONS.match(h):
            _extend(out["limitations"], _items_from_block(body, "limitation", "limitations", 0.9))
        elif _HEADING_FUTURE.match(h):
            _extend(out["future_work"], _items_from_block(body, "future_work", "future_work", 0.88))
        elif _HEADING_CONTRIB.match(h):
            _extend(out["novelty"], _items_from_block(body, "novelty", "contributions", 0.88))
        elif _HEADING_GAPS.match(h):
            _extend(out["research_gaps"], _items_from_block(body, "research_gap", "research_gaps", 0.86))
    return out


def _items_from_block(
    body: str, kind: str, source: str, confidence: float
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for m in _BULLET.finditer(body):
        item = (m.group("item") or "").strip()
        if len(item) < 12:
            continue
        items.append(_field(item, kind=kind, source=source, confidence=confidence))
        if len(items) >= _MAX_LIST:
            return items
    # Fall back to sentences if no bullets.
    if not items:
        for sent in re.split(r"(?<=[.!?])\s+", body):
            sent = sent.strip()
            if len(sent) < 20:
                continue
            items.append(_field(sent, kind=kind, source=source, confidence=confidence - 0.05))
            if len(items) >= _MAX_LIST:
                break
    return items


def _collect_sents(
    corpora: list[tuple[str, str]],
    pattern: re.Pattern[str],
    kind: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source, text in corpora:
        if not text:
            continue
        for m in pattern.finditer(text):
            sent = (m.groupdict().get("sent") or m.group(0) or "").strip()
            key = re.sub(r"\s+", " ", sent.lower())
            if len(sent) < 20 or key in seen:
                continue
            seen.add(key)
            out.append(_field(sent, kind=kind, source=source, confidence=0.78))
            if len(out) >= _MAX_LIST:
                return out
    return out


def _extend(dst: list[dict[str, Any]], more: list[dict[str, Any]]) -> None:
    seen = {re.sub(r"\s+", " ", (x.get("text") or "").lower()) for x in dst}
    for item in more:
        key = re.sub(r"\s+", " ", (item.get("text") or "").lower())
        if not key or key in seen:
            continue
        seen.add(key)
        dst.append(item)
        if len(dst) >= _MAX_LIST:
            return


def _merge_narrative_lists(
    narrative: Optional[dict[str, Any]],
    key: str,
    dst: list[dict[str, Any]],
    kind: str,
) -> None:
    if not isinstance(narrative, dict):
        return
    raw = narrative.get(key)
    if not isinstance(raw, list):
        return
    extras: list[dict[str, Any]] = []
    for item in raw:
        text = ""
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            text = str(item.get("text") or item.get("label") or "").strip()
        if len(text) < 12:
            continue
        extras.append(
            _field(text, kind=kind, source="narrative", confidence=0.7, label="narrative")
        )
    _extend(dst, extras)


def _clip(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= _MAX_TEXT:
        return text
    return text[: _MAX_TEXT - 1].rstrip() + "…"
