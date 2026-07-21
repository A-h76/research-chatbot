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
        metadata={"venue": "NeurIPS"}, content="", user_selected="not-a-real-domain",
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
        metadata={"venue": "Cell"}, content="a randomized clinical trial of patients",
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
