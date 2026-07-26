"""Reporting guideline classification — CONSORT, PRISMA, STROBE, etc. No
pass1 equivalent (see package docstring). Combines direct keyword/
checklist-name matches with corroboration from the document's already-
classified study_design and document_type (see keywords.py's
STUDY_DESIGN_TO_REPORTING_GUIDELINE/DOCUMENT_TYPE_TO_REPORTING_GUIDELINE)
— the same "use an already-classified label as extra corroborating
evidence" pattern backend.classification.pass1.publication.
PublicationTypeClassifier uses with document_type. Corroboration matters
because a document can legitimately follow CONSORT without the word
"CONSORT" ever appearing in the extracted body text (e.g. it was only
named in a supplementary checklist file, not the article itself).

Never infers ReportingGuideline.NONE (e.g. "an editorial needs no
guideline") — that's a judgment call about which document types are
exempt, out of scope for a detector whose job is only to report evidence
for a guideline actually being followed; it falls back to UNKNOWN like
every other detector when no evidence clears the confidence threshold.
"""

from typing import Optional, TypeVar

from backend.classification.pass1.rules import SignalMatch, combine_signals, match_keywords
from backend.document_understanding.models import ProcessedDocument

from .confidence import active_sources, resolve
from .enums import DocumentType, ReportingGuideline, StudyDesign
from .interfaces import BaseReportingGuidelineDetector
from .keywords import (
    DOCUMENT_TYPE_TO_REPORTING_GUIDELINE,
    REPORTING_GUIDELINE_KEYWORDS,
    STUDY_DESIGN_TO_REPORTING_GUIDELINE,
)
from .models import ClassificationDecision
from .reasoning import build_decision

# Corroboration from an already-classified label is nearly as strong as a
# literal keyword match (see module docstring) — weighted close to it.
_KEYWORD_WEIGHT = 1.5
_STUDY_DESIGN_WEIGHT = 1.0
_DOCUMENT_TYPE_WEIGHT = 1.0

_Label = TypeVar("_Label")


class ReportingGuidelineDetector(BaseReportingGuidelineDetector):
    """Classifies which reporting guideline (if any) a document follows.
    New guidelines are recognized by adding an entry to keywords.py's
    REPORTING_GUIDELINE_KEYWORDS (and enums.ReportingGuideline) —
    nothing here changes.

    `study_design`/`document_type`, if the caller already ran those
    detectors (per pipeline.py's order), add corroborating evidence — see
    module docstring. Both optional: this still works standalone from
    keyword evidence alone."""

    def detect(
        self,
        document: ProcessedDocument,
        study_design: Optional[StudyDesign] = None,
        document_type: Optional[DocumentType] = None,
    ) -> ClassificationDecision:
        ranked, sources = self.rank(document, study_design=study_design, document_type=document_type)
        label, confidence = resolve(ranked, ReportingGuideline.UNKNOWN)
        return build_decision(label, confidence, sources, ReportingGuideline.UNKNOWN)

    def rank(
        self,
        document: ProcessedDocument,
        study_design: Optional[StudyDesign] = None,
        document_type: Optional[DocumentType] = None,
    ) -> tuple[list[tuple[ReportingGuideline, float]], list[dict[ReportingGuideline, SignalMatch]]]:
        """Every ReportingGuideline candidate that matched at least one
        signal, ranked descending by confidence, plus the raw per-source
        signal dicts — see document_type.py's rank() for why this is
        exposed separately from detect()."""
        text = _searchable_text(document)

        keyword_signals = match_keywords(text, REPORTING_GUIDELINE_KEYWORDS)
        study_design_signals = _corroboration_signal(study_design, STUDY_DESIGN_TO_REPORTING_GUIDELINE, "study_design")
        document_type_signals = _corroboration_signal(
            document_type, DOCUMENT_TYPE_TO_REPORTING_GUIDELINE, "document_type"
        )

        ranked, _, _ = combine_signals(
            *active_sources(
                (keyword_signals, _KEYWORD_WEIGHT),
                (study_design_signals, _STUDY_DESIGN_WEIGHT),
                (document_type_signals, _DOCUMENT_TYPE_WEIGHT),
            )
        )
        return ranked, [keyword_signals, study_design_signals, document_type_signals]


def _searchable_text(document: ProcessedDocument) -> str:
    return f"{document.metadata.title}\n{document.metadata.abstract}\n{document.full_text}"


def _corroboration_signal(
    classified_label: Optional[_Label],
    correlation_map: dict[_Label, ReportingGuideline],
    source_name: str,
) -> dict[ReportingGuideline, SignalMatch]:
    if classified_label is None:
        return {}
    guideline = correlation_map.get(classified_label)
    if guideline is None:
        return {}
    return {
        guideline: SignalMatch(
            label=guideline,
            weight=1.0,
            matched_terms=[classified_label.value],
            reasoning=f"{source_name} classified as {classified_label.value!r}, which corroborates {guideline.value!r}",
        )
    }
