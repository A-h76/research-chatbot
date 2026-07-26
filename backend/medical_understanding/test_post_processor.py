from backend.document_understanding.enums import SectionType
from backend.document_understanding.models import EvidenceReference
from backend.medical_understanding.config import MedicalUnderstandingConfig
from backend.medical_understanding.entity_registry import EntityRegistry
from backend.medical_understanding.enums import ClinicalEntityType, EntityNormalizationStatus
from backend.medical_understanding.models import ClinicalEntity, Comparator, Intervention
from backend.medical_understanding.post_processor import post_process


def _ev(paragraph: int = 0) -> EvidenceReference:
    return EvidenceReference(
        page=1,
        section=SectionType.RESULTS,
        paragraph=paragraph,
        character_range=(0, 5),
        text_snippet="x",
        confidence=0.8,
    )


def _entity(value: str, entity_type: ClinicalEntityType, paragraph: int = 0) -> ClinicalEntity:
    return ClinicalEntity(
        value=value,
        entity_type=entity_type,
        raw_text=value,
        normalization_status=EntityNormalizationStatus.EXACT_MATCH,
        confidence=0.8,
        evidence=_ev(paragraph),
    )


def test_merges_entities_from_registry_and_lists_from_extracted():
    registry = EntityRegistry()
    registry.register_entity(_entity("diabetes", ClinicalEntityType.CONDITION))
    extracted = {"interventions": [Intervention(name="metformin", confidence=0.8)]}

    result = post_process(registry, extracted, MedicalUnderstandingConfig())

    assert len(result.clinical_entities) == 1
    assert len(result.interventions) == 1


def test_deduplicates_interventions_by_name_keeping_highest_confidence():
    registry = EntityRegistry()
    extracted = {
        "interventions": [
            Intervention(name="Metformin", confidence=0.4),
            Intervention(name="metformin", confidence=0.9),
        ]
    }
    result = post_process(registry, extracted, MedicalUnderstandingConfig())
    assert len(result.interventions) == 1
    assert result.interventions[0].confidence == 0.9


def test_deduplication_can_be_disabled_via_config():
    registry = EntityRegistry()
    extracted = {
        "comparators": [Comparator(name="placebo", confidence=0.5), Comparator(name="placebo", confidence=0.9)]
    }
    result = post_process(registry, extracted, MedicalUnderstandingConfig(deduplicate_entities=False))
    assert len(result.comparators) == 2


def test_builds_relation_for_co_occurring_drug_and_condition():
    registry = EntityRegistry()
    registry.register_entity(_entity("metformin", ClinicalEntityType.DRUG, paragraph=0))
    registry.register_entity(_entity("diabetes mellitus", ClinicalEntityType.CONDITION, paragraph=0))

    result = post_process(registry, {}, MedicalUnderstandingConfig())

    assert len(result.relations) == 1
    relation = result.relations[0]
    assert relation.subject == "metformin"
    assert relation.object == "diabetes mellitus"


def test_no_relation_for_entities_in_different_paragraphs():
    registry = EntityRegistry()
    registry.register_entity(_entity("metformin", ClinicalEntityType.DRUG, paragraph=0))
    registry.register_entity(_entity("diabetes mellitus", ClinicalEntityType.CONDITION, paragraph=1))

    result = post_process(registry, {}, MedicalUnderstandingConfig())
    assert result.relations == []


def test_relations_are_registered_back_onto_the_registry():
    registry = EntityRegistry()
    registry.register_entity(_entity("metformin", ClinicalEntityType.DRUG))
    registry.register_entity(_entity("diabetes mellitus", ClinicalEntityType.CONDITION))

    post_process(registry, {}, MedicalUnderstandingConfig())
    assert len(registry.relations) == 1


def test_entity_limit_truncates_and_warns():
    registry = EntityRegistry()
    for i in range(5):
        registry.register_entity(_entity(f"condition{i}", ClinicalEntityType.CONDITION, paragraph=i))

    result = post_process(registry, {}, MedicalUnderstandingConfig(max_entities=3))
    assert len(result.clinical_entities) == 3
    assert any("entity count exceeded" in w for w in result.warnings)


def test_missing_extracted_keys_default_to_empty_lists():
    result = post_process(EntityRegistry(), {}, MedicalUnderstandingConfig())
    assert result.populations == []
    assert result.outcomes == []
    assert result.statistical_measures == []
    assert result.key_findings == []
