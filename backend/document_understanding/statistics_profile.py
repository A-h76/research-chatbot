"""Statistical findings profile (Paper Analysis 2.3 / SUE).

Heuristic extraction of *explicit* statistical reporting from
results/abstract/discussion/methods text. Optionally merges medical
phase `statistical_measures` when present.

Never invents significance — interpretation entries are only kept when
the author literally states them (`author_stated: true`). Prefer honest
empty over guessed p-values or “significant” labels.

Cost: regex over already-extracted text; no extra LLM / PDF parse.
Distinct from `statistics.py` (document page/word counts).
"""

from __future__ import annotations

import re
from typing import Any, Optional

SCHEMA_VERSION = "1.0.0"
_MIN_CONF = 0.55
_MAX_TEXT = 280
_MAX_LIST = 8

# Named statistical tests / procedures (label, pattern).
_TEST_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    ("anova", re.compile(r"\b(?:one[- ]way|two[- ]way|repeated[- ]measures?\s+)?ANOVA\b|\bANCOVA\b", re.I), 0.88),
    ("t_test", re.compile(r"\b(?:paired\s+|unpaired\s+|independent\s+|student'?s?\s+)?t[- ]tests?\b", re.I), 0.88),
    ("chi_square", re.compile(r"\bchi[- ]square(?:d)?\b|\bχ\s*2\b|\bX\s*2\s*test\b", re.I), 0.88),
    ("mann_whitney", re.compile(r"\bMann[- ]Whitney\b|\bWilcoxon\s+rank[- ]sum\b", re.I), 0.86),
    ("wilcoxon", re.compile(r"\bWilcoxon\s+signed[- ]rank\b", re.I), 0.86),
    ("kruskal_wallis", re.compile(r"\bKruskal[- ]Wallis\b", re.I), 0.86),
    ("fisher_exact", re.compile(r"\bFisher(?:'s)?\s+exact\b", re.I), 0.86),
    ("regression", re.compile(
        r"\b(?:linear|logistic|multiple|multivariate|hierarchical|poisson|cox)\s+regression\b|"
        r"\bCox\s+(?:proportional\s+hazards\s+)?model\b",
        re.I,
    ), 0.84),
    ("correlation", re.compile(r"\b(?:Pearson|Spearman|Kendall)\s+(?:correlation|r)\b|\bcorrelation\s+coefficient\b", re.I), 0.82),
    ("bayesian", re.compile(r"\bBayesian\s+(?:analysis|inference|model|posterior)\b", re.I), 0.8),
    ("survival", re.compile(r"\bKaplan[- ]Meier\b|\blog[- ]rank\s+test\b", re.I), 0.84),
]

_P_VALUE = re.compile(
    r"(?P<span>\bp\s*(?:[- ]?value)?\s*[<≤≥>=]\s*0?\.\d+(?:e[-+]?\d+)?\b)",
    re.I,
)

_CI = re.compile(
    r"(?P<span>(?:\d{2,3}\s*%\s*)?(?:CI|confidence\s+interval)\s*"
    r"[=:]?\s*[\(\[]?\s*-?\d+(?:\.\d+)?\s*[,;\-–to]+\s*-?\d+(?:\.\d+)?\s*[\)\]]?)",
    re.I,
)

_EFFECT = re.compile(
    r"(?P<span>\b(?:(?:HR|OR|RR|hazard\s+ratio|odds\s+ratio|relative\s+risk)\s*"
    r"[=:]?\s*\d+(?:\.\d+)?(?:\s*\([^)]{0,80}\))?|"
    r"(?:Cohen'?s?\s+d|Hedges'?s?\s+g|eta[- ]?squared|η\s*2|partial\s+η\s*2)\s*"
    r"[=:]?\s*-?\d+(?:\.\d+)?|"
    r"effect\s+size\s*[=:]?\s*-?\d+(?:\.\d+)?)\b)",
    re.I,
)

_OTHER = re.compile(
    r"(?P<span>\b(?:mean\s+difference\s*[=:]?\s*-?\d+(?:\.\d+)?|"
    r"SD\s*[=:]?\s*\d+(?:\.\d+)?|"
    r"±\s*\d+(?:\.\d+)?)\b)",
    re.I,
)

# Author-stated interpretation only — never infer significance from p alone.
_INTERP = re.compile(
    r"(?P<sent>[^.!?\n]{0,40}?\b(?:statistically\s+significant|"
    r"did\s+not\s+reach\s+(?:statistical\s+)?significance|"
    r"not\s+statistically\s+significant|"
    r"failed\s+to\s+reach\s+significance|"
    r"marginally\s+significant|"
    r"no\s+significant\s+(?:difference|effect|association))\b[^.!?\n]{0,200}[.!?])",
    re.I,
)

_MEDICAL_KIND = {
    "p_value": "p_values",
    "confidence_interval": "confidence_intervals",
    "hazard_ratio": "effect_sizes",
    "odds_ratio": "effect_sizes",
    "relative_risk": "effect_sizes",
    "effect_size": "effect_sizes",
    "mean_difference": "other_measures",
    "standard_deviation": "other_measures",
}


def extract_statistics_profile(
    document_payload: dict[str, Any],
    *,
    medical: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build statistics_profile from DU (+ optional medical measures)."""
    metadata = document_payload.get("metadata") if isinstance(document_payload.get("metadata"), dict) else {}
    structure = document_payload.get("structure") if isinstance(document_payload.get("structure"), dict) else {}

    section_texts = _section_texts(structure)
    results = section_texts.get("results") or ""
    discussion = section_texts.get("discussion") or ""
    methods = section_texts.get("methods") or ""
    abstract = str(metadata.get("abstract") or "").strip()

    # Prefer results; fall back to abstract/discussion; methods mainly for named tests.
    corpora = [
        ("results", results[:14000]),
        ("abstract", abstract[:5000]),
        ("discussion", discussion[:8000]),
        ("methods", methods[:8000]),
    ]

    tests = _collect_tests(corpora)
    p_values = _collect_spans(corpora, _P_VALUE, "p_value", prefer=("results", "abstract", "discussion"))
    confidence_intervals = _collect_spans(
        corpora, _CI, "confidence_interval", prefer=("results", "abstract", "discussion")
    )
    effect_sizes = _collect_spans(corpora, _EFFECT, "effect_size", prefer=("results", "abstract", "discussion"))
    other_measures = _collect_spans(corpora, _OTHER, "other_measure", prefer=("results", "abstract", "discussion"))
    interpretations = _collect_interpretations(corpora)

    _merge_medical(
        medical,
        tests=tests,
        p_values=p_values,
        confidence_intervals=confidence_intervals,
        effect_sizes=effect_sizes,
        other_measures=other_measures,
    )

    tests = tests[:_MAX_LIST]
    p_values = p_values[:_MAX_LIST]
    confidence_intervals = confidence_intervals[:_MAX_LIST]
    effect_sizes = effect_sizes[:_MAX_LIST]
    other_measures = other_measures[:_MAX_LIST]
    interpretations = interpretations[:_MAX_LIST]

    has_content = bool(
        tests
        or p_values
        or confidence_intervals
        or effect_sizes
        or other_measures
        or interpretations
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "tests": tests,
        "p_values": p_values,
        "confidence_intervals": confidence_intervals,
        "effect_sizes": effect_sizes,
        "other_measures": other_measures,
        "interpretations": interpretations,
        "has_content": has_content,
        "results_section_present": bool(results.strip()),
        "field_count": (
            len(tests)
            + len(p_values)
            + len(confidence_intervals)
            + len(effect_sizes)
            + len(other_measures)
            + len(interpretations)
        ),
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
    label: Optional[str] = None,
    author_stated: bool = False,
    locator: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    return {
        "text": _clip(text),
        "label": label,
        "kind": kind,
        "source": source,
        "confidence": round(min(max(confidence, 0.0), 0.95), 2),
        "author_stated": bool(author_stated),
        "locator": locator or {"section": source},
    }


def _collect_tests(corpora: list[tuple[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source, text in corpora:
        if not text:
            continue
        for label, pat, conf in _TEST_PATTERNS:
            if label in seen:
                continue
            m = pat.search(text)
            if not m:
                continue
            seen.add(label)
            out.append(
                _field(
                    m.group(0),
                    kind="statistical_test",
                    source=source,
                    confidence=conf,
                    label=label,
                )
            )
            if len(out) >= _MAX_LIST:
                return out
    return out


def _collect_spans(
    corpora: list[tuple[str, str]],
    pattern: re.Pattern[str],
    kind: str,
    *,
    prefer: tuple[str, ...],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    ordered = sorted(
        corpora,
        key=lambda pair: prefer.index(pair[0]) if pair[0] in prefer else len(prefer),
    )
    for source, text in ordered:
        if not text:
            continue
        for m in pattern.finditer(text):
            span = (m.groupdict().get("span") or m.group(0) or "").strip()
            key = re.sub(r"\s+", " ", span.lower())
            if len(span) < 3 or key in seen:
                continue
            seen.add(key)
            out.append(_field(span, kind=kind, source=source, confidence=0.85))
            if len(out) >= _MAX_LIST:
                return out
    return out


def _collect_interpretations(corpora: list[tuple[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source, text in corpora:
        if not text or source == "methods":
            # Methods often say "significance was set at p<0.05" — not a finding.
            continue
        for m in _INTERP.finditer(text):
            sent = (m.groupdict().get("sent") or m.group(0) or "").strip()
            key = re.sub(r"\s+", " ", sent.lower())
            if len(sent) < 20 or key in seen:
                continue
            seen.add(key)
            out.append(
                _field(
                    sent,
                    kind="interpretation",
                    source=source,
                    confidence=0.78,
                    author_stated=True,
                    label="author_stated",
                )
            )
            if len(out) >= _MAX_LIST:
                return out
    return out


def _merge_medical(
    medical: Optional[dict[str, Any]],
    *,
    tests: list[dict[str, Any]],
    p_values: list[dict[str, Any]],
    confidence_intervals: list[dict[str, Any]],
    effect_sizes: list[dict[str, Any]],
    other_measures: list[dict[str, Any]],
) -> None:
    if not isinstance(medical, dict):
        return
    raw = medical.get("statistical_measures")
    if not isinstance(raw, list):
        return
    buckets = {
        "p_values": p_values,
        "confidence_intervals": confidence_intervals,
        "effect_sizes": effect_sizes,
        "other_measures": other_measures,
    }
    seen = {
        name: {re.sub(r"\s+", " ", (f.get("text") or "").lower()) for f in lst}
        for name, lst in buckets.items()
    }
    for item in raw:
        if not isinstance(item, dict):
            continue
        mtype = item.get("measure_type") or item.get("type") or ""
        if hasattr(mtype, "value"):
            mtype = getattr(mtype, "value")
        mtype_s = str(mtype).lower().strip()
        bucket = _MEDICAL_KIND.get(mtype_s)
        if not bucket:
            continue
        value = str(item.get("value") or "").strip()
        if len(value) < 3:
            continue
        key = re.sub(r"\s+", " ", value.lower())
        if key in seen[bucket]:
            continue
        seen[bucket].add(key)
        try:
            conf = float(item.get("confidence") or 0.75)
        except (TypeError, ValueError):
            conf = 0.75
        buckets[bucket].append(
            _field(
                value,
                kind=mtype_s,
                source="medical_understanding",
                confidence=max(conf, _MIN_CONF),
                label=mtype_s,
                locator={"phase": "medical_understanding"},
            )
        )
    # `tests` unused for medical merge today — kept for API symmetry / future.
    _ = tests


def _clip(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= _MAX_TEXT:
        return text
    return text[: _MAX_TEXT - 1].rstrip() + "…"
