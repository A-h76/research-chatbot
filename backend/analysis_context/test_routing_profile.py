from backend.analysis_context.enums import FallbackStrategy, RoutingDecision
from backend.analysis_context.routing_profile import RoutingProfiler
from backend.classification.pass2.enums import DocumentType, ScientificDomain, StudyDesign


def test_medicine_rct_routes_to_clinical_trial(document_factory, classification_factory):
    classification = classification_factory(domain=ScientificDomain.MEDICINE, study_design=StudyDesign.RCT)
    profile = RoutingProfiler().profile(document_factory(), classification)
    assert profile.primary_routing == RoutingDecision.CLINICAL_TRIAL


def test_medicine_systematic_review_routes_to_systematic_review(document_factory, classification_factory):
    classification = classification_factory(
        domain=ScientificDomain.MEDICINE,
        study_design=StudyDesign.SYSTEMATIC_REVIEW,
        document_type=DocumentType.SYSTEMATIC_REVIEW,
    )
    profile = RoutingProfiler().profile(document_factory(), classification)
    assert profile.primary_routing == RoutingDecision.SYSTEMATIC_REVIEW


def test_medicine_other_routes_to_medical_full_when_confident(document_factory, classification_factory):
    classification = classification_factory(
        domain=ScientificDomain.MEDICINE,
        study_design=StudyDesign.COHORT,
        domain_confidence=0.9,
        document_type_confidence=0.9,
    )
    profile = RoutingProfiler().profile(document_factory(), classification)
    assert profile.primary_routing == RoutingDecision.MEDICAL_FULL


def test_medicine_other_routes_to_medical_scoped_when_low_confidence(document_factory, classification_factory):
    classification = classification_factory(
        domain=ScientificDomain.MEDICINE,
        study_design=StudyDesign.COHORT,
        domain_confidence=0.2,
        document_type_confidence=0.2,
    )
    profile = RoutingProfiler().profile(document_factory(), classification)
    assert profile.primary_routing == RoutingDecision.MEDICAL_SCOPED


def test_computer_science_domain_routes_to_computer_science(document_factory, classification_factory):
    classification = classification_factory(domain=ScientificDomain.COMPUTER_SCIENCE)
    profile = RoutingProfiler().profile(document_factory(), classification)
    assert profile.primary_routing == RoutingDecision.COMPUTER_SCIENCE


def test_unknown_domain_routes_to_unknown_with_no_secondary(document_factory, classification_factory):
    classification = classification_factory(domain=ScientificDomain.UNKNOWN)
    profile = RoutingProfiler().profile(document_factory(), classification)
    assert profile.primary_routing == RoutingDecision.UNKNOWN
    assert profile.secondary_routing == []


def test_non_generic_routing_gets_generic_as_secondary(document_factory, classification_factory):
    classification = classification_factory(domain=ScientificDomain.MEDICINE, study_design=StudyDesign.RCT)
    profile = RoutingProfiler().profile(document_factory(), classification)
    assert RoutingDecision.GENERIC in profile.secondary_routing


def test_fallback_strategy_escalates_as_confidence_drops(document_factory, classification_factory):
    high = RoutingProfiler().profile(
        document_factory(), classification_factory(domain_confidence=0.9, document_type_confidence=0.9)
    )
    low = RoutingProfiler().profile(
        document_factory(), classification_factory(domain_confidence=0.1, document_type_confidence=0.1)
    )
    assert high.fallback_strategy == FallbackStrategy.NONE
    assert low.fallback_strategy == FallbackStrategy.MANUAL_REVIEW


def test_priority_weights_decrease_by_pipeline_position(document_factory, classification_factory):
    classification = classification_factory(domain=ScientificDomain.MEDICINE, study_design=StudyDesign.RCT)
    profile = RoutingProfiler().profile(document_factory(), classification)
    weights = [profile.priority_weights[module] for module in profile.module_pipeline]
    assert weights == sorted(weights, reverse=True)
