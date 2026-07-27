"""Document type classification — research_article, case_report,
systematic_review, etc. Combines structural features Phase 1.1 already
computed (DocumentStructure.normalized_headings — no re-detection, no
re-parsing) with keyword matches over the document's own text. Scoring
itself is backend.classification.pass1.rules, composed not reimplemented
(see package docstring).
"""

from backend.classification.pass1.rules import SignalMatch, combine_signals, match_keywords, match_structural_features
from backend.document_understanding.models import ProcessedDocument

from .confidence import active_sources, resolve
from .enums import DocumentType
from .interfaces import BaseDocumentTypeDetector
from .keywords import DOCUMENT_TYPE_KEYWORDS, DOCUMENT_TYPE_STRUCTURAL_FEATURES
from .models import ClassificationDecision
from .reasoning import build_decision

# Keyword phrases like "case report" or "systematic review" are far more
# specific/decisive than a generic structural shape (many document types
# share "has an abstract and a discussion") — weighted higher accordingly
# (same weights backend.classification.pass1.type uses for the same
# reason).
_KEYWORD_WEIGHT = 2.0
_STRUCTURAL_WEIGHT = 1.0


class DocumentTypeDetector(BaseDocumentTypeDetector):
    """Classifies a ProcessedDocument's type from its structure and text
    content. New document types are recognized by adding an entry to
    keywords.py's DOCUMENT_TYPE_KEYWORDS (and optionally
    DOCUMENT_TYPE_STRUCTURAL_FEATURES, and enums.DocumentType) — nothing
    here changes."""

    def detect(self, document: ProcessedDocument) -> ClassificationDecision:
        ranked, sources = self.rank(document)
        label, confidence = resolve(ranked, DocumentType.UNKNOWN)
        return build_decision(label, confidence, sources, DocumentType.UNKNOWN)

    def rank(
        self, document: ProcessedDocument
    ) -> tuple[list[tuple[DocumentType, float]], list[dict[DocumentType, SignalMatch]]]:
        """Every DocumentType candidate that matched at least one signal,
        ranked descending by confidence, plus the raw per-source signal
        dicts detect() builds its ClassificationDecision from — exposed
        separately so pipeline.py can populate ClassificationResult.
        candidate_labels without re-running this detector's own matching."""
        text = _searchable_text(document)
        present_sections = set(document.structure.normalized_headings)

        keyword_signals = match_keywords(text, DOCUMENT_TYPE_KEYWORDS)
        structural_signals = match_structural_features(present_sections, DOCUMENT_TYPE_STRUCTURAL_FEATURES)

        ranked, _, _ = combine_signals(
            *active_sources(
                (keyword_signals, _KEYWORD_WEIGHT),
                (structural_signals, _STRUCTURAL_WEIGHT),
            )
        )
        return ranked, [keyword_signals, structural_signals]


def _searchable_text(document: ProcessedDocument) -> str:
    return f"{document.metadata.title}\n{document.metadata.abstract}\n{document.full_text}"
