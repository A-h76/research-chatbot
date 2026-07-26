"""Study design classification — RCT, cohort, benchmark, framework, etc.
No pass1 equivalent (see package docstring) — keyword-only, since the
label set spans both medical (RCT/cohort/...) and computer-science
(algorithm/benchmark/...) vocabularies with no single structural-feature
mapping that applies across both. Scoring itself is
backend.classification.pass1.rules, composed not reimplemented.
"""

from backend.classification.pass1.rules import SignalMatch, combine_signals, match_keywords
from backend.document_understanding.models import ProcessedDocument

from .confidence import resolve
from .enums import StudyDesign
from .interfaces import BaseStudyDesignDetector
from .keywords import STUDY_DESIGN_KEYWORDS
from .models import ClassificationDecision
from .reasoning import build_decision

_KEYWORD_WEIGHT = 1.0


class StudyDesignDetector(BaseStudyDesignDetector):
    """Classifies a ProcessedDocument's study design from its text
    content. New designs are recognized by adding an entry to
    keywords.py's STUDY_DESIGN_KEYWORDS (and enums.StudyDesign) —
    nothing here changes."""

    def detect(self, document: ProcessedDocument) -> ClassificationDecision:
        ranked, sources = self.rank(document)
        label, confidence = resolve(ranked, StudyDesign.UNKNOWN)
        return build_decision(label, confidence, sources, StudyDesign.UNKNOWN)

    def rank(
        self, document: ProcessedDocument
    ) -> tuple[list[tuple[StudyDesign, float]], list[dict[StudyDesign, SignalMatch]]]:
        """Every StudyDesign candidate that matched at least one signal,
        ranked descending by confidence, plus the raw per-source signal
        dicts — see document_type.py's rank() for why this is exposed
        separately from detect()."""
        text = _searchable_text(document)
        keyword_signals = match_keywords(text, STUDY_DESIGN_KEYWORDS)

        ranked, _, _ = combine_signals((keyword_signals, _KEYWORD_WEIGHT))
        return ranked, [keyword_signals]


def _searchable_text(document: ProcessedDocument) -> str:
    return f"{document.metadata.title}\n{document.metadata.abstract}\n{document.full_text}"
