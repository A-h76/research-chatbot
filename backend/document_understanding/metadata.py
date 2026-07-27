"""Bibliographic metadata extraction.

Composes backend.processing.metadata.MetadataExtractor (see package
docstring's reuse table) — its 7 fields (title/authors/venue/year/doi/
abstract/keywords) are a strict subset of DocumentMetadata's own, so
nothing it already extracts is duplicated here. This module adds
identifier extraction (PMID/PMCID/arXiv ID/ClinicalTrials.gov ID —
unambiguous regex patterns, same "high confidence on a structural match"
reasoning as the legacy DOI pattern), a journal/conference bucketing of
the legacy venue string, and a best-effort license heuristic.

subtitle, affiliations, corresponding_author, and publication_type are
always left empty/None: no reliable layout-independent marker exists for
any of them the way a DOI/PMID/arXiv-ID pattern is unambiguous (a real
extraction would need PDF layout/font analysis, out of scope here — see
DocumentMetadata's own docstring).
"""

import re
from typing import Optional

from backend.processing.metadata import MetadataExtractor as _LegacyMetadataExtractor

from .enums import DocumentLanguage
from .interfaces import BaseMetadataExtractor
from .models import DocumentMetadata, DocumentStructure, ParsedDocument
from .utils import to_legacy_parsed, to_legacy_sections

# PubMed ID: an all-digit identifier, always introduced by a "PMID" label
# in body text (never appears unlabeled — unlike a DOI, bare digits alone
# would be far too ambiguous to match on).
_PMID_RE = re.compile(r"PMID:?\s*(\d{1,9})", re.IGNORECASE)

# PubMed Central ID: always the literal "PMC" prefix + digits.
_PMCID_RE = re.compile(r"\b(PMC\d{6,9})\b", re.IGNORECASE)

# arXiv identifier, modern "YYMM.NNNNN" scheme, optionally versioned.
_ARXIV_RE = re.compile(r"arXiv:\s*(\d{4}\.\d{4,5}(?:v\d+)?)", re.IGNORECASE)

# ClinicalTrials.gov registration number: literal "NCT" + 8 digits.
_NCT_RE = re.compile(r"\b(NCT\d{8})\b")

# Common license phrasing in academic papers/preprints — not a real
# license-clause parser, just enough to catch the phrase itself.
_LICENSE_RE = re.compile(
    r"(Creative Commons[^.\n]{0,80}|CC[\s-]?BY(?:[\s-](?:NC|ND|SA))*(?:\s+\d\.\d)?|All rights reserved)",
    re.IGNORECASE,
)

# Substrings that bucket an already-detected venue string as a journal vs
# a conference — checked case-insensitively, in this priority order
# (conference markers first: "transactions on" and "journal" can both
# appear in a conference's own long-form name, e.g. "IEEE Transactions
# on ... Symposium", so a conference marker hit should win).
_CONFERENCE_MARKERS: tuple[str, ...] = ("conference", "proceedings", "symposium")
_JOURNAL_MARKERS: tuple[str, ...] = ("journal", "transactions on")

_LICENSE_CONFIDENCE = 0.4
_IDENTIFIER_CONFIDENCE = 0.9


class MetadataExtractor(BaseMetadataExtractor):
    """Extracts DocumentMetadata by composing the legacy extractor for
    the fields it already handles, plus new identifier/venue/license
    heuristics for the rest."""

    def __init__(self) -> None:
        self._legacy = _LegacyMetadataExtractor()

    def extract(
        self,
        parsed: ParsedDocument,
        structure: Optional[DocumentStructure],
        language: DocumentLanguage,
    ) -> DocumentMetadata:
        legacy_parsed = to_legacy_parsed(parsed)
        legacy_sections = to_legacy_sections(structure) if structure is not None else None
        legacy = self._legacy.extract(legacy_parsed, legacy_sections)

        confidence = dict(legacy.confidence)
        reasoning = dict(legacy.reasoning)

        pmid = self._match(_PMID_RE, parsed.raw_text, "pmid", "PMID label", confidence, reasoning)
        pmcid = self._match(_PMCID_RE, parsed.raw_text, "pmcid", "PMCID pattern", confidence, reasoning)
        arxiv_id = self._match(_ARXIV_RE, parsed.raw_text, "arxiv_id", "arXiv ID pattern", confidence, reasoning)
        clinical_trials_id = self._match(
            _NCT_RE, parsed.raw_text, "clinical_trials_id", "ClinicalTrials.gov ID pattern", confidence, reasoning
        )
        license_ = self._match(
            _LICENSE_RE,
            parsed.raw_text,
            "license",
            "license phrase",
            confidence,
            reasoning,
            own_confidence=_LICENSE_CONFIDENCE,
        )
        journal, conference = self._bucket_venue(legacy.venue, confidence.get("venue", 0.0), confidence, reasoning)

        return DocumentMetadata(
            title=legacy.title,
            subtitle=None,
            authors=legacy.authors,
            affiliations=[],
            corresponding_author=None,
            venue=legacy.venue,
            journal=journal,
            conference=conference,
            doi=legacy.doi,
            pmid=pmid,
            pmcid=pmcid,
            arxiv_id=arxiv_id,
            clinical_trials_id=clinical_trials_id,
            publication_year=legacy.year,
            publication_type=None,
            keywords=legacy.keywords,
            abstract=legacy.abstract,
            language=language,
            license=license_,
            raw_metadata=dict(parsed.pdf_metadata),
            confidence=confidence,
            reasoning=reasoning,
        )

    @staticmethod
    def _match(
        pattern: re.Pattern,
        text: str,
        field: str,
        label: str,
        confidence: dict[str, float],
        reasoning: dict[str, str],
        own_confidence: float = _IDENTIFIER_CONFIDENCE,
    ) -> Optional[str]:
        match = pattern.search(text)
        if match:
            confidence[field] = own_confidence
            reasoning[field] = f"regex match on {label}"
            return match.group(1) if match.groups() else match.group(0)

        confidence[field] = 0.0
        reasoning[field] = f"no {label} found"
        return None

    @staticmethod
    def _bucket_venue(
        venue: str,
        venue_confidence: float,
        confidence: dict[str, float],
        reasoning: dict[str, str],
    ) -> tuple[Optional[str], Optional[str]]:
        lowered = venue.lower()

        if venue and any(marker in lowered for marker in _CONFERENCE_MARKERS):
            confidence["conference"] = venue_confidence
            confidence["journal"] = 0.0
            reasoning["conference"] = "venue text matched a conference/proceedings marker"
            reasoning["journal"] = "venue was bucketed as a conference, not a journal"
            return None, venue

        if venue and any(marker in lowered for marker in _JOURNAL_MARKERS):
            confidence["journal"] = venue_confidence
            confidence["conference"] = 0.0
            reasoning["journal"] = "venue text matched a journal marker"
            reasoning["conference"] = "venue was bucketed as a journal, not a conference"
            return venue, None

        confidence["journal"] = 0.0
        confidence["conference"] = 0.0
        reasoning["journal"] = "no venue detected or it matched neither a journal nor conference marker"
        reasoning["conference"] = "no venue detected or it matched neither a journal nor conference marker"
        return None, None
