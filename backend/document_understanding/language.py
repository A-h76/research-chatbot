"""Deterministic language detection via stopword-frequency scoring.

Not real language identification (no n-gram model, no external library —
rule: "prefer deterministic algorithms... do not introduce unnecessary
third-party dependencies", and no language-detection package is already
a project dependency). This counts how many of each language's ~30 most
common function words appear in the text and picks the language with the
highest hit ratio. It will misclassify short excerpts, mixed-language
text, and any language not in _STOPWORDS below — DocumentLanguage.UNKNOWN
with confidence 0.0 is the honest, expected outcome for all of those, not
an error case. A real NLP/ML-backed detector is the documented future
extension point (see BaseLanguageDetector) if this ever isn't good enough.
"""

import re
from collections import Counter

from .enums import DocumentLanguage
from .interfaces import BaseLanguageDetector
from .models import LanguageDetectionResult

# ~30 of the most frequent function words per language — closed classes
# (articles, prepositions, conjunctions, pronouns), chosen because they
# recur constantly regardless of a document's subject matter, unlike
# content words. Deliberately small: this is a coarse heuristic, not an
# attempt at real coverage.
_STOPWORDS: dict[DocumentLanguage, frozenset[str]] = {
    DocumentLanguage.ENGLISH: frozenset(
        "the of and to in is that for on with as are by this be from at an or which "
        "we have has was were been their its these those".split()
    ),
    DocumentLanguage.SPANISH: frozenset(
        "el la los las de que y en un una es por para con no se su al del como mas "
        "pero sus le ya o este esta entre cuando".split()
    ),
    DocumentLanguage.FRENCH: frozenset(
        "le la les de des et en un une est pour dans que qui sur avec ne se pas ce "
        "il elle nous vous ils du au mais ou par".split()
    ),
    DocumentLanguage.GERMAN: frozenset(
        "der die das und ist in zu den von mit auf fur dem nicht ein eine als auch "
        "es an im sich nach bei um aus wie oder wenn".split()
    ),
}

_WORD_RE = re.compile(r"[a-zA-ZÀ-ÿ]+")

# Below this many recognized-language tokens, any score is too noisy to
# trust — a two-word title match on a common stopword shouldn't be
# reported as a confident language detection.
_MIN_TOKENS_FOR_CONFIDENCE = 20


class StopwordLanguageDetector(BaseLanguageDetector):
    """Scores DocumentLanguage members by stopword-frequency overlap.
    See module docstring for the accuracy tradeoffs this accepts."""

    def detect(self, text: str) -> LanguageDetectionResult:
        tokens = [t.lower() for t in _WORD_RE.findall(text or "")]
        if len(tokens) < _MIN_TOKENS_FOR_CONFIDENCE:
            return LanguageDetectionResult(
                DocumentLanguage.UNKNOWN,
                0.0,
                f"too little text to classify ({len(tokens)} word(s), need at least {_MIN_TOKENS_FOR_CONFIDENCE})",
            )

        counts = Counter(tokens)
        total = len(tokens)
        scores: dict[DocumentLanguage, float] = {}
        for language, stopwords in _STOPWORDS.items():
            hits = sum(counts[word] for word in stopwords)
            scores[language] = hits / total

        best_language, best_score = max(scores.items(), key=lambda pair: pair[1])
        if best_score <= 0.0:
            return LanguageDetectionResult(
                DocumentLanguage.UNKNOWN, 0.0, "no recognized stopwords from any known language found"
            )

        # Scaled, not the raw ratio: a well-formed English paragraph
        # typically has ~30-40% stopword density, not 100% — treating
        # that density itself as "confidence" would cap out low even for
        # an unambiguous match.
        confidence = min(best_score / 0.35, 1.0)
        return LanguageDetectionResult(
            best_language,
            confidence,
            f"stopword density {best_score:.0%} for {best_language.value} (highest among {len(scores)} known languages)",
        )
