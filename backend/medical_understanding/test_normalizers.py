from backend.medical_understanding.enums import EntityNormalizationStatus
from backend.medical_understanding.normalizers import normalize


def test_exact_match():
    value, status, synonyms = normalize("Multiple Sclerosis")
    assert value == "multiple sclerosis"
    assert status == EntityNormalizationStatus.EXACT_MATCH
    assert "ms" in synonyms


def test_synonym_match():
    value, status, _ = normalize("MI")
    assert value == "myocardial infarction"
    assert status == EntityNormalizationStatus.SYNONYM_MATCH


def test_ambiguous_abbreviation():
    value, status, synonyms = normalize("MS")
    assert value == "ms"
    assert status == EntityNormalizationStatus.AMBIGUOUS
    assert set(synonyms) == {"multiple sclerosis", "mitral stenosis"}


def test_fuzzy_match_via_containment():
    value, status, _ = normalize("diabetes mellitus type 2")
    assert value == "diabetes mellitus"
    assert status == EntityNormalizationStatus.FUZZY_MATCH


def test_unknown_term():
    value, status, synonyms = normalize("some totally unrecognized phrase")
    assert value == "some totally unrecognized phrase"
    assert status == EntityNormalizationStatus.UNKNOWN
    assert synonyms == []


def test_empty_text_is_unknown():
    value, status, _ = normalize("")
    assert value == ""
    assert status == EntityNormalizationStatus.UNKNOWN
