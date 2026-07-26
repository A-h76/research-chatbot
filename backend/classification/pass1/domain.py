"""Domain classification — which academic field a document belongs to
(medical, computer_science, physics, ...). See rules.py for the scoring
mechanism this is built on, and keywords.py for the actual keyword/venue
data; this module only decides which signals to check and how heavily
to weight each one relative to the others.
"""

from backend.processing.models import ProcessedDocument

from .keywords import DOMAIN_KEYWORDS, DOMAIN_VENUES
from .models import DomainClassificationResult
from .rules import combine_signals, match_keywords, match_venue

# Venue is a much stronger, less ambiguous signal than body-text keywords
# (see match_venue()'s own docstring) — weighted higher so a venue match
# alone can outrank a handful of keyword hits for a different domain.
_VENUE_WEIGHT = 2.0
_KEYWORD_WEIGHT = 1.0


class DomainClassifier:
    """Classifies a ProcessedDocument's academic domain from its venue
    and text content. New domains are recognized by adding an entry to
    keywords.py's DOMAIN_KEYWORDS/DOMAIN_VENUES (and to models.py's
    DOMAINS, for documentation/completeness) — nothing here changes."""

    def classify(self, document: ProcessedDocument) -> DomainClassificationResult:
        text = self._searchable_text(document)

        venue_signals = match_venue(document.venue, DOMAIN_VENUES)
        keyword_signals = match_keywords(text, DOMAIN_KEYWORDS)

        ranked, reasoning, matched_features = combine_signals(
            (venue_signals, _VENUE_WEIGHT),
            (keyword_signals, _KEYWORD_WEIGHT),
        )

        if not ranked:
            return DomainClassificationResult(
                primary_domain="other",
                domains=[("other", 0.0)],
                reasoning=["no domain keyword or venue signal matched; falling back to 'other'"],
                matched_features={},
            )

        return DomainClassificationResult(
            primary_domain=ranked[0][0],
            domains=ranked,
            reasoning=reasoning,
            matched_features=matched_features,
        )

    @staticmethod
    def _searchable_text(document: ProcessedDocument) -> str:
        return f"{document.title}\n{document.abstract}\n{document.full_text}"
