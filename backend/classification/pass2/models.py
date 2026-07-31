"""Dataclasses for Pass 2 classification — see package docstring.

ClassificationDecision.label is typed `str` (matching the task's own
Public API) but every detector in this package actually stores one of
this package's own Enum members there (DocumentType.RESEARCH_ARTICLE,
not the bare string "research_article") — each Enum subclasses `str`
too (see enums.py), so this costs nothing: `isinstance(x, str)` holds,
JSON serialization emits the plain value, and callers who want the
richer Enum type can still get it (`DocumentType(decision.label)`).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ClassificationDecision:
    """One detector's output for one label family.

    Attributes:
        label: The winning label (an Enum member — see module docstring
            — or that family's own UNKNOWN/NONE member if nothing cleared
            the confidence threshold; see confidence.py).
        confidence: 0.0-1.0, this label's own aggregated score.
        evidence: Human-readable strings, each naming one concrete signal
            that supported `label` (a matched keyword, venue, or
            structural feature) — the audit trail, not a summary.
        reasoning: One human-readable sentence summarizing the decision,
            or None when there was nothing to summarize (no evidence at
            all — the fallback-to-UNKNOWN case).
    """

    label: str
    confidence: float
    evidence: list[str]
    reasoning: Optional[str]


@dataclass
class ClassificationResult:
    """DocumentClassificationPipeline's output for one ProcessedDocument.

    Attributes:
        document_type: See document_type.py.
        domain: See domain.py.
        study_design: See study_design.py.
        reporting_guideline: See reporting_guideline.py.
        detected_keywords: Domain subject-matter keyword phrases found in
            the document (not document-type / study-design / reporting
            classifier chrome) — used as Primary Topics / key_themes.
        candidate_labels: Every label any detector considered (across all
            four families), keyed by that label's own string value, with
            its own confidence — not just the four winners; a caller
            wanting the runner-up domain/study-design/etc. reads this
            rather than re-running detection.
        warnings: Non-fatal issues (e.g. a detector's input was too
            sparse to classify confidently) — never raised, always
            surfaced here instead (see pipeline.py's module docstring).
        processing_time_ms: Wall-clock time for the whole process() call.
        pipeline_version: This extraction logic's version — bump when a
            keyword list or scoring rule changes.
    """

    document_type: ClassificationDecision
    domain: ClassificationDecision
    study_design: ClassificationDecision
    reporting_guideline: ClassificationDecision
    detected_keywords: list[str]
    candidate_labels: dict[str, float]
    warnings: list[str]
    processing_time_ms: float
    pipeline_version: str
