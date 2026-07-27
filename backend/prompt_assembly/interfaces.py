"""Builder / selector interfaces for the Prompt Assembly Engine."""

from abc import ABC, abstractmethod

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.models import MedicalUnderstanding

from .enums import PromptComponentType, PromptStrategy
from .models import PromptComponent


class BasePromptBuilder(ABC):
    """Base interface for prompt builders."""

    @abstractmethod
    def build(
        self,
        document: ProcessedDocument,
        classification: ClassificationResult,
        context: AnalysisContext,
        medical: MedicalUnderstanding,
        grades: EvidenceGrades,
    ) -> PromptComponent:
        raise NotImplementedError

    @abstractmethod
    def supports(self, context: AnalysisContext) -> bool:
        raise NotImplementedError

    @abstractmethod
    def priority(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def component_type(self) -> PromptComponentType:
        raise NotImplementedError


class BaseTemplateSelector(ABC):
    """Base interface for template selection — returns a template name
    key (e.g. 'medical', 'clinical'), not raw template text."""

    @abstractmethod
    def select(self, context: AnalysisContext, classification: ClassificationResult) -> str:
        raise NotImplementedError

    @abstractmethod
    def supports(self, context: AnalysisContext) -> bool:
        raise NotImplementedError


class BaseStrategySelector(ABC):
    """Base interface for strategy selection."""

    @abstractmethod
    def select(
        self,
        context: AnalysisContext,
        classification: ClassificationResult,
        grades: EvidenceGrades,
        medical: MedicalUnderstanding | None = None,
    ) -> PromptStrategy:
        raise NotImplementedError

    @abstractmethod
    def supports(self, context: AnalysisContext) -> bool:
        raise NotImplementedError
