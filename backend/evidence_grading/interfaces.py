"""Base interfaces for the Evidence Grading Engine's two component kinds
— see registry.py's own module docstring for how GraderRegistry
schedules them via a real dependency-aware execution plan (prerequisite
assessors never depend on each other; framework graders depend on
whichever prerequisite assessments their own requires() names).
"""

from abc import ABC, abstractmethod

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.medical_understanding.models import MedicalUnderstanding

from .enums import GradingFramework
from .models import FrameworkResult, PrerequisiteAssessment, PrerequisiteAssessments


class BasePrerequisiteAssessor(ABC):
    """Base interface for prerequisite assessors. See assessments/*.py."""

    @abstractmethod
    def assess(
        self,
        document: ProcessedDocument,
        classification: ClassificationResult,
        medical: MedicalUnderstanding,
    ) -> PrerequisiteAssessment:
        raise NotImplementedError

    @abstractmethod
    def supports(self, context: AnalysisContext) -> bool:
        """Whether this assessor should run at all for this document."""
        raise NotImplementedError

    @abstractmethod
    def priority(self) -> int:
        """Higher priority runs first within its dependency tier."""
        raise NotImplementedError


class BaseFrameworkGrader(ABC):
    """Base interface for framework graders. See frameworks/*.py."""

    @abstractmethod
    def grade(
        self,
        prerequisites: PrerequisiteAssessments,
        document: ProcessedDocument,
        classification: ClassificationResult,
        medical: MedicalUnderstanding,
    ) -> FrameworkResult:
        raise NotImplementedError

    @abstractmethod
    def framework(self) -> GradingFramework:
        raise NotImplementedError

    @abstractmethod
    def requires(self) -> list[str]:
        """Names of the prerequisite assessments this grader consumes —
        registry.py's DependencyGraph uses these names to compute a
        real execution order (prerequisite assessors' tier, then this
        grader's tier)."""
        raise NotImplementedError

    @abstractmethod
    def supports(self, context: AnalysisContext) -> bool:
        raise NotImplementedError

    @abstractmethod
    def priority(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def version(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def compatible_frameworks(self) -> list[GradingFramework]:
        """Frameworks this one's grade can be meaningfully compared/
        aggregated against — see aggregators/conflict_resolver.py."""
        raise NotImplementedError
