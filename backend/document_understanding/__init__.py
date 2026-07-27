"""Document Understanding Engine — see pipeline.py's module docstring
for the full stage diagram and graceful-degradation design.

Only DocumentUnderstandingPipeline, the enums, and the models are
exported here. Deliberately no module-level convenience function (unlike
backend.processing.process_pdf()): the whole point of this package's
Public API is exactly one entry point —
`DocumentUnderstandingPipeline().process(path)` already is one line, a
second wrapper function would just be another name for the same call.
Future callers needing a custom stage implementation (e.g. a DOCX
parser) import the relevant Base* interface from .interfaces directly —
not re-exported here since this package's own stages are the only
current implementers and nothing else in this codebase constructs one
today (see interfaces.py's own module docstring on avoiding
unnecessary abstraction).

This is Phase 1 (Document Understanding) only — no classification,
domain routing, medical understanding, evidence grading, prompt
generation, or LLM/AI calls happen anywhere in this package. See
docs/architecture (or the originating task) for later phases that
consume ProcessedDocument.
"""

from .enums import DocumentFormat, DocumentLanguage, ExtractionStatus, HeadingType, QualityLevel, SectionType
from .models import (
    DocumentMetadata,
    DocumentQuality,
    DocumentStatistics,
    DocumentStructure,
    EvidenceReference,
    HeadingCandidate,
    LanguageDetectionResult,
    NormalizedHeading,
    PageOffset,
    ParsedDocument,
    ProcessedDocument,
    StageLog,
)
from .pipeline import DocumentUnderstandingPipeline

__all__ = [
    "DocumentUnderstandingPipeline",
    # enums
    "DocumentFormat",
    "DocumentLanguage",
    "ExtractionStatus",
    "HeadingType",
    "QualityLevel",
    "SectionType",
    # models
    "DocumentMetadata",
    "DocumentQuality",
    "DocumentStatistics",
    "DocumentStructure",
    "EvidenceReference",
    "HeadingCandidate",
    "LanguageDetectionResult",
    "NormalizedHeading",
    "PageOffset",
    "ParsedDocument",
    "ProcessedDocument",
    "StageLog",
]
