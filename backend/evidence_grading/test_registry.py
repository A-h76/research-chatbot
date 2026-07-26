import pytest

from backend.evidence_grading.config import EvidenceGradingConfig
from backend.evidence_grading.enums import GradingFramework
from backend.evidence_grading.exceptions import DependencyCycleError
from backend.evidence_grading.interfaces import BaseFrameworkGrader, BasePrerequisiteAssessor
from backend.evidence_grading.models import FrameworkResult, Grade, RiskOfBiasAssessment
from backend.evidence_grading.registry import DependencyGraph, GraderRegistry


class _StubAssessor(BasePrerequisiteAssessor):
    def __init__(self, confidence: float = 0.9):
        self._confidence = confidence

    def assess(self, document, classification, medical):
        return RiskOfBiasAssessment(confidence=self._confidence)

    def supports(self, context) -> bool:
        return True

    def priority(self) -> int:
        return 50


class _StubGrader(BaseFrameworkGrader):
    def __init__(self, framework: GradingFramework, requires: list = None):
        self._framework = framework
        self._requires = requires or ["risk_of_bias"]

    def grade(self, prerequisites, document, classification, medical) -> FrameworkResult:
        return FrameworkResult(
            framework=self._framework,
            grade=Grade(framework=self._framework, grade_value="x", confidence=prerequisites.risk_of_bias.confidence),
        )

    def framework(self) -> GradingFramework:
        return self._framework

    def requires(self) -> list:
        return self._requires

    def supports(self, context) -> bool:
        return True

    def priority(self) -> int:
        return 50

    def version(self) -> str:
        return "1.0.0"

    def compatible_frameworks(self) -> list:
        return []


def test_dependency_graph_tiers_orders_by_dependency():
    graph = DependencyGraph()
    graph.add_node("risk_of_bias")
    graph.add_node("grade", depends_on=["risk_of_bias"])
    tiers = graph.tiers()
    assert tiers == [["grade", "risk_of_bias"]] or tiers == [["risk_of_bias"], ["grade"]]
    # risk_of_bias (no deps) must appear strictly before grade
    flat_positions = {name: i for i, tier in enumerate(tiers) for name in tier}
    assert flat_positions["risk_of_bias"] < flat_positions["grade"]


def test_dependency_graph_raises_on_cycle():
    graph = DependencyGraph()
    graph.add_node("a", depends_on=["b"])
    graph.add_node("b", depends_on=["a"])
    with pytest.raises(DependencyCycleError):
        graph.tiers()


def test_get_assessment_plan_builds_correct_tiers(context_factory):
    config = EvidenceGradingConfig(enabled_frameworks=[GradingFramework.GRADE, GradingFramework.OXFORD])
    registry = GraderRegistry(config)
    registry.register_prerequisite_assessor("risk_of_bias", _StubAssessor())
    registry.register_framework_grader("grade", _StubGrader(GradingFramework.GRADE))
    registry.register_framework_grader("oxford", _StubGrader(GradingFramework.OXFORD))

    plan = registry.get_assessment_plan(context_factory())
    assert plan.assessor_tiers == [["risk_of_bias"]]
    assert plan.grader_tiers == [["grade", "oxford"]]


def test_execute_dag_shares_prerequisites_across_graders(context_factory):
    config = EvidenceGradingConfig(enabled_frameworks=[GradingFramework.GRADE, GradingFramework.OXFORD])
    registry = GraderRegistry(config)
    registry.register_prerequisite_assessor("risk_of_bias", _StubAssessor(confidence=0.42))
    registry.register_framework_grader("grade", _StubGrader(GradingFramework.GRADE))
    registry.register_framework_grader("oxford", _StubGrader(GradingFramework.OXFORD))

    plan = registry.get_assessment_plan(context_factory())
    prerequisites, results, errors = registry.execute_dag(plan, None, None, None)

    assert prerequisites.risk_of_bias.confidence == 0.42
    assert results["grade"].grade.confidence == 0.42
    assert results["oxford"].grade.confidence == 0.42
    assert errors == []


def test_execute_dag_isolates_a_crashing_component(context_factory):
    class _CrashingAssessor(_StubAssessor):
        def assess(self, document, classification, medical):
            raise RuntimeError("boom")

    config = EvidenceGradingConfig(enabled_frameworks=[GradingFramework.GRADE])
    registry = GraderRegistry(config)
    registry.register_prerequisite_assessor("risk_of_bias", _CrashingAssessor())
    registry.register_framework_grader("grade", _StubGrader(GradingFramework.GRADE))

    plan = registry.get_assessment_plan(context_factory())
    prerequisites, results, errors = registry.execute_dag(plan, None, None, None)

    assert len(errors) == 1
    assert errors[0].component == "risk_of_bias"
    # grade still ran, consuming the neutral default risk_of_bias
    assert results["grade"].grade.confidence == 0.0
    assert prerequisites.risk_of_bias.confidence == 0.0


def test_execute_dag_enforces_plugin_allowlist(context_factory):
    config = EvidenceGradingConfig(enabled_frameworks=[GradingFramework.GRADE], plugin_allowlist=["grade"])
    registry = GraderRegistry(config)
    registry.register_prerequisite_assessor("risk_of_bias", _StubAssessor())
    registry.register_framework_grader("grade", _StubGrader(GradingFramework.GRADE))

    plan = registry.get_assessment_plan(context_factory())
    _, _, errors = registry.execute_dag(plan, None, None, None)

    assert any(e.component == "risk_of_bias" and e.error_type.value == "security_error" for e in errors)


def test_get_assessment_plan_respects_enable_flags(context_factory):
    config = EvidenceGradingConfig(
        enabled_frameworks=[GradingFramework.GRADE],
        enable_risk_of_bias=False,
        enable_consistency=True,
    )
    registry = GraderRegistry(config)
    registry.register_prerequisite_assessor("risk_of_bias", _StubAssessor())
    registry.register_prerequisite_assessor("consistency", _StubAssessor())
    registry.register_framework_grader("grade", _StubGrader(GradingFramework.GRADE, requires=["consistency"]))

    plan = registry.get_assessment_plan(context_factory())
    assert "risk_of_bias" not in plan.enabled_assessors
    assert "consistency" in plan.enabled_assessors
