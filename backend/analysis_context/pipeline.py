"""AnalysisContextPipeline — the package's one public entry point.

    (ProcessedDocument, ClassificationResult)
        |
        v
    Validators            (validators.py)          -- input validation, never re-extracts
        |
        v
    DocumentProfiler       (document_profile.py)
    SectionProfiler        (section_profile.py)
    AnalysisProfiler       (analysis_profile.py)
    RoutingProfiler        (routing_profile.py)
    PromptProfiler         (prompt_profile.py)       -- each independent, no cross-profile input (see interfaces.py)
        |
        v
    QualityProfiler        (quality_profile.py)
    ConfidenceEngine        (confidence.py)
        |
        v
    AnalysisContext         (models.py)

Same graceful-degradation guard as backend.document_understanding.
pipeline and backend.classification.pass2.pipeline: each profiler call
is wrapped in _run_profiler(), which catches any exception into a
warning and substitutes a neutral, empty/UNKNOWN profile default so one
profiler's bug can never take down the other four (or the quality/
confidence steps, which always run against whatever profiles resulted).

No re-parsing, no re-classification: every profiler reads only
ProcessedDocument's and ClassificationResult's already-computed fields —
nothing here touches a PDF or re-runs Phase 1.1/1.2.
"""

import time
from typing import Callable, Optional, TypeVar

from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument

from .analysis_profile import AnalysisProfiler
from .confidence import compute_confidence
from .document_profile import DocumentProfiler
from .enums import AudienceType, ComplexityLevel, PromptFamily, PromptStrategy, RoutingDecision
from .interfaces import (
    BaseAnalysisProfiler,
    BaseDocumentProfiler,
    BasePromptProfiler,
    BaseRoutingProfiler,
    BaseSectionProfiler,
)
from .models import AnalysisContext, AnalysisProfile, DocumentProfile, PromptProfile, RoutingProfile, SectionProfile
from .prompt_profile import PromptProfiler
from .quality_profile import QualityProfiler
from .routing_profile import RoutingProfiler
from .section_profile import SectionProfiler
from .validators import require_valid_inputs, validate_inputs

# This extraction logic's version — bump when a routing/prompt/readiness
# rule changes (matches the PIPELINE_VERSION convention Phase 1.1 and
# Phase 1.2's own pipelines already use).
PIPELINE_VERSION = "1.0.0"

_Profile = TypeVar("_Profile")


class AnalysisContextPipeline:
    """Coordinates all five profilers plus quality/confidence scoring
    behind one method, process(). All internal components are
    constructor-injected with working defaults — a future caller (tests,
    or a future ML/LLM-backed profiler) supplies its own implementation
    of the relevant Base*Profiler interface instead of subclassing or
    monkeypatching this class."""

    def __init__(
        self,
        document_profiler: Optional[BaseDocumentProfiler] = None,
        section_profiler: Optional[BaseSectionProfiler] = None,
        analysis_profiler: Optional[BaseAnalysisProfiler] = None,
        routing_profiler: Optional[BaseRoutingProfiler] = None,
        prompt_profiler: Optional[BasePromptProfiler] = None,
        quality_profiler: Optional[QualityProfiler] = None,
    ) -> None:
        self._document_profiler = document_profiler or DocumentProfiler()
        self._section_profiler = section_profiler or SectionProfiler()
        self._analysis_profiler = analysis_profiler or AnalysisProfiler()
        self._routing_profiler = routing_profiler or RoutingProfiler()
        self._prompt_profiler = prompt_profiler or PromptProfiler()
        self._quality_profiler = quality_profiler or QualityProfiler()

    def process(self, document: ProcessedDocument, classification: ClassificationResult) -> AnalysisContext:
        """Builds an AnalysisContext from Phase 1.1's ProcessedDocument
        and Phase 1.2's ClassificationResult — never raises for an
        analysis-quality problem (see module docstring); only raises if
        either argument isn't the type it claims to be (a caller bug)."""
        require_valid_inputs(document, classification)
        start = time.perf_counter()
        warnings = validate_inputs(document, classification)

        document_profile = self._run_profiler(
            "document_profile",
            lambda: self._document_profiler.profile(document, classification),
            _default_document_profile(classification),
            warnings,
        )
        section_profile = self._run_profiler(
            "section_profile",
            lambda: self._section_profiler.profile(document, classification),
            SectionProfile(),
            warnings,
        )
        analysis_profile = self._run_profiler(
            "analysis_profile",
            lambda: self._analysis_profiler.profile(document, classification),
            AnalysisProfile(),
            warnings,
        )
        routing_profile = self._run_profiler(
            "routing_profile",
            lambda: self._routing_profiler.profile(document, classification),
            RoutingProfile(primary_routing=RoutingDecision.UNKNOWN),
            warnings,
        )
        prompt_profile = self._run_profiler(
            "prompt_profile",
            lambda: self._prompt_profiler.profile(document, classification),
            PromptProfile(prompt_family=PromptFamily.UNKNOWN, prompt_strategy=PromptStrategy.CLAIM_BASED),
            warnings,
        )

        quality_profile = self._quality_profiler.profile(document, classification)
        confidence = compute_confidence(
            document_profile, section_profile, analysis_profile, routing_profile, prompt_profile
        )

        return AnalysisContext(
            document_profile=document_profile,
            analysis_profile=analysis_profile,
            section_profile=section_profile,
            routing_profile=routing_profile,
            prompt_profile=prompt_profile,
            quality_profile=quality_profile,
            confidence=confidence,
            warnings=warnings,
            processing_time_ms=(time.perf_counter() - start) * 1000,
            pipeline_version=PIPELINE_VERSION,
        )

    @staticmethod
    def _run_profiler(
        name: str,
        fn: Callable[[], _Profile],
        default: _Profile,
        warnings: list[str],
    ) -> _Profile:
        """The one graceful-degradation boundary for profiler calls (see
        module docstring) — catches any exception a profiler raises,
        substituting a neutral default so the other profilers and the
        rest of process() are unaffected."""
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 -- intentional catch-all, see docstring above
            warnings.append(f"{name} profiler failed: {exc}")
            return default


def _default_document_profile(classification: ClassificationResult) -> DocumentProfile:
    """Falls back to classification's own already-decided labels (a
    plain read, not the profiler's own logic) plus UNKNOWN/0.0 for
    everything document_profile.py itself would have inferred."""
    return DocumentProfile(
        document_type=classification.document_type.label,
        domain=classification.domain.label,
        study_design=classification.study_design.label,
        reporting_guideline=None,
        intended_audience=AudienceType.UNKNOWN,
        complexity_level=ComplexityLevel.UNKNOWN,
        confidence=0.0,
    )
