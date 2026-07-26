"""Scientific domain classification — medicine, computer_science, ai_ml,
etc. Combines a venue signal (metadata.venue/journal/conference) with
keyword matches over the document's own text. Scoring itself is
backend.classification.pass1.rules, composed not reimplemented (see
package docstring).
"""

from backend.classification.pass1.rules import SignalMatch, combine_signals, match_keywords, match_venue
from backend.document_understanding.models import ProcessedDocument

from .confidence import active_sources, resolve
from .enums import ScientificDomain
from .interfaces import BaseDomainDetector
from .keywords import DOMAIN_KEYWORDS, DOMAIN_VENUES
from .models import ClassificationDecision
from .reasoning import build_decision

# Venue is a much stronger, less ambiguous signal than body-text keywords
# (see pass1.rules.match_venue's own docstring) — weighted higher so a
# venue match alone can outrank a handful of keyword hits for a
# different domain (same weights backend.classification.pass1.domain
# uses).
_VENUE_WEIGHT = 2.0
_KEYWORD_WEIGHT = 1.0


class DomainDetector(BaseDomainDetector):
    """Classifies a ProcessedDocument's scientific domain from its venue
    and text content. New domains are recognized by adding an entry to
    keywords.py's DOMAIN_KEYWORDS/DOMAIN_VENUES (and enums.
    ScientificDomain) — nothing here changes."""

    def detect(self, document: ProcessedDocument) -> ClassificationDecision:
        ranked, sources = self.rank(document)
        label, confidence = resolve(ranked, ScientificDomain.UNKNOWN)
        return build_decision(label, confidence, sources, ScientificDomain.UNKNOWN)

    def rank(
        self, document: ProcessedDocument
    ) -> tuple[list[tuple[ScientificDomain, float]], list[dict[ScientificDomain, SignalMatch]]]:
        """Every ScientificDomain candidate that matched at least one
        signal, ranked descending by confidence, plus the raw per-source
        signal dicts — see document_type.py's rank() for why this is
        exposed separately from detect()."""
        text = _searchable_text(document)
        venue = _venue_text(document)

        venue_signals = match_venue(venue, DOMAIN_VENUES)
        keyword_signals = match_keywords(text, DOMAIN_KEYWORDS)

        ranked, _, _ = combine_signals(
            *active_sources(
                (venue_signals, _VENUE_WEIGHT),
                (keyword_signals, _KEYWORD_WEIGHT),
            )
        )
        return ranked, [venue_signals, keyword_signals]


def _searchable_text(document: ProcessedDocument) -> str:
    return f"{document.metadata.title}\n{document.metadata.abstract}\n{document.full_text}"


def _venue_text(document: ProcessedDocument) -> str:
    metadata = document.metadata
    return " ".join(part for part in (metadata.venue, metadata.journal, metadata.conference) if part)
