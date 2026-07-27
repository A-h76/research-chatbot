from backend.document_understanding.enums import DocumentLanguage
from backend.document_understanding.language import StopwordLanguageDetector

_ENGLISH_TEXT = (
    "The results of the study are presented in this section. We have shown that "
    "the method works well for this and other similar problems. This is the "
    "conclusion that we have reached after these experiments were run by us."
)

_SPANISH_TEXT = (
    "Los resultados del estudio se presentan en esta seccion. Hemos demostrado "
    "que el metodo funciona bien para este y otros problemas similares con los "
    "datos que se han recopilado durante el experimento por nosotros."
)


def test_detects_english():
    result = StopwordLanguageDetector().detect(_ENGLISH_TEXT)
    assert result.language == DocumentLanguage.ENGLISH
    assert result.confidence > 0.0


def test_detects_spanish():
    result = StopwordLanguageDetector().detect(_SPANISH_TEXT)
    assert result.language == DocumentLanguage.SPANISH
    assert result.confidence > 0.0


def test_short_text_is_unknown_with_zero_confidence():
    result = StopwordLanguageDetector().detect("too short")
    assert result.language == DocumentLanguage.UNKNOWN
    assert result.confidence == 0.0


def test_empty_text_is_unknown_with_zero_confidence():
    result = StopwordLanguageDetector().detect("")
    assert result.language == DocumentLanguage.UNKNOWN
    assert result.confidence == 0.0
