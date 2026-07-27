"""Builder / calculator interfaces for the Knowledge Graph Engine."""

from abc import ABC, abstractmethod
from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.document_understanding.models import EvidenceReference
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.models import MedicalUnderstanding

from .models import GraphEdge, GraphNode


class BaseNodeBuilder(ABC):
    @abstractmethod
    def build_nodes(self, medical: MedicalUnderstanding, grades: EvidenceGrades) -> list[GraphNode]:
        raise NotImplementedError

    @abstractmethod
    def supports(self, context: AnalysisContext) -> bool:
        raise NotImplementedError

    @abstractmethod
    def priority(self) -> int:
        raise NotImplementedError

    def version(self) -> str:
        return "1.0.0"


class BaseEdgeBuilder(ABC):
    @abstractmethod
    def build_edges(
        self,
        nodes: list[GraphNode],
        medical: MedicalUnderstanding,
        grades: EvidenceGrades,
    ) -> list[GraphEdge]:
        raise NotImplementedError

    @abstractmethod
    def supports(self, context: AnalysisContext) -> bool:
        raise NotImplementedError

    @abstractmethod
    def priority(self) -> int:
        raise NotImplementedError

    def version(self) -> str:
        return "1.0.0"


class BaseWeightCalculator(ABC):
    @abstractmethod
    def calculate_confidence(
        self,
        node: Optional[GraphNode],
        edge: Optional[GraphEdge],
        evidence: list[EvidenceReference],
        node_lookup: Optional[dict[str, GraphNode]] = None,
    ) -> float:
        raise NotImplementedError

    @abstractmethod
    def supports(self, context: AnalysisContext) -> bool:
        raise NotImplementedError


class BaseGraphBuilder(ABC):
    """Optional composite builder returning nodes+edges together."""

    @abstractmethod
    def build(
        self,
        document,
        classification,
        context: AnalysisContext,
        medical: MedicalUnderstanding,
        grades: EvidenceGrades,
        prompt,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        raise NotImplementedError

    @abstractmethod
    def supports(self, context: AnalysisContext) -> bool:
        raise NotImplementedError

    @abstractmethod
    def priority(self) -> int:
        raise NotImplementedError

    def version(self) -> str:
        return "1.0.0"
