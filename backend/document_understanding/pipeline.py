"""DocumentUnderstandingPipeline — the package's one public entry point.

    Uploaded PDF
        |
        v
    DocumentParser        (parser.py)         -- raw text, page offsets, native metadata
        |
        v
    StopwordLanguageDetector (language.py)     -- primary language
        |
        v
    SectionBuilder         (sections.py)       -- headings -> DocumentStructure
        |          (via headings.py + normalization.py)
        v
    MetadataExtractor       (metadata.py)      -- DocumentMetadata
        |
        v
    StatisticsCalculator    (statistics.py)    -- DocumentStatistics
        |
        v
    QualityAssessor          (quality.py)      -- DocumentQuality
        |
        v
    TraceabilityBuilder       (traceability.py) -- evidence dict
        |
        v
    ProcessedDocument          (models.py)      -- structured output

Graceful degradation is two layers (see exceptions.py's module docstring
for the internal bookkeeping type this uses):
  1. Field-level: every extractor method throughout this package already
     returns an empty/0.0-confidence value on "not found" rather than
     raising (established pattern, see e.g. metadata.py/language.py).
  2. Stage-level: this module's own _run_stage() wraps each of the 7
     stage calls below, times it, catches any exception it raises into
     that stage's own StageLog(status=FAILED, errors=[str(exc)]), and
     substitutes a neutral empty default so the pipeline always continues
     to the next stage. One guard, not one per stage, so a stage added
     later can't forget it. This is what actually implements this
     package's "never crash, return structured warnings instead"
     requirement for corrupted/encrypted/unsupported-format documents
     (see parser.py's module docstring for exactly which of those it
     detects itself vs. lets propagate up to here).

process() never raises for a document-shaped problem (corrupt file,
encrypted file, unsupported format, empty/garbled text, missing
metadata) — every one of those degrades to a ProcessedDocument with low
confidence/populated warnings-errors instead. It can still raise for a
genuinely broken call (e.g. document_path doesn't exist as a str/Path at
all) — that is a caller bug, not a document quality problem, and isn't
swallowed.
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, TypeVar

from .enums import DocumentFormat, DocumentLanguage, ExtractionStatus
from .headings import HeadingDetector
from .interfaces import (
    BaseHeadingDetector,
    BaseHeadingNormalizer,
    BaseLanguageDetector,
    BaseMetadataExtractor,
    BaseParser,
    BaseQualityAssessor,
    BaseSectionBuilder,
    BaseTraceabilityBuilder,
)
from .language import StopwordLanguageDetector
from .metadata import MetadataExtractor
from .models import (
    DocumentMetadata,
    DocumentQuality,
    DocumentStatistics,
    DocumentStructure,
    LanguageDetectionResult,
    ParsedDocument,
    ProcessedDocument,
    StageLog,
)
from .normalization import HeadingNormalizer
from .parser import DocumentParser
from .quality import QualityAssessor
from .sections import SectionBuilder
from .statistics import StatisticsCalculator
from .traceability import TraceabilityBuilder

logger = logging.getLogger("backend.document_understanding")

# This dataclass's own shape — bump on ProcessedDocument/sub-model field
# additions or removals.
SCHEMA_VERSION = "1.0.0"

# The extraction logic's behavior — bump when a heuristic/regex changes
# even if the shape (SCHEMA_VERSION) is stable.
PIPELINE_VERSION = "1.0.0"

_StageResult = TypeVar("_StageResult")


class DocumentUnderstandingPipeline:
    """Coordinates every stage in this package behind one method,
    process(). All internal components are constructor-injected with
    working defaults — future callers (tests, or a future ML/LLM-backed
    stage) supply their own implementation of the relevant Base* interface
    instead of subclassing or monkeypatching this class."""

    def __init__(
        self,
        parser: Optional[BaseParser] = None,
        language_detector: Optional[BaseLanguageDetector] = None,
        heading_detector: Optional[BaseHeadingDetector] = None,
        heading_normalizer: Optional[BaseHeadingNormalizer] = None,
        section_builder: Optional[BaseSectionBuilder] = None,
        statistics_calculator: Optional[StatisticsCalculator] = None,
        metadata_extractor: Optional[BaseMetadataExtractor] = None,
        quality_assessor: Optional[BaseQualityAssessor] = None,
        traceability_builder: Optional[BaseTraceabilityBuilder] = None,
    ) -> None:
        self._parser = parser or DocumentParser()
        self._language_detector = language_detector or StopwordLanguageDetector()
        normalizer = heading_normalizer or HeadingNormalizer()
        detector = heading_detector or HeadingDetector()
        self._section_builder = section_builder or SectionBuilder(detector, normalizer)
        self._statistics_calculator = statistics_calculator or StatisticsCalculator()
        self._metadata_extractor = metadata_extractor or MetadataExtractor()
        self._quality_assessor = quality_assessor or QualityAssessor()
        self._traceability_builder = traceability_builder or TraceabilityBuilder()

    def process(self, document_path: Path, metadata: Optional[dict] = None) -> ProcessedDocument:
        """Runs the full pipeline (see module docstring's diagram) and
        returns one ProcessedDocument — never raises for a document-
        shaped problem (see module docstring).

        `metadata`, if given, may carry an "id" key to use as
        ProcessedDocument.id; a fresh uuid4() is minted if absent or not
        given — this package has no database dependency and no notion of
        "the" identity for a document beyond what its caller tracks.
        """
        start = time.perf_counter()
        caller_metadata = metadata or {}
        document_id = str(caller_metadata.get("id") or uuid.uuid4())

        parsed, parser_log = self._run_stage(
            "parser", document_id, lambda: self._parser.parse(document_path), ParsedDocument()
        )
        if parser_log.status == ExtractionStatus.SUCCESS and parsed.format != DocumentFormat.PDF:
            # Structural, not a caught exception (see parser.py's module
            # docstring) — parser.py returned normally, this just names
            # what it returned.
            parser_log.status = ExtractionStatus.PARTIAL
            parser_log.warnings.append(f"unsupported document format: {parsed.format.value}")

        language_result, language_log = self._run_stage(
            "language",
            document_id,
            lambda: self._language_detector.detect(parsed.raw_text),
            LanguageDetectionResult(DocumentLanguage.UNKNOWN, 0.0, "stage failed, defaulting to unknown"),
        )
        language_log.confidence = language_result.confidence

        structure, structure_log = self._run_stage(
            "sections", document_id, lambda: self._section_builder.build(parsed.raw_text), DocumentStructure()
        )
        structure_log.confidence = structure.confidence

        doc_metadata, metadata_log = self._run_stage(
            "metadata",
            document_id,
            lambda: self._metadata_extractor.extract(parsed, structure, language_result.language),
            DocumentMetadata(),
        )
        if doc_metadata.confidence:
            metadata_log.confidence = sum(doc_metadata.confidence.values()) / len(doc_metadata.confidence)

        statistics, statistics_log = self._run_stage(
            "statistics",
            document_id,
            lambda: self._statistics_calculator.calculate(parsed, structure),
            DocumentStatistics(),
        )

        quality, quality_log = self._run_stage(
            "quality",
            document_id,
            lambda: self._quality_assessor.assess(parsed, doc_metadata, structure, statistics),
            DocumentQuality(),
        )
        quality_log.confidence = quality.confidence
        quality_log.warnings.extend(quality.warnings)
        quality_log.errors.extend(quality.errors)

        traceability, traceability_log = self._run_stage(
            "traceability",
            document_id,
            lambda: self._traceability_builder.build(parsed, doc_metadata, structure),
            {},
        )
        if traceability:
            traceability_log.confidence = sum(ref.confidence for ref in traceability.values()) / len(traceability)

        stage_logs = [
            parser_log,
            language_log,
            structure_log,
            metadata_log,
            statistics_log,
            quality_log,
            traceability_log,
        ]
        for log in stage_logs:
            self._emit_log(log)

        return ProcessedDocument(
            id=document_id,
            metadata=doc_metadata,
            structure=structure,
            statistics=statistics,
            quality=quality,
            traceability=traceability,
            full_text=parsed.raw_text,
            schema_version=SCHEMA_VERSION,
            pipeline_version=PIPELINE_VERSION,
            processing_time_ms=(time.perf_counter() - start) * 1000,
            created_at=datetime.now(timezone.utc),
            stage_logs=stage_logs,
            page_ranges=parsed.page_ranges,
        )

    @staticmethod
    def _run_stage(
        stage: str,
        document_id: str,
        fn: Callable[[], _StageResult],
        default: _StageResult,
    ) -> tuple[_StageResult, StageLog]:
        """The one graceful-degradation boundary (see module docstring,
        layer 2). Deliberately catches Exception broadly — this is the
        pipeline's documented safety net for "the document is broken in
        some way `fn` couldn't predict", not a substitute for the field-
        level handling every extractor already does for known failure
        modes."""
        started = time.perf_counter()
        result = default
        status = ExtractionStatus.SUCCESS
        errors: list[str] = []
        try:
            result = fn()
        except Exception as exc:  # noqa: BLE001 -- intentional catch-all, see docstring above
            status = ExtractionStatus.FAILED
            errors.append(str(exc))
            logger.warning("stage '%s' failed for document %s: %s", stage, document_id, exc)

        duration_ms = (time.perf_counter() - started) * 1000
        log = StageLog(
            stage=stage,
            document_id=document_id,
            duration_ms=duration_ms,
            status=status,
            confidence=None,
            warnings=[],
            errors=errors,
        )
        return result, log

    @staticmethod
    def _emit_log(log: StageLog) -> None:
        logger.info(
            "stage=%s document_id=%s duration_ms=%.1f status=%s confidence=%s warnings=%d errors=%d",
            log.stage,
            log.document_id,
            log.duration_ms,
            log.status.value,
            log.confidence,
            len(log.warnings),
            len(log.errors),
        )
