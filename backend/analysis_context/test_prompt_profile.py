from backend.analysis_context.enums import PromptFamily, PromptStrategy
from backend.analysis_context.prompt_profile import PromptProfiler
from backend.classification.pass2.enums import DocumentType, ScientificDomain, StudyDesign
from backend.document_understanding.enums import SectionType


def test_medicine_rct_gets_clinical_prompt_family(document_factory, classification_factory):
    classification = classification_factory(domain=ScientificDomain.MEDICINE, study_design=StudyDesign.RCT)
    profile = PromptProfiler().profile(document_factory(), classification)
    assert profile.prompt_family == PromptFamily.CLINICAL


def test_medicine_systematic_review_gets_systematic_prompt_family(document_factory, classification_factory):
    classification = classification_factory(
        domain=ScientificDomain.MEDICINE, document_type=DocumentType.SYSTEMATIC_REVIEW
    )
    profile = PromptProfiler().profile(document_factory(), classification)
    assert profile.prompt_family == PromptFamily.SYSTEMATIC


def test_unknown_domain_gets_unknown_prompt_family(document_factory, classification_factory):
    classification = classification_factory(domain=ScientificDomain.UNKNOWN)
    profile = PromptProfiler().profile(document_factory(), classification)
    assert profile.prompt_family == PromptFamily.UNKNOWN


def test_very_long_document_gets_summary_first_strategy(document_factory, classification_factory):
    document = document_factory(word_count=20000, section_count=5)
    profile = PromptProfiler().profile(document, classification_factory())
    assert profile.prompt_strategy == PromptStrategy.SUMMARY_FIRST


def test_zero_word_count_gets_claim_based_strategy(document_factory, classification_factory):
    document = document_factory(word_count=0, section_count=0)
    profile = PromptProfiler().profile(document, classification_factory())
    assert profile.prompt_strategy == PromptStrategy.CLAIM_BASED


def test_well_structured_moderate_document_gets_section_based_strategy(document_factory, classification_factory):
    document = document_factory(word_count=3000, section_count=6)
    profile = PromptProfiler().profile(document, classification_factory())
    assert profile.prompt_strategy == PromptStrategy.SECTION_BASED


def test_research_article_section_priorities_lead_with_results(document_factory, classification_factory):
    classification = classification_factory(document_type=DocumentType.RESEARCH_ARTICLE)
    profile = PromptProfiler().profile(document_factory(), classification)
    assert profile.section_priorities[0] == SectionType.RESULTS


def test_key_themes_reuse_classification_detected_keywords(document_factory, classification_factory):
    classification = classification_factory(detected_keywords=["randomized controlled trial", "consort statement"])
    profile = PromptProfiler().profile(document_factory(), classification)
    assert profile.key_themes == ["randomized controlled trial", "consort statement"]


def test_priority_claims_are_always_empty(document_factory, classification_factory):
    profile = PromptProfiler().profile(document_factory(), classification_factory())
    assert profile.evidence_priorities.priority_claims == []


def test_systematic_review_requires_primary_sources(document_factory, classification_factory):
    classification = classification_factory(document_type=DocumentType.SYSTEMATIC_REVIEW)
    profile = PromptProfiler().profile(document_factory(), classification)
    assert profile.evidence_priorities.require_primary_sources is True


def test_research_article_does_not_require_primary_sources_flag(document_factory, classification_factory):
    classification = classification_factory(document_type=DocumentType.RESEARCH_ARTICLE)
    profile = PromptProfiler().profile(document_factory(), classification)
    assert profile.evidence_priorities.require_primary_sources is False
