"""Grader registry with dependency management.

get_assessment_plan() builds a real DependencyGraph from every enabled
prerequisite assessor (which never depend on anything else — see
package docstring's dependency diagram: "Prerequisite Assessment Phase
(parallel where independent)") and every enabled framework grader
(which depends on whichever prerequisite-assessor names its own
requires() lists) and computes execution tiers via a real topological
sort (Kahn's algorithm) — not a hardcoded two-tier shortcut, so a future
grader depending on only a subset of prerequisites, or a future
assessor depending on another assessor, is scheduled correctly with no
change here.

A cycle in the requires() graph (a configuration bug, not a document-
quality problem) raises DependencyCycleError at plan-construction time
rather than silently dropping nodes or hanging — see exceptions.py.

Naming convention this registry relies on: a prerequisite assessor's
registered name must match the PrerequisiteAssessments field it
populates exactly ("risk_of_bias", "consistency", "precision",
"directness", "publication_bias", "reporting_quality", "applicability")
— see _build_prerequisites(), the one place that convention is used.

Every assessor/grader call in _safe_call() is additionally routed
through security/isolation.py's PluginIsolator (allowlist check +
best-effort timeout) — this is the one real call site those protections
guard; PluginIsolator itself has no effect sitting unused.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Optional

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.medical_understanding.models import MedicalUnderstanding

from .config import EvidenceGradingConfig
from .enums import ErrorSeverity, ErrorType
from .exceptions import DependencyCycleError, EvidenceGradingError, SecurityError
from .interfaces import BaseFrameworkGrader, BasePrerequisiteAssessor
from .models import ExtractionError, FrameworkResult, PrerequisiteAssessments
from .security.isolation import PluginIsolator

_PREREQUISITE_FIELD_NAMES = (
    "risk_of_bias",
    "consistency",
    "precision",
    "directness",
    "publication_bias",
    "reporting_quality",
    "applicability",
)

# Maps registered assessor names to EvidenceGradingConfig enable_* flags.
# Assessors without a flag (applicability) stay enabled whenever supports() agrees.
_ASSESSOR_ENABLE_FLAGS = {
    "risk_of_bias": "enable_risk_of_bias",
    "consistency": "enable_consistency",
    "precision": "enable_precision",
    "directness": "enable_directness",
    "publication_bias": "enable_publication_bias",
    "reporting_quality": "enable_reporting_quality",
}


@dataclass
class DependencyGraph:
    """Plain node/edge storage — node name -> set of names it depends
    on. Prerequisite-assessor nodes always have an empty dependency
    set."""

    edges: dict[str, set[str]] = field(default_factory=dict)

    def add_node(self, name: str, depends_on: Optional[list[str]] = None) -> None:
        self.edges.setdefault(name, set())
        for dependency in depends_on or []:
            self.edges[name].add(dependency)
            self.edges.setdefault(dependency, set())

    def tiers(self) -> list[list[str]]:
        """Kahn's algorithm, grouped into tiers: each tier is every node
        whose remaining dependencies have all already been placed in an
        earlier tier. Raises DependencyCycleError if nodes remain with
        no zero-remaining-dependency node left to place — a real cycle,
        not just an artifact of iteration order."""
        remaining = {name: set(deps) for name, deps in self.edges.items()}
        placed: set[str] = set()
        result: list[list[str]] = []

        while remaining:
            ready = sorted(name for name, deps in remaining.items() if deps <= placed)
            if not ready:
                raise DependencyCycleError(f"cycle detected among: {sorted(remaining)}")
            result.append(ready)
            for name in ready:
                remaining.pop(name)
            placed.update(ready)

        return result


@dataclass
class AssessmentPlan:
    """The ordered execution plan get_assessment_plan() produces — tiers
    of prerequisite-assessor names, then tiers of framework-grader
    names (see module docstring)."""

    assessor_tiers: list[list[str]] = field(default_factory=list)
    grader_tiers: list[list[str]] = field(default_factory=list)
    enabled_assessors: dict[str, BasePrerequisiteAssessor] = field(default_factory=dict)
    enabled_graders: dict[str, BaseFrameworkGrader] = field(default_factory=dict)


class GraderRegistry:
    """Registry with dependency management."""

    def __init__(self, config: Optional[EvidenceGradingConfig] = None) -> None:
        self._prerequisite_assessors: dict[str, BasePrerequisiteAssessor] = {}
        self._framework_graders: dict[str, BaseFrameworkGrader] = {}
        self._config = config or EvidenceGradingConfig()
        self._isolator = PluginIsolator(self._config)

    def register_prerequisite_assessor(self, name: str, assessor: BasePrerequisiteAssessor) -> None:
        self._prerequisite_assessors[name] = assessor

    def register_framework_grader(self, name: str, grader: BaseFrameworkGrader) -> None:
        self._framework_graders[name] = grader

    def _assessor_enabled(self, name: str) -> bool:
        flag = _ASSESSOR_ENABLE_FLAGS.get(name)
        if flag is None:
            return True
        return bool(getattr(self._config, flag, True))

    def get_assessment_plan(self, context: AnalysisContext) -> AssessmentPlan:
        """Every registered assessor whose own supports(context) agrees,
        and every registered grader whose framework() is both enabled in
        config and whose own supports(context) agrees — assembled into a
        real dependency graph and split into tiers."""
        enabled_assessors = {
            name: assessor
            for name, assessor in self._prerequisite_assessors.items()
            if self._assessor_enabled(name) and assessor.supports(context)
        }
        enabled_graders = {
            name: grader
            for name, grader in self._framework_graders.items()
            if grader.framework() in self._config.enabled_frameworks and grader.supports(context)
        }

        graph = DependencyGraph()
        for name in enabled_assessors:
            graph.add_node(name)
        for name, grader in enabled_graders.items():
            # A grader requiring an assessment that isn't enabled/
            # registered simply gets that PrerequisiteAssessments field
            # at its own neutral default (see _build_prerequisites) —
            # not a hard scheduling failure.
            graph.add_node(name, depends_on=[req for req in grader.requires() if req in enabled_assessors])

        tiers = graph.tiers()
        assessor_names = set(enabled_assessors)
        assessor_tiers = [sorted(n for n in tier if n in assessor_names) for tier in tiers]
        grader_tiers = [sorted(n for n in tier if n not in assessor_names) for tier in tiers]

        return AssessmentPlan(
            assessor_tiers=[tier for tier in assessor_tiers if tier],
            grader_tiers=[tier for tier in grader_tiers if tier],
            enabled_assessors=enabled_assessors,
            enabled_graders=enabled_graders,
        )

    def execute_dag(
        self,
        plan: AssessmentPlan,
        document: ProcessedDocument,
        classification: ClassificationResult,
        medical: MedicalUnderstanding,
    ) -> tuple[PrerequisiteAssessments, dict[str, FrameworkResult], list[ExtractionError]]:
        """Executes the dependency graph with parallelization where safe
        — assessor tiers first (each tier's assessors run in parallel
        with each other), building one shared PrerequisiteAssessments,
        then grader tiers (every framework grader consumes the SAME
        PrerequisiteAssessments — never recomputed per-grader)."""
        errors: list[ExtractionError] = []
        assessment_results: dict[str, object] = {}

        for tier in plan.assessor_tiers:
            thunks = {
                name: self._assessor_thunk(plan.enabled_assessors[name], document, classification, medical)
                for name in tier
            }
            assessment_results.update(self._run_tier(tier, thunks, errors))

        prerequisites = self._build_prerequisites(assessment_results)

        framework_results: dict[str, FrameworkResult] = {}
        for tier in plan.grader_tiers:
            thunks = {
                name: self._grader_thunk(plan.enabled_graders[name], prerequisites, document, classification, medical)
                for name in tier
            }
            framework_results.update(self._run_tier(tier, thunks, errors))

        return prerequisites, framework_results, errors

    @staticmethod
    def _assessor_thunk(assessor: BasePrerequisiteAssessor, document, classification, medical) -> Callable[[], object]:
        return lambda: assessor.assess(document, classification, medical)

    @staticmethod
    def _grader_thunk(grader: BaseFrameworkGrader, prerequisites, document, classification, medical) -> Callable[[], object]:
        return lambda: grader.grade(prerequisites, document, classification, medical)

    def _run_tier(
        self, names: list[str], thunks: dict[str, Callable[[], object]], errors: list[ExtractionError]
    ) -> dict[str, object]:
        if not self._config.enable_parallel or len(names) <= 1:
            return {name: self._safe_call(name, thunks[name], errors) for name in names}

        results: dict[str, object] = {}
        with ThreadPoolExecutor(max_workers=self._config.max_parallel_workers) as executor:
            futures = {executor.submit(self._safe_call, name, thunks[name], errors): name for name in names}
            for future, name in futures.items():
                results[name] = future.result()
        return results

    def _safe_call(self, name: str, thunk: Callable[[], object], errors: list[ExtractionError]) -> Optional[object]:
        try:
            return self._isolator.execute_plugin(name, thunk)
        except SecurityError as exc:
            errors.append(
                ExtractionError(component=name, error_type=ErrorType.SECURITY_ERROR, message=str(exc), severity=ErrorSeverity.CRITICAL)
            )
            return None
        except EvidenceGradingError as exc:
            errors.append(
                ExtractionError(component=name, error_type=exc.error_type, message=str(exc), severity=exc.severity)
            )
            return None
        except Exception as exc:  # noqa: BLE001 -- one component's crash must never take down the others
            errors.append(
                ExtractionError(component=name, error_type=ErrorType.ASSESSMENT_ERROR, message=str(exc), severity=ErrorSeverity.ERROR)
            )
            return None

    @staticmethod
    def _build_prerequisites(assessment_results: dict[str, object]) -> PrerequisiteAssessments:
        kwargs = {
            name: assessment_results[name] for name in _PREREQUISITE_FIELD_NAMES if assessment_results.get(name) is not None
        }
        return PrerequisiteAssessments(**kwargs)
