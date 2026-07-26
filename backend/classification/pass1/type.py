"""Document type classification — research_article, clinical_guideline,
review, case_report, etc. Combines two signal sources: structural
features already computed by backend.processing (DocumentQuality's
has_methods/has_results/... flags) and keyword matches over the
document's text. See rules.py for the scoring mechanism.
"""

from backend.processing.models import ProcessedDocument

from .keywords import DOCUMENT_TYPE_KEYWORDS, DOCUMENT_TYPE_STRUCTURAL_FEATURES
from .models import DocumentTypeClassificationResult
from .rules import combine_signals, match_keywords, match_structural_features

# Keyword phrases like "case report" or "systematic review" are far more
# specific/decisive than a generic structural shape (many document types
# share "has an abstract and a discussion") — weighted higher accordingly.
_KEYWORD_WEIGHT = 2.0
_STRUCTURAL_WEIGHT = 1.0


class DocumentTypeClassifier:
    """Classifies a ProcessedDocument's type from its structure (which
    sections it has) and text content. New document types are recognized
    by adding an entry to keywords.py's DOCUMENT_TYPE_KEYWORDS (and
    optionally DOCUMENT_TYPE_STRUCTURAL_FEATURES, and to models.py's
    DOCUMENT_TYPES) — nothing here changes."""

    def classify(self, document: ProcessedDocument) -> DocumentTypeClassificationResult:
        text = f"{document.title}\n{document.abstract}\n{document.full_text}"

        keyword_signals = match_keywords(text, DOCUMENT_TYPE_KEYWORDS)
        structural_signals = match_structural_features(
            self._present_features(document), DOCUMENT_TYPE_STRUCTURAL_FEATURES
        )

        ranked, reasoning, matched_features = combine_signals(
            (keyword_signals, _KEYWORD_WEIGHT),
            (structural_signals, _STRUCTURAL_WEIGHT),
        )

        if not ranked:
            return DocumentTypeClassificationResult(
                primary_type="other",
                document_types=[("other", 0.0)],
                reasoning=["no document-type keyword or structural signal matched; falling back to 'other'"],
                matched_features={},
            )

        return DocumentTypeClassificationResult(
            primary_type=ranked[0][0],
            document_types=ranked,
            reasoning=reasoning,
            matched_features=matched_features,
        )

    @staticmethod
    def _present_features(document: ProcessedDocument) -> set[str]:
        quality = document.quality
        return {
            name
            for name in ("has_abstract", "has_methods", "has_results", "has_discussion", "has_references")
            if getattr(quality, name)
        }
