"""Pass 2 Classification — Document Classification Engine.

Consumes backend.document_understanding.ProcessedDocument (Phase 1.1's
output) and returns a ClassificationResult: document_type, domain,
study_design, and reporting_guideline, each an evidence-backed
ClassificationDecision, plus a flat detected_keywords overview and every
candidate label any detector considered — see pipeline.py's module
docstring for the full stage diagram.

Distinct from pass1 (Pass 1: domain/document-type/publication-type,
built on backend.processing's differently-shaped ProcessedDocument) —
this package is a sibling sub-package, not a replacement; pass1 is
reused here only for its generic, stable scoring engine
(pass1.rules.combine_signals() and friends), never modified.

Only DocumentClassificationPipeline, the enums, and the two result
models are exported here. Deliberately no module-level convenience
function (unlike pass1's own classify_document()) — the task's Public
API is exactly DocumentClassificationPipeline.process(document), already
a one-liner. Non-goals: medical understanding, study quality analysis,
paper summarization, cross-document comparison, conclusion inference,
LLM integration — this package only classifies, using the same
deterministic rule-based approach as pass1 and Phase 1.1.
"""

from .enums import DocumentType, ReportingGuideline, ScientificDomain, StudyDesign
from .models import ClassificationDecision, ClassificationResult
from .pipeline import DocumentClassificationPipeline

__all__ = [
    "DocumentClassificationPipeline",
    "ClassificationDecision",
    "ClassificationResult",
    "DocumentType",
    "ScientificDomain",
    "StudyDesign",
    "ReportingGuideline",
]
