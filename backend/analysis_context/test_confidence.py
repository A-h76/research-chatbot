from backend.analysis_context.confidence import compute_confidence
from backend.analysis_context.enums import AudienceType, ComplexityLevel, PromptFamily, PromptStrategy, RoutingDecision
from backend.analysis_context.models import (
    AnalysisProfile,
    DocumentProfile,
    PromptProfile,
    RoutingProfile,
    SectionProfile,
)
from backend.classification.pass2.enums import DocumentType, ScientificDomain, StudyDesign
from backend.document_understanding.enums import SectionType


def _document_profile(confidence: float) -> DocumentProfile:
    return DocumentProfile(
        document_type=DocumentType.RESEARCH_ARTICLE,
        domain=ScientificDomain.MEDICINE,
        study_design=StudyDesign.RCT,
        reporting_guideline=None,
        intended_audience=AudienceType.RESEARCH,
        complexity_level=ComplexityLevel.MODERATE,
        confidence=confidence,
    )


def test_overall_is_plain_mean_of_five_profiles():
    document_profile = _document_profile(0.8)
    section_profile = SectionProfile(section_confidence={SectionType.METHODS: 0.6, SectionType.RESULTS: 1.0})
    analysis_profile = AnalysisProfile(confidence=0.4)
    routing_profile = RoutingProfile(primary_routing=RoutingDecision.MEDICAL_FULL, confidence=0.6)
    prompt_profile = PromptProfile(
        prompt_family=PromptFamily.MEDICAL, prompt_strategy=PromptStrategy.SECTION_BASED, confidence=0.2
    )

    score = compute_confidence(document_profile, section_profile, analysis_profile, routing_profile, prompt_profile)

    assert score.document_profile == 0.8
    assert score.section_profile == 0.8  # mean of 0.6 and 1.0
    assert score.analysis_profile == 0.4
    assert score.routing_profile == 0.6
    assert score.prompt_profile == 0.2
    assert score.overall == (0.8 + 0.8 + 0.4 + 0.6 + 0.2) / 5


def test_section_profile_with_no_sections_contributes_zero():
    document_profile = _document_profile(0.5)
    section_profile = SectionProfile()  # no sections detected at all
    analysis_profile = AnalysisProfile(confidence=0.5)
    routing_profile = RoutingProfile(primary_routing=RoutingDecision.GENERIC, confidence=0.5)
    prompt_profile = PromptProfile(
        prompt_family=PromptFamily.GENERIC, prompt_strategy=PromptStrategy.HYBRID, confidence=0.5
    )

    score = compute_confidence(document_profile, section_profile, analysis_profile, routing_profile, prompt_profile)
    assert score.section_profile == 0.0
