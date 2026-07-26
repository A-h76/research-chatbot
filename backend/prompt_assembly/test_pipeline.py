"""Integration and unit tests for PromptAssemblyPipeline."""

import pytest

from backend.analysis_context.enums import PromptFamily, PromptStrategy, RoutingDecision
from backend.prompt_assembly.conftest import process_pdf
from backend.prompt_assembly.exceptions import ValidationError
from backend.prompt_assembly.pipeline import PIPELINE_VERSION, PromptAssemblyPipeline
from backend.prompt_assembly.security.sanitizers import ContentSanitizer, safe_fill_template
from backend.prompt_assembly.validators import require_valid_inputs


def test_assembles_clinical_trial_prompt(
    pdf_factory, classification_factory, context_factory, medical_factory, grades_factory
):
    document = process_pdf(
        pdf_factory(
            [
                "Metformin RCT\n\n"
                "Abstract\n"
                "A randomized controlled trial of metformin versus placebo.\n\n"
                "Methods\n"
                "Adults with type 2 diabetes were randomly assigned.\n\n"
                "Results\n"
                "HbA1c decreased significantly.\n"
            ]
        )
    )
    result = PromptAssemblyPipeline().process(
        document,
        classification_factory(),
        context_factory(primary_routing=RoutingDecision.CLINICAL_TRIAL),
        medical_factory(with_pico=True),
        grades_factory(skipped=False),
    )

    assert result.pipeline_version == PIPELINE_VERSION
    assert result.system_prompt
    assert result.user_prompt
    assert result.full_prompt.startswith(result.system_prompt)
    assert result.prompt_family == PromptFamily.CLINICAL
    assert result.prompt_strategy == PromptStrategy.PICO_FIRST
    assert result.components
    assert result.assembly_log.tokens_estimated >= 0
    assert 0.0 <= result.confidence_score.overall <= 1.0


def test_assembles_when_medical_and_grades_skipped(
    pdf_factory, classification_factory, context_factory, medical_factory, grades_factory
):
    document = process_pdf(pdf_factory(["A generic methods overview.\n"]))
    result = PromptAssemblyPipeline().process(
        document,
        classification_factory(),
        context_factory(
            primary_routing=RoutingDecision.GENERIC,
            prompt_family=PromptFamily.GENERIC,
            prompt_strategy=PromptStrategy.HYBRID,
        ),
        medical_factory(skipped=True),
        grades_factory(skipped=True),
    )

    assert result.system_prompt
    assert result.user_prompt
    assert result.errors == [] or all(e.severity.value != "critical" for e in result.errors)


def test_safe_fill_ignores_unknown_placeholders():
    filled = safe_fill_template(
        "Hello {title} leftover {evil}",
        {"title": "Paper", "evil": "x"},
        allowed_keys={"title"},
    )
    assert filled == "Hello Paper leftover "


def test_sanitizer_neutralizes_braces():
    cleaned = ContentSanitizer().sanitize("claim {secret}")
    assert "{" not in cleaned
    assert "}" not in cleaned


def test_require_valid_inputs_rejects_wrong_types(
    pdf_factory, classification_factory, context_factory, medical_factory, grades_factory
):
    document = process_pdf(pdf_factory(["x\n"]))
    with pytest.raises(ValidationError):
        require_valid_inputs(
            document,
            classification_factory(),
            context_factory(),
            medical_factory(),
            "bad",  # type: ignore[arg-type]
        )


def test_determinism_same_inputs(
    pdf_factory, classification_factory, context_factory, medical_factory, grades_factory
):
    document = process_pdf(pdf_factory(["RCT methods and results.\n"]))
    args = (
        document,
        classification_factory(),
        context_factory(),
        medical_factory(),
        grades_factory(),
    )
    pipeline = PromptAssemblyPipeline()
    first = pipeline.process(*args)
    second = pipeline.process(*args)
    assert first.prompt_family == second.prompt_family
    assert first.prompt_strategy == second.prompt_strategy
    assert first.system_prompt == second.system_prompt
    assert first.user_prompt == second.user_prompt
