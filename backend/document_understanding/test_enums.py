from backend.document_understanding.enums import QualityLevel, SectionType


def test_section_type_from_key_known_value():
    assert SectionType.from_key("methods") is SectionType.METHODS


def test_section_type_from_key_unknown_value_degrades_to_other():
    assert SectionType.from_key("not-a-real-key") is SectionType.OTHER


def test_section_type_from_key_none_degrades_to_other():
    assert SectionType.from_key(None) is SectionType.OTHER


def test_quality_level_from_score_boundaries():
    assert QualityLevel.from_score(0.9) is QualityLevel.EXCELLENT
    assert QualityLevel.from_score(0.85) is QualityLevel.EXCELLENT
    assert QualityLevel.from_score(0.7) is QualityLevel.GOOD
    assert QualityLevel.from_score(0.5) is QualityLevel.FAIR
    assert QualityLevel.from_score(0.2) is QualityLevel.POOR
    assert QualityLevel.from_score(0.0) is QualityLevel.UNUSABLE


def test_enums_serialize_as_plain_strings():
    import json

    assert json.dumps(SectionType.METHODS) == '"methods"'
