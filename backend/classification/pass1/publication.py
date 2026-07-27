"""Publication type classification — journal_article, conference_paper,
thesis, preprint, etc. Runs last in the Pass 1 pipeline (see package
__init__.py), so it can use the already-classified document_type as an
extra corroborating signal alongside venue and content keywords.
"""

from backend.processing.models import ProcessedDocument

from .keywords import DOCUMENT_TYPE_TO_PUBLICATION_TYPE, PUBLICATION_TYPE_KEYWORDS, PUBLICATION_TYPE_VENUES
from .models import PublicationTypeClassificationResult
from .rules import SignalMatch, combine_signals, match_keywords, match_venue

# Venue names are the least ambiguous signal (a venue literally named
# "NeurIPS" is essentially conclusive); the already-classified
# document_type is next (it's itself the output of a whole other
# classifier, not a raw keyword); body-text keywords are weakest (a
# mention of "arxiv" as a citation, not necessarily this document's own
# host).
_VENUE_WEIGHT = 2.0
_DOCUMENT_TYPE_WEIGHT = 1.5
_KEYWORD_WEIGHT = 1.0


class PublicationTypeClassifier:
    """Classifies a ProcessedDocument's publication type from its venue,
    text content, and (if the caller already ran DocumentTypeClassifier,
    per the Pass 1 pipeline order) its classified document_type. New
    publication types are recognized by adding an entry to keywords.py's
    PUBLICATION_TYPE_VENUES/PUBLICATION_TYPE_KEYWORDS (and to models.py's
    PUBLICATION_TYPES) — nothing here changes."""

    def classify(
        self, document: ProcessedDocument, document_type: str = "other"
    ) -> PublicationTypeClassificationResult:
        text = f"{document.title}\n{document.abstract}\n{document.full_text}"

        venue_signals = match_venue(document.venue, PUBLICATION_TYPE_VENUES)
        keyword_signals = match_keywords(text, PUBLICATION_TYPE_KEYWORDS)
        document_type_signals = self._document_type_signal(document_type)

        ranked, reasoning, matched_features = combine_signals(
            (venue_signals, _VENUE_WEIGHT),
            (document_type_signals, _DOCUMENT_TYPE_WEIGHT),
            (keyword_signals, _KEYWORD_WEIGHT),
        )

        if not ranked:
            return PublicationTypeClassificationResult(
                publication_type="other",
                confidence=0.0,
                reasoning=["no venue, keyword, or document-type signal matched; falling back to 'other'"],
                matched_features={},
            )

        publication_type, confidence = ranked[0]
        return PublicationTypeClassificationResult(
            publication_type=publication_type,
            confidence=confidence,
            reasoning=reasoning,
            matched_features=matched_features,
        )

    @staticmethod
    def _document_type_signal(document_type: str) -> dict[str, SignalMatch]:
        publication_type = DOCUMENT_TYPE_TO_PUBLICATION_TYPE.get(document_type)
        if not publication_type:
            return {}
        return {
            publication_type: SignalMatch(
                label=publication_type,
                weight=1.0,
                matched_terms=[document_type],
                reasoning=f"document_type classified as {document_type!r}, which maps to publication_type {publication_type!r}",
            )
        }
