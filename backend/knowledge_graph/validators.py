"""Input and output validation."""

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.models import MedicalUnderstanding
from backend.prompt_assembly.models import AssembledPrompt

from .config import KnowledgeGraphConfig
from .exceptions import ValidationError
from .models import KnowledgeGraph


def require_valid_inputs(
    document: ProcessedDocument,
    classification: ClassificationResult,
    context: AnalysisContext,
    medical: MedicalUnderstanding,
    grades: EvidenceGrades,
    prompt: AssembledPrompt,
) -> None:
    if not isinstance(document, ProcessedDocument):
        raise ValidationError(f"document must be ProcessedDocument, got {type(document).__name__}")
    if not isinstance(classification, ClassificationResult):
        raise ValidationError(f"classification must be ClassificationResult, got {type(classification).__name__}")
    if not isinstance(context, AnalysisContext):
        raise ValidationError(f"context must be AnalysisContext, got {type(context).__name__}")
    if not isinstance(medical, MedicalUnderstanding):
        raise ValidationError(f"medical must be MedicalUnderstanding, got {type(medical).__name__}")
    if not isinstance(grades, EvidenceGrades):
        raise ValidationError(f"grades must be EvidenceGrades, got {type(grades).__name__}")
    if not isinstance(prompt, AssembledPrompt):
        raise ValidationError(f"prompt must be AssembledPrompt, got {type(prompt).__name__}")


def validate_inputs(medical: MedicalUnderstanding, grades: EvidenceGrades) -> list[str]:
    warnings: list[str] = []
    if medical.skipped:
        warnings.append(f"medical understanding skipped: {medical.reasoning or 'no reason'}")
    if grades.skipped:
        warnings.append(f"evidence grades skipped: {grades.reasoning or 'no reason'}")
    return warnings


def validate_output(graph: KnowledgeGraph, config: KnowledgeGraphConfig) -> list[str]:
    warnings: list[str] = []
    if len(graph.nodes) > config.max_nodes:
        warnings.append(f"node count {len(graph.nodes)} exceeds max_nodes {config.max_nodes}")
    if len(graph.edges) > config.max_edges:
        warnings.append(f"edge count {len(graph.edges)} exceeds max_edges {config.max_edges}")
    node_ids = {n.node_id for n in graph.nodes}
    dangling = [
        e.edge_id
        for e in graph.edges
        if e.source_node_id not in node_ids or e.target_node_id not in node_ids
    ]
    if dangling:
        warnings.append(f"{len(dangling)} edges reference missing nodes")
    if not (0.0 <= graph.confidence.overall_confidence <= 1.0):
        warnings.append(f"overall_confidence out of range: {graph.confidence.overall_confidence}")
    return warnings
