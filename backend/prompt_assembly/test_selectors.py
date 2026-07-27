"""Unit tests for selectors."""

from backend.analysis_context.enums import PromptFamily, PromptStrategy, RoutingDecision
from backend.classification.pass2.enums import DocumentType, ScientificDomain, StudyDesign
from backend.prompt_assembly.selectors.family_selector import FamilySelector
from backend.prompt_assembly.selectors.section_prioritizer import SectionPrioritizer
from backend.prompt_assembly.selectors.strategy_selector import StrategySelector, pico_is_complete
from backend.document_understanding.enums import SectionType


def test_family_selector_clinical_trial(context_factory, classification_factory):
    family = FamilySelector().select(
        context_factory(primary_routing=RoutingDecision.CLINICAL_TRIAL),
        classification_factory(),
    )
    assert family == PromptFamily.CLINICAL


def test_family_selector_ai_domain(context_factory, classification_factory):
    family = FamilySelector().select(
        context_factory(primary_routing=RoutingDecision.GENERIC, prompt_family=PromptFamily.UNKNOWN),
        classification_factory(domain=ScientificDomain.AI_ML, document_type=DocumentType.RESEARCH_ARTICLE),
    )
    assert family == PromptFamily.COMPUTER_SCIENCE


def test_strategy_selector_pico_first_for_clinical(context_factory, classification_factory, grades_factory, medical_factory):
    strategy = StrategySelector().select(
        context_factory(primary_routing=RoutingDecision.CLINICAL_TRIAL),
        classification_factory(study_design=StudyDesign.RCT),
        grades_factory(skipped=True),
        medical_factory(with_pico=True),
    )
    assert strategy == PromptStrategy.PICO_FIRST


def test_strategy_selector_evidence_based(context_factory, classification_factory, grades_factory, medical_factory):
    strategy = StrategySelector().select(
        context_factory(primary_routing=RoutingDecision.MEDICAL_FULL),
        classification_factory(),
        grades_factory(skipped=False),
        medical_factory(skipped=True, with_pico=False),
    )
    assert strategy == PromptStrategy.EVIDENCE_BASED


def test_section_prioritizer_pico_first(context_factory, classification_factory):
    priorities = SectionPrioritizer().prioritize(
        context_factory(),
        classification_factory(),
        PromptStrategy.PICO_FIRST,
    )
    assert priorities[0] == SectionType.METHODS


def test_pico_is_complete_helper(medical_factory):
    assert pico_is_complete(medical_factory(with_pico=True).pico_elements) is True
    assert pico_is_complete(None) is False
