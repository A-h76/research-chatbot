"""DocumentClassificationPipeline — the package's one public entry point.

    ProcessedDocument (Phase 1.1)
        |
        v
    Validators               (validators.py)         -- input validation, never re-parses
        |
        v
    DocumentTypeDetector      (document_type.py)
        |
        v
    DomainDetector            (domain.py)
        |
        v
    StudyDesignDetector       (study_design.py)
        |
        v
    ReportingGuidelineDetector (reporting_guideline.py) -- uses study_design + document_type as corroboration
        |
        v
    ClassificationResult      (models.py)

Every detector call is wrapped in the same lightweight graceful-
degradation guard: an exception is caught, turned into a warning, and
substituted with a neutral UNKNOWN ClassificationDecision for that
family, so a bug in one detector's regex/keyword logic can never take
down classification for the other three (see _run_detector()). Each
detector already degrades to its own family's UNKNOWN member internally
on low-confidence evidence (confidence.py's threshold) — this is the
outer safety net for a detector that raises outright, the same two-layer
design backend.document_understanding.pipeline uses.

No re-parsing, no re-extraction: every detector reads only
ProcessedDocument's already-computed fields (metadata, structure,
full_text) — nothing here touches a PDF, re-runs Phase 1.1's parser, or
re-derives anything Phase 1.1 already produced. pass1 (Phase 1's own
classifier, consuming backend.processing's differently-shaped
ProcessedDocument) is untouched and unrelated to this pipeline.
"""

import time
from typing import Callable, Optional, TypeVar

from backend.document_understanding.models import ProcessedDocument

from .document_type import DocumentTypeDetector
from .domain import DomainDetector
from .enums import DocumentType, ReportingGuideline, ScientificDomain, StudyDesign
from .interfaces import (
    BaseDocumentTypeDetector,
    BaseDomainDetector,
    BaseReportingGuidelineDetector,
    BaseStudyDesignDetector,
)
from .keywords import extract_detected_keywords
from .models import ClassificationDecision, ClassificationResult
from .reporting_guideline import ReportingGuidelineDetector
from .study_design import StudyDesignDetector
from .validators import require_processed_document, validate_document

# This extraction logic's version — bump when a keyword list or scoring
# rule changes (matches backend.document_understanding.pipeline's
# PIPELINE_VERSION convention).
PIPELINE_VERSION = "1.0.1"

_Label = TypeVar("_Label")


class DocumentClassificationPipeline:
    """Coordinates all four detectors behind one method, process(). All
    internal components are constructor-injected with working defaults —
    a future caller (tests, or a future ML/LLM-backed detector) supplies
    its own implementation of the relevant Base*Detector interface
    instead of subclassing or monkeypatching this class."""

    def __init__(
        self,
        document_type_detector: Optional[BaseDocumentTypeDetector] = None,
        domain_detector: Optional[BaseDomainDetector] = None,
        study_design_detector: Optional[BaseStudyDesignDetector] = None,
        reporting_guideline_detector: Optional[BaseReportingGuidelineDetector] = None,
    ) -> None:
        self._document_type_detector = document_type_detector or DocumentTypeDetector()
        self._domain_detector = domain_detector or DomainDetector()
        self._study_design_detector = study_design_detector or StudyDesignDetector()
        self._reporting_guideline_detector = reporting_guideline_detector or ReportingGuidelineDetector()

    def process(self, document: ProcessedDocument) -> ClassificationResult:
        """Classifies `document` (Phase 1.1's ProcessedDocument) and
        returns one ClassificationResult — never raises for a
        classification-quality problem (see module docstring); only
        raises if `document` isn't actually a ProcessedDocument at all
        (a caller bug, not a document-quality problem)."""
        require_processed_document(document)
        start = time.perf_counter()
        warnings = validate_document(document)

        document_type_decision = self._run_detector(
            "document_type", lambda: self._document_type_detector.detect(document), DocumentType.UNKNOWN, warnings
        )
        domain_decision = self._run_detector(
            "domain", lambda: self._domain_detector.detect(document), ScientificDomain.UNKNOWN, warnings
        )
        study_design_decision = self._run_detector(
            "study_design", lambda: self._study_design_detector.detect(document), StudyDesign.UNKNOWN, warnings
        )
        reporting_guideline_decision = self._run_detector(
            "reporting_guideline",
            lambda: self._reporting_guideline_detector.detect(
                document,
                study_design=study_design_decision.label,
                document_type=document_type_decision.label,
            ),
            ReportingGuideline.UNKNOWN,
            warnings,
        )

        candidate_labels = self._candidate_labels(document, study_design_decision, document_type_decision, warnings)
        detected_keywords = self._detected_keywords(document, warnings)

        return ClassificationResult(
            document_type=document_type_decision,
            domain=domain_decision,
            study_design=study_design_decision,
            reporting_guideline=reporting_guideline_decision,
            detected_keywords=detected_keywords,
            candidate_labels=candidate_labels,
            warnings=warnings,
            processing_time_ms=(time.perf_counter() - start) * 1000,
            pipeline_version=PIPELINE_VERSION,
        )

    def _candidate_labels(
        self,
        document: ProcessedDocument,
        study_design_decision: ClassificationDecision,
        document_type_decision: ClassificationDecision,
        warnings: list[str],
    ) -> dict[str, float]:
        """Every label any detector considered (not just the four
        winners), namespaced by family ("document_type.research_article",
        "study_design.rct", ...) since the four label sets share some
        string values (e.g. both DocumentType and StudyDesign have a
        "survey" member, and since every enum here also subclasses str,
        an un-namespaced dict would silently let one family's entry
        overwrite another's). Relies on each detector's own rank()
        (beyond the strict BaseXDetector.detect() interface — see
        document_type.py) being available; a detector that only
        implements detect() simply contributes nothing here, degrading
        to an empty dict rather than raising."""
        try:
            document_type_ranked, _ = self._document_type_detector.rank(document)
            domain_ranked, _ = self._domain_detector.rank(document)
            study_design_ranked, _ = self._study_design_detector.rank(document)
            reporting_guideline_ranked, _ = self._reporting_guideline_detector.rank(
                document,
                study_design=study_design_decision.label,
                document_type=document_type_decision.label,
            )
        except Exception as exc:  # noqa: BLE001 -- optional enrichment, never fatal
            warnings.append(f"candidate_labels aggregation failed: {exc}")
            return {}

        candidates: dict[str, float] = {}
        for family, ranked in (
            ("document_type", document_type_ranked),
            ("domain", domain_ranked),
            ("study_design", study_design_ranked),
            ("reporting_guideline", reporting_guideline_ranked),
        ):
            for label, score in ranked:
                candidates[f"{family}.{label.value}"] = score
        return candidates

    @staticmethod
    def _detected_keywords(document: ProcessedDocument, warnings: list[str]) -> list[str]:
        try:
            return extract_detected_keywords(document)
        except Exception as exc:  # noqa: BLE001 -- optional enrichment, never fatal
            warnings.append(f"keyword extraction failed: {exc}")
            return []

    @staticmethod
    def _run_detector(
        name: str,
        fn: Callable[[], ClassificationDecision],
        unknown_label: _Label,
        warnings: list[str],
    ) -> ClassificationDecision:
        """The one graceful-degradation boundary for detector calls (see
        module docstring) — catches any exception a detector raises,
        substituting a neutral UNKNOWN decision so the other three
        detectors and the rest of process() are unaffected."""
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 -- intentional catch-all, see docstring above
            warnings.append(f"{name} detector failed: {exc}")
            return ClassificationDecision(label=unknown_label, confidence=0.0, evidence=[], reasoning=None)
