"""Methodology profile (Paper Analysis 2.2 / SUE).

Heuristic extraction from Phase 1.1 methods/abstract text, optionally
enriched with classification study_design and medical PICO when present.

Never invents — null / empty when signals are weak.
Cost: regex over already-extracted text; no extra LLM / PDF parse.
"""

from __future__ import annotations

import re
from typing import Any, Optional

SCHEMA_VERSION = "1.0.0"
_MIN_CONF = 0.55
_MAX_TEXT = 400
_MAX_LIST = 6

# Study-design phrases (label, pattern) — prefer longer / more specific first.
_DESIGN_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    ("randomized_controlled_trial", re.compile(r"\brandom(?:i[sz]ed)\s+controlled\s+trial\b|\bRCT\b", re.I), 0.9),
    ("meta_analysis", re.compile(r"\bmeta[- ]analysis\b", re.I), 0.88),
    ("systematic_review", re.compile(r"\bsystematic\s+review\b", re.I), 0.88),
    ("case_control", re.compile(r"\bcase[- ]control\b", re.I), 0.85),
    ("cross_sectional", re.compile(r"\bcross[- ]sectional\b", re.I), 0.85),
    ("cohort", re.compile(r"\b(?:prospective|retrospective)?\s*cohort\s+stud(?:y|ies)\b|\bcohort\s+design\b", re.I), 0.82),
    ("qualitative", re.compile(r"\bqualitative\s+(?:study|interview|analysis)\b", re.I), 0.8),
    ("mixed_methods", re.compile(r"\bmixed[- ]methods?\b", re.I), 0.8),
    ("survey", re.compile(r"\b(?:online\s+)?survey\b|\bquestionnaire[- ]based\b", re.I), 0.75),
    ("benchmark", re.compile(r"\bbenchmark(?:ing)?\s+(?:study|evaluation|experiment)\b", re.I), 0.78),
    ("experiment", re.compile(r"\b(?:controlled\s+)?experiment(?:al\s+study)?\b", re.I), 0.7),
]

_SAMPLE_SIZE = re.compile(
    r"(?P<span>(?:(?:a\s+)?(?:total\s+of\s+)?(?P<n>\d{1,3}(?:,\d{3})*|\d+)\s+"
    r"(?:participants?|patients?|subjects?|respondents?|students?|users?|samples?|"
    r"papers?|articles?|documents?|images?|trials?))"
    r"|(?:n\s*=\s*(?P<n2>\d{1,3}(?:,\d{3})*|\d+))"
    r"|(?:sample\s+size\s*(?:of|=|:)?\s*(?P<n3>\d{1,3}(?:,\d{3})*|\d+)))",
    re.I,
)

_POPULATION = re.compile(
    r"(?P<sent>[^.!?\n]{0,60}?\b(?:participants?|patients?|subjects?|respondents?|"
    r"population|adults?|children|students?)\b[^.!?\n]{10,280}[.!?])",
    re.I,
)

_INTERVENTION = re.compile(
    r"(?P<sent>[^.!?\n]{0,40}?\b(?:intervention|treatment|therapy|we\s+(?:applied|administered|used)\b)"
    r"[^.!?\n]{8,280}[.!?])",
    re.I,
)

_CONTROL = re.compile(
    r"(?P<sent>[^.!?\n]{0,40}?\b(?:control\s+group|placebo|usual\s+care|sham|"
    r"baseline\s+condition|comparison\s+group)\b[^.!?\n]{5,250}[.!?])",
    re.I,
)

_DATASET = re.compile(
    r"(?P<sent>[^.!?\n]{0,50}?\b(?:dataset|data\s+set|corpus|benchmark)\b[^.!?\n]{5,250}[.!?])",
    re.I,
)

_METRIC = re.compile(
    r"(?P<span>\b(?:accuracy|precision|recall|f1(?:[- ]score)?|auc|auroc|rmse|mae|"
    r"bleu|rouge|perplexity|sensitivity|specificity|odds\s+ratio|hazard\s+ratio|"
    r"p[- ]value|confidence\s+interval)\b)",
    re.I,
)

_VARIABLE = re.compile(
    r"(?P<sent>[^.!?\n]{0,40}?\b(?:independent|dependent|predictor|outcome)\s+variables?\b"
    r"[^.!?\n]{5,220}[.!?])",
    re.I,
)

_SETUP = re.compile(
    r"(?P<sent>[^.!?\n]{0,40}?\b(?:experimental\s+setup|procedure|protocol|we\s+conducted|"
    r"study\s+design\s+was|design\s+was)\b[^.!?\n]{10,300}[.!?])",
    re.I,
)

_CODE_AVAIL = re.compile(
    r"(?P<span>[^.!?\n]{0,80}?\b(?:code|source\s+code|implementation)\b[^.!?\n]{0,120}?"
    r"(?:available|released|github\.com|gitlab\.com|bitbucket\.org)[^.!?\n]{0,120})",
    re.I,
)
_CODE_UNAVAIL = re.compile(
    r"\b(?:code|source\s+code)\b[^.!?\n]{0,40}\b(?:not\s+available|unavailable|proprietary)\b",
    re.I,
)

_DATA_AVAIL = re.compile(
    r"(?P<span>[^.!?\n]{0,80}?\b(?:data|dataset)\b[^.!?\n]{0,100}?"
    r"(?:available|publicly\s+available|upon\s+request|zenodo|figshare|dryad)[^.!?\n]{0,100})",
    re.I,
)
_DATA_UNAVAIL = re.compile(
    r"\b(?:data|dataset)\b[^.!?\n]{0,40}\b(?:not\s+available|unavailable|confidential|proprietary)\b",
    re.I,
)


def extract_methodology_profile(
    document_payload: dict[str, Any],
    *,
    classification: Optional[dict[str, Any]] = None,
    medical: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build methodology_profile from DU (+ optional classification / medical)."""
    metadata = document_payload.get("metadata") if isinstance(document_payload.get("metadata"), dict) else {}
    structure = document_payload.get("structure") if isinstance(document_payload.get("structure"), dict) else {}

    section_texts = _section_texts(structure)
    methods = section_texts.get("methods") or ""
    abstract = str(metadata.get("abstract") or "").strip()
    # Prefer methods; fall back to abstract for design/availability cues only.
    primary = methods[:12000] if methods else abstract[:6000]
    secondary = abstract[:4000] if methods else ""

    study_design = _from_classification(classification) or _match_design(primary) or _match_design(secondary)
    sample_size = _match_sample_size(primary) or _match_sample_size(secondary)
    population = _first_sent(primary, _POPULATION, "population", "methods", 0.7) or _pico_field(
        medical, "population"
    )
    intervention = _first_sent(primary, _INTERVENTION, "intervention", "methods", 0.68) or _pico_field(
        medical, "intervention"
    )
    controls = _first_sent(primary, _CONTROL, "controls", "methods", 0.7)
    dataset = _first_sent(primary, _DATASET, "dataset", "methods", 0.72) or _first_sent(
        secondary, _DATASET, "dataset", "abstract", 0.65
    )
    experimental_setup = _first_sent(primary, _SETUP, "experimental_setup", "methods", 0.68)
    variables = _collect_sents(primary, _VARIABLE, "variables", "methods", 0.65)
    metrics = _collect_metrics(primary) or _collect_metrics(secondary)

    code_available = _availability(primary + "\n" + secondary, _CODE_AVAIL, _CODE_UNAVAIL, "code_available")
    dataset_available = _availability(primary + "\n" + secondary, _DATA_AVAIL, _DATA_UNAVAIL, "dataset_available")

    fields = {
        "study_design": study_design,
        "population": population,
        "sample_size": sample_size,
        "intervention": intervention,
        "controls": controls,
        "dataset": dataset,
        "experimental_setup": experimental_setup,
        "variables": variables[:_MAX_LIST],
        "metrics": metrics[:_MAX_LIST],
        "code_available": code_available,
        "dataset_available": dataset_available,
    }
    filled = sum(1 for v in fields.values() if v) + sum(
        1 for v in (variables, metrics) if v
    )

    return {
        "schema_version": SCHEMA_VERSION,
        **fields,
        "has_content": bool(
            study_design
            or population
            or sample_size
            or intervention
            or controls
            or dataset
            or experimental_setup
            or variables
            or metrics
            or code_available
            or dataset_available
        ),
        "methods_section_present": bool(methods.strip()),
        "field_count": filled,
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
    locator: Optional[dict[str, str]] = None,
    label: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "text": _clip(text),
        "label": label,
        "kind": kind,
        "source": source,
        "confidence": round(min(max(confidence, 0.0), 0.95), 2),
        "locator": locator or {"section": source},
    }


def _from_classification(classification: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not isinstance(classification, dict):
        return None
    design = classification.get("study_design")
    label = None
    conf = 0.8
    if isinstance(design, dict):
        label = design.get("label") or design.get("study_design") or design.get("value")
        try:
            conf = float(design.get("confidence") or conf)
        except (TypeError, ValueError):
            conf = 0.8
    elif isinstance(design, str):
        label = design
    if not label:
        return None
    text = str(label).replace("_", " ").strip()
    if not text or text.lower() in {"unknown", "other", "none"}:
        return None
    return _field(
        text,
        kind="study_design",
        source="classification",
        confidence=max(conf, 0.75),
        locator={"phase": "classification"},
        label=str(label),
    )


def _match_design(text: str) -> Optional[dict[str, Any]]:
    if not text:
        return None
    for label, pat, conf in _DESIGN_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        return _field(
            m.group(0),
            kind="study_design",
            source="methods",
            confidence=conf,
            label=label,
        )
    return None


def _match_sample_size(text: str) -> Optional[dict[str, Any]]:
    if not text:
        return None
    m = _SAMPLE_SIZE.search(text)
    if not m:
        return None
    n = m.group("n") or m.group("n2") or m.group("n3")
    span = m.group("span") or m.group(0)
    return _field(
        span,
        kind="sample_size",
        source="methods",
        confidence=0.85,
        label=str(n).replace(",", "") if n else None,
    )


def _first_sent(
    text: str,
    pattern: re.Pattern[str],
    kind: str,
    source: str,
    confidence: float,
) -> Optional[dict[str, Any]]:
    if not text or confidence < _MIN_CONF:
        return None
    m = pattern.search(text)
    if not m:
        return None
    sent = (m.groupdict().get("sent") or m.group(0) or "").strip()
    if len(sent) < 16:
        return None
    return _field(sent, kind=kind, source=source, confidence=confidence)


def _collect_sents(
    text: str,
    pattern: re.Pattern[str],
    kind: str,
    source: str,
    confidence: float,
) -> list[dict[str, Any]]:
    if not text:
        return []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for m in pattern.finditer(text):
        sent = (m.groupdict().get("sent") or m.group(0) or "").strip()
        key = re.sub(r"\s+", " ", sent.lower())
        if len(sent) < 16 or key in seen:
            continue
        seen.add(key)
        out.append(_field(sent, kind=kind, source=source, confidence=confidence))
        if len(out) >= _MAX_LIST:
            break
    return out


def _collect_metrics(text: str) -> list[dict[str, Any]]:
    if not text:
        return []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for m in _METRIC.finditer(text):
        span = (m.group("span") or m.group(0) or "").strip()
        key = span.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(_field(span, kind="metrics", source="methods", confidence=0.8, label=key))
        if len(out) >= _MAX_LIST:
            break
    return out


def _pico_field(medical: Optional[dict[str, Any]], key: str) -> Optional[dict[str, Any]]:
    if not isinstance(medical, dict):
        return None
    pico = medical.get("pico_elements") or medical.get("pico") or {}
    if not isinstance(pico, dict):
        return None
    raw = pico.get(key)
    text = ""
    if isinstance(raw, dict):
        text = str(raw.get("label") or raw.get("value") or raw.get("description") or "").strip()
    elif isinstance(raw, str):
        text = raw.strip()
    if len(text) < 3:
        return None
    return _field(text, kind=key, source="medical_understanding", confidence=0.8, locator={"phase": "medical_understanding"})


def _availability(
    text: str,
    avail_pat: re.Pattern[str],
    unavail_pat: re.Pattern[str],
    kind: str,
) -> Optional[dict[str, Any]]:
    if not text:
        return None
    if unavail_pat.search(text):
        m = unavail_pat.search(text)
        return _field(
            (m.group(0) if m else "not available").strip(),
            kind=kind,
            source="methods",
            confidence=0.8,
            label="unavailable",
        )
    m = avail_pat.search(text)
    if not m:
        return None
    span = (m.groupdict().get("span") or m.group(0) or "").strip()
    return _field(span, kind=kind, source="methods", confidence=0.82, label="available")


def _clip(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= _MAX_TEXT:
        return text
    return text[: _MAX_TEXT - 1].rstrip() + "…"
