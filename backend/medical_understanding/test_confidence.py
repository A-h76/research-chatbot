from backend.document_understanding.enums import SectionType
from backend.document_understanding.models import EvidenceReference
from backend.medical_understanding.confidence import compute_confidence
from backend.medical_understanding.enums import ClinicalEntityType, EntityNormalizationStatus
from backend.medical_understanding.models import ClinicalEntity

_EVIDENCE = EvidenceReference(
    page=1, section=None, paragraph=0, character_range=(0, 5), text_snippet="x", confidence=0.8
)


def _entity(confidence: float, status: EntityNormalizationStatus) -> ClinicalEntity:
    return ClinicalEntity(
        value="x",
        entity_type=ClinicalEntityType.CONDITION,
        raw_text="x",
        normalization_status=status,
        confidence=confidence,
        evidence=_EVIDENCE,
    )


def test_no_entities_and_no_sections_yields_zero_overall():
    score = compute_confidence([], {})
    assert score.overall == 0.0
    assert score.components["section_quality"] == 0.0
    assert score.components["evidence_count"] == 0.0
    assert score.components["keyword_confidence"] == 0.0
    assert score.components["normalization_quality"] == 0.0


def test_empty_section_completeness_yields_zero_section_quality():
    entities = [_entity(0.8, EntityNormalizationStatus.EXACT_MATCH)]
    score = compute_confidence(entities, {})
    assert score.components["section_quality"] == 0.0


def test_section_quality_is_mean_of_completeness_values():
    entities = [_entity(0.8, EntityNormalizationStatus.EXACT_MATCH)]
    score = compute_confidence(entities, {SectionType.METHODS: 1.0, SectionType.RESULTS: 0.0})
    assert score.components["section_quality"] == 0.5


def test_normalization_quality_counts_exact_and_synonym_as_good():
    entities = [
        _entity(0.8, EntityNormalizationStatus.EXACT_MATCH),
        _entity(0.8, EntityNormalizationStatus.SYNONYM_MATCH),
        _entity(0.8, EntityNormalizationStatus.FUZZY_MATCH),
        _entity(0.8, EntityNormalizationStatus.UNKNOWN),
    ]
    score = compute_confidence(entities, {SectionType.METHODS: 1.0})
    assert score.components["normalization_quality"] == 0.5


def test_formula_string_is_present_and_matches_task_spec():
    score = compute_confidence([], {})
    assert (
        score.formula == "0.4*section_quality + 0.3*evidence_count + 0.2*keyword_confidence + 0.1*normalization_quality"
    )


def test_overall_is_clamped_to_zero_one_range():
    entities = [_entity(1.0, EntityNormalizationStatus.EXACT_MATCH) for _ in range(50)]
    score = compute_confidence(entities, {SectionType.METHODS: 1.0})
    assert 0.0 <= score.overall <= 1.0
