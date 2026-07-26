from backend.document_understanding.models import EvidenceReference
from backend.medical_understanding.deduplicators import deduplicate_by_name, deduplicate_entities
from backend.medical_understanding.enums import ClinicalEntityType, EntityNormalizationStatus
from backend.medical_understanding.models import ClinicalEntity, Intervention

_EVIDENCE = EvidenceReference(
    page=1, section=None, paragraph=0, character_range=(0, 5), text_snippet="x", confidence=0.8
)


def _entity(value: str, confidence: float, synonyms=None) -> ClinicalEntity:
    return ClinicalEntity(
        value=value,
        entity_type=ClinicalEntityType.CONDITION,
        raw_text=value,
        normalization_status=EntityNormalizationStatus.EXACT_MATCH,
        confidence=confidence,
        evidence=_EVIDENCE,
        synonyms=synonyms or [],
    )


def test_deduplicate_entities_keeps_highest_confidence():
    low = _entity("diabetes", 0.4)
    high = _entity("diabetes", 0.9)
    result = deduplicate_entities([low, high])
    assert len(result) == 1
    assert result[0].confidence == 0.9


def test_deduplicate_entities_merges_synonyms_from_both():
    low = _entity("diabetes", 0.4, synonyms=["dm"])
    high = _entity("diabetes", 0.9, synonyms=["diabetes mellitus"])
    result = deduplicate_entities([low, high])
    assert set(result[0].synonyms) == {"dm", "diabetes mellitus"}


def test_deduplicate_entities_normalizes_near_duplicates_together():
    a = _entity("diabetes", 0.5)
    b = _entity("dm", 0.6)  # normalizes to "diabetes mellitus" via synonym match
    result = deduplicate_entities([a, b])
    # "diabetes" fuzzy-matches "diabetes mellitus"; "dm" synonym-matches it too
    assert len(result) == 1


def test_deduplicate_entities_keeps_distinct_concepts_separate():
    a = _entity("diabetes", 0.5)
    b = _entity("hypertension", 0.5)
    result = deduplicate_entities([a, b])
    assert len(result) == 2


def test_deduplicate_by_name_keeps_highest_confidence():
    low = Intervention(name="Metformin", confidence=0.4)
    high = Intervention(name="metformin", confidence=0.8)
    result = deduplicate_by_name([low, high], lambda i: i.name, lambda i: i.confidence)
    assert len(result) == 1
    assert result[0].confidence == 0.8


def test_deduplicate_by_name_ignores_empty_names():
    items = [Intervention(name="", confidence=0.9), Intervention(name="metformin", confidence=0.5)]
    result = deduplicate_by_name(items, lambda i: i.name, lambda i: i.confidence)
    assert len(result) == 1
    assert result[0].name == "metformin"
