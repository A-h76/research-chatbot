"""Tests for DomainRegistry — pure Python, no DB, no fixtures needed
beyond a plain instance.

Run: pytest backend/ai/test_domain_registry.py -v
"""

from backend.ai.domain_registry import DomainRegistry

registry = DomainRegistry()


# ------------------------------------------------------------ detect_domain
def test_detect_domain_by_venue():
    domain = registry.detect_domain(metadata={"venue": "Proceedings of NeurIPS 2024"}, content="")
    assert domain == "ai_ml"


def test_detect_domain_by_venue_case_insensitive():
    domain = registry.detect_domain(metadata={"venue": "THE LANCET"}, content="")
    assert domain == "medical"


def test_detect_domain_by_keyword():
    domain = registry.detect_domain(
        metadata=None,
        content="This randomized clinical trial enrolled 200 patients at a hospital.",
    )
    assert domain == "medical"


def test_detect_domain_by_keyword_ai_ml():
    domain = registry.detect_domain(
        metadata=None,
        content="We train a deep learning model on a benchmark dataset and report accuracy.",
    )
    assert domain == "ai_ml"


def test_detect_domain_user_selection():
    # Even though the content looks like a medical paper, an explicit
    # user_selected wins — highest priority per the detection order.
    domain = registry.detect_domain(
        metadata={"venue": "The Lancet"},
        content="patient hospital treatment",
        user_selected="ai_ml",
    )
    assert domain == "ai_ml"


def test_detect_domain_user_selection_unknown_falls_through():
    # An invalid/typo'd user_selected shouldn't be trusted blindly — it
    # falls through to venue/keyword detection instead of propagating a
    # domain name that doesn't exist in DOMAINS.
    domain = registry.detect_domain(
        metadata={"venue": "NeurIPS"},
        content="",
        user_selected="not-a-real-domain",
    )
    assert domain == "ai_ml"


def test_detect_domain_fallback():
    domain = registry.detect_domain(metadata={}, content="Nothing domain-specific here at all.")
    assert domain == "general"


def test_detect_domain_fallback_with_no_arguments():
    assert registry.detect_domain() == "general"


def test_detect_domain_venue_takes_priority_over_keyword():
    # Venue detection (2nd priority) should win even when the content
    # would keyword-match a different domain (3rd priority).
    domain = registry.detect_domain(
        metadata={"venue": "Cell"},
        content="a randomized clinical trial of patients",
    )
    assert domain == "biology"


# ------------------------------------------------------------ get_domain / list_domains
def test_get_domain_returns_metadata():
    entry = registry.get_domain("medical")
    assert entry["label"] == "Medical and Allied Health Sciences"
    assert entry["prompt_name"] == "domain_medical"


def test_get_domain_returns_none_for_unknown():
    assert registry.get_domain("not-a-domain") is None


def test_list_domains_returns_all_nine():
    assert len(registry.list_domains()) == 9


def test_list_domains_enabled_only_default_true():
    names = {d["name"] for d in registry.list_domains()}
    assert names == set(registry.DOMAINS.keys())


# ------------------------------------------------------------ get_domain_prompt_name
def test_get_domain_prompt_name():
    assert registry.get_domain_prompt_name("biology") == "domain_biology"


def test_get_domain_prompt_name_general_reuses_paper_analysis():
    assert registry.get_domain_prompt_name("general") == "paper_analysis"


def test_get_domain_prompt_name_unknown_returns_none():
    assert registry.get_domain_prompt_name("not-a-domain") is None


# ------------------------------------------------------------ is_domain_available
def test_is_domain_available_true_for_known_enabled_domain():
    assert registry.is_domain_available("chemistry") is True


def test_is_domain_available_false_for_unknown_domain():
    assert registry.is_domain_available("not-a-domain") is False


# ------------------------------------------------------------ detect_document_type
def test_detect_document_type_by_venue():
    doc_type = registry.detect_document_type(metadata={"venue": "NEJM"}, content="")
    assert doc_type == "research"


def test_detect_document_type_by_venue_case_insensitive():
    doc_type = registry.detect_document_type(metadata={"venue": "the new england journal of medicine, nejm"})
    assert doc_type == "research"


def test_detect_document_type_case_report_by_keyword():
    doc_type = registry.detect_document_type(
        content="A 45-year-old man presented with acute chest pain. This case report describes..."
    )
    assert doc_type == "case_report"


def test_detect_document_type_review_by_keyword():
    doc_type = registry.detect_document_type(
        content="We performed a systematic review and meta-analysis of 30 randomized controlled trials."
    )
    assert doc_type == "review"


def test_detect_document_type_clinical_guide_by_keyword():
    doc_type = registry.detect_document_type(
        content="This practical guide walks clinicians step by step through the diagnostic workflow."
    )
    assert doc_type == "clinical_guide"


def test_detect_document_type_editorial_by_keyword():
    doc_type = registry.detect_document_type(content="In this editorial, we share our opinion on the new findings.")
    assert doc_type == "editorial"


def test_detect_document_type_research_by_keyword():
    doc_type = registry.detect_document_type(
        content="This randomized controlled trial followed a cohort of 500 patients."
    )
    assert doc_type == "research"


def test_detect_document_type_checks_title_too():
    doc_type = registry.detect_document_type(
        metadata={"title": "A Case Report of Unusual Presentation"},
        content="No matching keywords in the body text at all.",
    )
    assert doc_type == "case_report"


def test_detect_document_type_only_scans_first_500_chars_of_content():
    # The matching keyword sits well past the 500-char window — content
    # alone shouldn't match; title still can independently.
    padding = "x" * 600
    doc_type = registry.detect_document_type(content=f"{padding} systematic review meta-analysis")
    assert doc_type == "general"


def test_detect_document_type_case_report_beats_generic_research_keyword():
    # "study" (a research keyword) appears alongside "case report" — the
    # more specific type should win, not the first one listed in the task.
    doc_type = registry.detect_document_type(content="This case report describes a rare presentation in a study.")
    assert doc_type == "case_report"


def test_detect_document_type_venue_takes_priority_over_keyword():
    doc_type = registry.detect_document_type(
        metadata={"venue": "NEJM"},
        content="This practical guide explains step by step how to proceed.",
    )
    assert doc_type == "research"


def test_detect_document_type_fallback():
    doc_type = registry.detect_document_type(metadata={}, content="Nothing relevant to any known type here.")
    assert doc_type == "general"


def test_detect_document_type_fallback_with_no_arguments():
    assert registry.detect_document_type() == "general"
