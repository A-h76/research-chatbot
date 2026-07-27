"""PromptAssemblyPipeline — Phase 1.6 public entry point.

    (ProcessedDocument, ClassificationResult, AnalysisContext,
     MedicalUnderstanding, EvidenceGrades)
        |
        v
    Validate inputs
        |
        v
    FamilySelector / StrategySelector / SectionPrioritizer
        |
        v
    Run builders (priority order; failures isolated)
        |
        v
    PromptAssembler (confidence filter → safe template fill → token clamp)
        |
        v
    AssembledPrompt
"""

import time
from typing import Callable, Optional, TypeVar

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult
from backend.document_understanding.models import ProcessedDocument
from backend.evidence_grading.models import EvidenceGrades
from backend.medical_understanding.models import MedicalUnderstanding

from .assemblers.prompt_assembler import PromptAssembler
from .assemblers.section_assembler import SectionAssembler
from .builders.context_builder import ContextBuilder
from .builders.entities_builder import EntitiesBuilder
from .builders.evidence_builder import EvidenceBuilder
from .builders.grading_builder import GradingBuilder
from .builders.instructions_builder import InstructionsBuilder
from .builders.pico_builder import PICOBuilder
from .builders.statistics_builder import StatisticsBuilder
from .config import PromptAssemblyConfig
from .enums import ErrorSeverity, ErrorType
from .models import AssembledPrompt, ExtractionError, PromptComponent
from .registry import PromptBuilderRegistry
from .selectors.family_selector import FamilySelector, TemplateNameSelector
from .selectors.section_prioritizer import SectionPrioritizer
from .selectors.strategy_selector import StrategySelector
from .validators import require_valid_inputs, validate_inputs, validate_output
PIPELINE_VERSION = "1.0.0"

_Result = TypeVar("_Result")


class PromptAssemblyPipeline:
    """See module docstring."""

    def __init__(self, config: Optional[PromptAssemblyConfig] = None) -> None:
        self.config = config or PromptAssemblyConfig()
        self.registry = PromptBuilderRegistry(self.config)
        self._family_selector = FamilySelector(self.config)
        self._strategy_selector = StrategySelector(self.config)
        self._section_prioritizer = SectionPrioritizer()
        self._assembler = PromptAssembler(self.config)
        self._section_assembler = SectionAssembler(self.config)
        self._context_builder = ContextBuilder(self.config)
        self._register_default_builders()

    def _register_default_builders(self) -> None:
        self.registry.register_builder(self._context_builder)
        self.registry.register_builder(EvidenceBuilder(self.config))
        self.registry.register_builder(PICOBuilder(self.config))
        self.registry.register_builder(EntitiesBuilder(self.config))
        self.registry.register_builder(StatisticsBuilder(self.config))
        self.registry.register_builder(GradingBuilder(self.config))
        self.registry.register_builder(InstructionsBuilder(self.config, mode="task"))
        self.registry.register_builder(InstructionsBuilder(self.config, mode="instructions"))
        self.registry.register_builder(InstructionsBuilder(self.config, mode="output"))
        self.registry.register_template_selector(TemplateNameSelector(self.config))
        self.registry.register_strategy_selector(self._strategy_selector)

    def process(
        self,
        document: ProcessedDocument,
        classification: ClassificationResult,
        context: AnalysisContext,
        medical: MedicalUnderstanding,
        grades: EvidenceGrades,
    ) -> AssembledPrompt:
        require_valid_inputs(document, classification, context, medical, grades)
        start = time.perf_counter()
        warnings = validate_inputs(document, medical, grades)
        errors: list[ExtractionError] = []

        family = self._family_selector.select(context, classification)
        strategy = self.registry.get_strategy(context, classification, grades, medical)
        template_name = self.registry.get_template(context, classification)
        section_priorities = self._section_prioritizer.prioritize(context, classification, strategy)

        components: list[PromptComponent] = []
        for builder in self.registry.get_enabled_builders(context):
            component = self._run_builder(
                builder.component_type().value,
                lambda b=builder: b.build(document, classification, context, medical, grades),
                errors,
            )
            if component is not None:
                components.append(component)

        document_context = self._context_builder.build_document_context(document, context)
        document_context.key_sections = self._section_assembler.assemble(document, section_priorities)

        extra = self._extra_variables(classification, medical, grades)
        assembled = self._assembler.assemble(
            components=components,
            template_name=template_name,
            strategy=strategy,
            family=family,
            document_context=document_context,
            extra_variables=extra,
        )

        assembled.assembly_log.add_decision(
            "family_selected",
            f"prompt family={family.value}",
            confidence=context.prompt_profile.confidence or 1.0,
        )
        assembled.assembly_log.add_decision(
            "strategy_selected",
            f"prompt strategy={strategy.value}",
            confidence=1.0,
        )

        assembled.warnings = warnings + assembled.warnings
        assembled.errors = errors
        assembled.processing_time_ms = (time.perf_counter() - start) * 1000
        assembled.pipeline_version = PIPELINE_VERSION

        if assembled.processing_time_ms > self.config.max_processing_time_ms:
            assembled.warnings.append(
                f"processing exceeded max_processing_time_ms "
                f"({assembled.processing_time_ms:.0f}ms > {self.config.max_processing_time_ms}ms)"
            )

        assembled.warnings.extend(validate_output(assembled, self.config))
        return assembled

    @staticmethod
    def _extra_variables(
        classification: ClassificationResult,
        medical: MedicalUnderstanding,
        grades: EvidenceGrades,
    ) -> dict[str, str]:
        pico = medical.pico_elements
        population = pico.population.description if pico and pico.population else ""
        intervention = ", ".join(i.name for i in pico.interventions) if pico else ""
        comparator = ", ".join(c.name for c in pico.comparators) if pico else ""
        outcomes = ", ".join(o.name for o in pico.outcomes) if pico else ""
        return {
            "study_design": classification.study_design.label.value,
            "population": population,
            "intervention": intervention,
            "comparator": comparator,
            "outcomes": outcomes,
            "risk_of_bias": grades.risk_of_bias.overall_risk.value if not grades.skipped else "",
            "method": "",
            "contributions": "",
            "review_question": "",
        }

    @staticmethod
    def _run_builder(
        name: str,
        fn: Callable[[], PromptComponent],
        errors: list[ExtractionError],
    ) -> Optional[PromptComponent]:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 — isolate one builder failure
            errors.append(
                ExtractionError(
                    component=name,
                    error_type=ErrorType.BUILDER_ERROR,
                    message=str(exc),
                    severity=ErrorSeverity.ERROR,
                )
            )
            return None
