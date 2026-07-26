"""Unit tests for builders and confidence filter."""

from backend.analysis_context.enums import RoutingDecision
from backend.prompt_assembly.assemblers.confidence_filter import filter_by_confidence
from backend.prompt_assembly.builders.grading_builder import GradingBuilder
from backend.prompt_assembly.builders.pico_builder import PICOBuilder
from backend.prompt_assembly.config import PromptAssemblyConfig
from backend.prompt_assembly.conftest import process_pdf
from backend.prompt_assembly.enums import PromptComponentType, PromptPriority
from backend.prompt_assembly.models import PromptComponent
from backend.prompt_assembly.security.limits import estimate_tokens
from backend.prompt_assembly.enums import TokenEstimationStrategy


def test_pico_builder_incomplete(pdf_factory, classification_factory, context_factory, medical_factory, grades_factory):
    document = process_pdf(pdf_factory(["x\n"]))
    component = PICOBuilder().build(
        document,
        classification_factory(),
        context_factory(),
        medical_factory(with_pico=False),
        grades_factory(skipped=True),
    )
    assert component.component_type == PromptComponentType.PICO
    assert component.confidence == 0.0


def test_grading_builder_skipped(pdf_factory, classification_factory, context_factory, medical_factory, grades_factory):
    document = process_pdf(pdf_factory(["x\n"]))
    component = GradingBuilder().build(
        document,
        classification_factory(),
        context_factory(primary_routing=RoutingDecision.GENERIC),
        medical_factory(skipped=True),
        grades_factory(skipped=True),
    )
    assert "not available" in component.content.lower() or "not" in component.content.lower()


def test_confidence_filter_keeps_critical_even_if_low_confidence():
    config = PromptAssemblyConfig(confidence_threshold=0.9)
    components = [
        PromptComponent(
            component_type=PromptComponentType.DOCUMENT_CONTEXT,
            content="ctx",
            priority=1,
            confidence=0.0,
            priority_level=PromptPriority.CRITICAL,
        ),
        PromptComponent(
            component_type=PromptComponentType.STATISTICS,
            content="stats",
            priority=6,
            confidence=0.1,
            priority_level=PromptPriority.LOW,
        ),
    ]
    kept, result = filter_by_confidence(components, config)
    assert any(c.component_type == PromptComponentType.DOCUMENT_CONTEXT for c in kept)
    assert PromptComponentType.STATISTICS.value in result.excluded_items


def test_estimate_tokens_word_count():
    tokens = estimate_tokens("one two three four", TokenEstimationStrategy.WORD_COUNT)
    assert tokens >= 4
