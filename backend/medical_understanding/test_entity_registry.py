import threading

from backend.document_understanding.models import EvidenceReference
from backend.medical_understanding.entity_registry import EntityRegistry
from backend.medical_understanding.enums import ClinicalEntityType, ClinicalRelationType, EntityNormalizationStatus
from backend.medical_understanding.models import ClinicalEntity, ClinicalRelation

_EVIDENCE = EvidenceReference(
    page=1, section=None, paragraph=0, character_range=(0, 5), text_snippet="x", confidence=0.8
)


def _entity(value: str, entity_type: ClinicalEntityType = ClinicalEntityType.CONDITION) -> ClinicalEntity:
    return ClinicalEntity(
        value=value,
        entity_type=entity_type,
        raw_text=value,
        normalization_status=EntityNormalizationStatus.EXACT_MATCH,
        confidence=0.8,
        evidence=_EVIDENCE,
    )


def test_register_and_get_entity():
    registry = EntityRegistry()
    entity = registry.register_entity(_entity("diabetes"))
    assert registry.get_entity("diabetes", ClinicalEntityType.CONDITION) is entity


def test_duplicate_registration_returns_first_registered():
    registry = EntityRegistry()
    first = registry.register_entity(_entity("diabetes"))
    second = registry.register_entity(_entity("diabetes"))
    assert second is first
    assert len(registry.entities) == 1


def test_different_entity_types_are_distinct_keys():
    registry = EntityRegistry()
    registry.register_entity(_entity("ms", ClinicalEntityType.CONDITION))
    registry.register_entity(_entity("ms", ClinicalEntityType.DRUG))
    assert len(registry.entities) == 2


def test_resolve_ambiguity_finds_registered_alternate_meaning():
    registry = EntityRegistry()
    registry.register_entity(_entity("multiple sclerosis"))
    resolved = registry.resolve_ambiguity("MS")
    assert [e.value for e in resolved] == ["multiple sclerosis"]


def test_resolve_ambiguity_empty_for_non_ambiguous_term():
    registry = EntityRegistry()
    assert registry.resolve_ambiguity("diabetes") == []


def test_entities_by_type_filters_correctly():
    registry = EntityRegistry()
    registry.register_entity(_entity("metformin", ClinicalEntityType.DRUG))
    registry.register_entity(_entity("diabetes", ClinicalEntityType.CONDITION))
    drugs = registry.entities_by_type(ClinicalEntityType.DRUG)
    assert [e.value for e in drugs] == ["metformin"]


def test_all_entities_returns_everything():
    registry = EntityRegistry()
    registry.register_entity(_entity("diabetes"))
    registry.register_entity(_entity("metformin", ClinicalEntityType.DRUG))
    assert len(registry.all_entities()) == 2


def test_register_relation_appends():
    registry = EntityRegistry()
    registry.register_relation(ClinicalRelation(subject="a", relation_type=ClinicalRelationType.TREATS, object="b"))
    assert len(registry.relations) == 1


def test_concurrent_registration_of_same_entity_yields_one_winner():
    registry = EntityRegistry()
    results = []

    def worker():
        results.append(registry.register_entity(_entity("diabetes")))

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len({id(r) for r in results}) == 1
    assert len(registry.entities) == 1
