"""Builds task-instruction and output-format PromptComponents."""

from typing import Optional

from backend.analysis_context.enums import PromptFamily, RoutingDecision
from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.models import MedicalUnderstanding

from ..config import PromptAssemblyConfig
from ..enums import PromptComponentType, PromptPriority
from ..interfaces import BasePromptBuilder
from ..models import PromptComponent
from ..selectors.family_selector import FamilySelector

_TASK_BY_FAMILY = {
    PromptFamily.MEDICAL: (
        "Analyze the clinical findings, methodological quality, and evidence strength. "
        "Identify clinical implications and research gaps."
    ),
    PromptFamily.CLINICAL: (
        "Evaluate this clinical trial's design, population, interventions, outcomes, "
        "and risk of bias. Summarize efficacy and safety findings."
    ),
    PromptFamily.SYSTEMATIC: (
        "Summarize the review question, included evidence, synthesis results, "
        "and GRADE assessments. Note limitations and implications for practice."
    ),
    PromptFamily.METHODOLOGICAL: (
        "Assess the methodological approach, validity of claims, and reproducibility. "
        "Highlight strengths and weaknesses."
    ),
    PromptFamily.COMPUTER_SCIENCE: (
        "Summarize the problem, method, experiments, baselines, and results. "
        "Note limitations and contributions."
    ),
    PromptFamily.GENERIC: (
        "Provide a structured analysis of the document covering key claims, "
        "supporting evidence, and limitations."
    ),
}

_OUTPUT_STRUCTURED = (
    "Provide a structured analysis with these sections:\n"
    "1. Summary of Findings\n"
    "2. Quality Assessment\n"
    "3. Clinical/Domain Implications\n"
    "4. Research Gaps\n"
    "5. Recommendations"
)

_OUTPUT_FREEFORM = "Respond in clear prose covering findings, quality, implications, and recommendations."


class InstructionsBuilder(BasePromptBuilder):
    """Produces TASK_DESCRIPTION, INSTRUCTION, and OUTPUT_FORMAT via
    three registered instances (task / instructions / output)."""

    def __init__(
        self,
        config: Optional[PromptAssemblyConfig] = None,
        mode: str = "instructions",
    ) -> None:
        self._config = config or PromptAssemblyConfig()
        self._mode = mode  # "task" | "instructions" | "output"
        self._family_selector = FamilySelector(self._config)

    def build(
        self,
        document: ProcessedDocument,
        classification: ClassificationResult,
        context: AnalysisContext,
        medical: MedicalUnderstanding,
        grades: EvidenceGrades,
    ) -> PromptComponent:
        family = self._family_selector.select(context, classification)

        if self._mode == "task":
            content = _TASK_BY_FAMILY.get(family, _TASK_BY_FAMILY[PromptFamily.GENERIC])
            return PromptComponent(
                component_type=PromptComponentType.TASK_DESCRIPTION,
                content=content,
                priority=1,
                confidence=1.0,
                evidence=[],
                source="InstructionsBuilder.task",
                priority_level=PromptPriority.CRITICAL,
            )

        if self._mode == "output":
            content = _OUTPUT_STRUCTURED if self._config.output_format != "freeform" else _OUTPUT_FREEFORM
            return PromptComponent(
                component_type=PromptComponentType.OUTPUT_FORMAT,
                content=content,
                priority=8,
                confidence=1.0,
                evidence=[],
                source="InstructionsBuilder.output",
                priority_level=PromptPriority.CRITICAL,
            )

        # instructions
        steps = [
            "1. Use only information present in the provided context — do not invent citations or results.",
            "2. Prefer higher-confidence extracted entities and graded evidence when available.",
            "3. Explicitly note when medical understanding or evidence grading was skipped.",
            "4. Separate findings, quality appraisal, and recommendations.",
        ]
        if context.routing_profile.primary_routing == RoutingDecision.CLINICAL_TRIAL:
            steps.append("5. Emphasize randomization, blinding, and intention-to-treat signals when present.")
        content = "\n".join(steps)
        return PromptComponent(
            component_type=PromptComponentType.INSTRUCTION,
            content=content,
            priority=7,
            confidence=1.0,
            evidence=[],
            source="InstructionsBuilder.instructions",
            priority_level=PromptPriority.CRITICAL,
        )

    def supports(self, context: AnalysisContext) -> bool:
        return True

    def priority(self) -> int:
        if self._mode == "task":
            return 95
        if self._mode == "output":
            return 40
        return 50

    def component_type(self) -> PromptComponentType:
        if self._mode == "task":
            return PromptComponentType.TASK_DESCRIPTION
        if self._mode == "output":
            return PromptComponentType.OUTPUT_FORMAT
        return PromptComponentType.INSTRUCTION
