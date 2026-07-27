"""Entity normalization — maps a raw matched string (e.g. "MI", "heart
attack") to a canonical value (e.g. "myocardial infarction") plus an
EntityNormalizationStatus describing how confident that mapping is.

ontology_provider="local" (see config.py's own docstring for why this is
the only real implementation) means this is a small, curated synonym/
abbreviation table, not a real UMLS/SNOMED CT lookup — new terms are
recognized by extending SYNONYMS/AMBIGUOUS_ABBREVIATIONS below, the same
"add a dict entry, no logic changes" pattern every keyword table in this
codebase already follows (see backend.classification.pass2.keywords).

Strategy ("exact_then_synonym_then_fuzzy", config.normalization_strategy):
  1. Exact match: the raw text, lowercased, already equals a known
     canonical value.
  2. Synonym match: the raw text is a known synonym/abbreviation for
     exactly one canonical value.
  3. Fuzzy match: falls back to a simple, deterministic containment
     check between the raw text and known canonical values — no edit-
     distance/embedding similarity (that's ML territory; see package
     docstring's Non-Goals on LLM integration).
  4. Ambiguous: the raw text is a known abbreviation for more than one
     canonical value (see entity_registry.py's resolve_ambiguity(),
     which a caller should try first, using document context to
     disambiguate before falling back to this AMBIGUOUS status).
  5. Unknown: nothing matched at all — the raw text is kept as its own
     canonical value, honestly flagged as not normalized.
"""

from typing import Optional

from .enums import EntityNormalizationStatus

# Canonical value -> known synonyms/abbreviations (case-insensitive).
# Deliberately small and illustrative, not exhaustive medical coverage —
# see module docstring.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "myocardial infarction": ("mi", "heart attack"),
    "hypertension": ("htn", "high blood pressure"),
    "diabetes mellitus": ("dm", "diabetes"),
    "chronic obstructive pulmonary disease": ("copd",),
    "multiple sclerosis": ("ms",),
    "cerebrovascular accident": ("cva", "stroke"),
    "acute kidney injury": ("aki",),
    "chronic kidney disease": ("ckd",),
    "coronary artery disease": ("cad",),
    "atrial fibrillation": ("af", "afib"),
    "human immunodeficiency virus": ("hiv",),
    "acquired immunodeficiency syndrome": ("aids",),
}

# Abbreviations known to be genuinely ambiguous (map to more than one
# real canonical value) — resolved via document context
# (entity_registry.py's resolve_ambiguity()) or left AMBIGUOUS if context
# doesn't help. "ms" is deliberately absent from SYNONYMS above (it would
# otherwise be treated as an unambiguous synonym of "multiple sclerosis")
# so this table is checked first.
AMBIGUOUS_ABBREVIATIONS: dict[str, tuple[str, ...]] = {
    "ms": ("multiple sclerosis", "mitral stenosis"),
    "pd": ("parkinson's disease", "peritoneal dialysis"),
    "ra": ("rheumatoid arthritis", "renal artery"),
}

_SYNONYM_TO_CANONICAL: dict[str, str] = {
    synonym: canonical for canonical, synonyms in SYNONYMS.items() for synonym in synonyms
}


def normalize(raw_text: str) -> tuple[str, EntityNormalizationStatus, list[str]]:
    """Returns (normalized_value, status, synonyms_of_the_result) — see
    module docstring for the strategy. Never raises; an unrecognized
    term normalizes to its own lowercased text with UNKNOWN status."""
    lowered = raw_text.strip().lower()
    if not lowered:
        return "", EntityNormalizationStatus.UNKNOWN, []

    if lowered in AMBIGUOUS_ABBREVIATIONS:
        return lowered, EntityNormalizationStatus.AMBIGUOUS, list(AMBIGUOUS_ABBREVIATIONS[lowered])

    if lowered in SYNONYMS:
        return lowered, EntityNormalizationStatus.EXACT_MATCH, list(SYNONYMS[lowered])

    if lowered in _SYNONYM_TO_CANONICAL:
        canonical = _SYNONYM_TO_CANONICAL[lowered]
        return canonical, EntityNormalizationStatus.SYNONYM_MATCH, list(SYNONYMS[canonical])

    fuzzy = _fuzzy_match(lowered)
    if fuzzy is not None:
        return fuzzy, EntityNormalizationStatus.FUZZY_MATCH, list(SYNONYMS.get(fuzzy, ()))

    return lowered, EntityNormalizationStatus.UNKNOWN, []


def _fuzzy_match(lowered: str) -> Optional[str]:
    """Deterministic containment check only — no edit-distance/embedding
    similarity (see module docstring)."""
    for canonical in SYNONYMS:
        if canonical in lowered or lowered in canonical:
            return canonical
    return None
