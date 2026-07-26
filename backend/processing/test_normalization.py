"""Tests for backend/processing/normalization.py.

Run: pytest backend/processing/test_normalization.py -v
"""

from backend.processing.normalization import NORMALIZED_SECTIONS, normalize_heading


def test_exact_match_returns_full_confidence():
    match = normalize_heading("Methods")
    assert match.normalized_key == "methods"
    assert match.confidence == 1.0
    assert "exact match" in match.reasoning


def test_exact_match_is_case_insensitive():
    match = normalize_heading("METHODS")
    assert match.normalized_key == "methods"
    assert match.confidence == 1.0


def test_strips_markdown_hash_prefix():
    match = normalize_heading("## Introduction")
    assert match.normalized_key == "introduction"
    assert match.confidence == 1.0


def test_strips_numbered_prefix():
    match = normalize_heading("2.1 Materials and Methods")
    assert match.normalized_key == "methods"
    assert match.confidence == 1.0


def test_strips_roman_numeral_prefix():
    match = normalize_heading("IV. Discussion")
    assert match.normalized_key == "discussion"
    assert match.confidence == 1.0


def test_partial_match_returns_lower_confidence():
    match = normalize_heading("Introduction and Motivation")
    assert match.normalized_key == "introduction"
    assert match.confidence == 0.6
    assert "partial match" in match.reasoning


def test_no_match_returns_none_and_zero_confidence():
    match = normalize_heading("Xyzzy Plugh Foobar")
    assert match.normalized_key is None
    assert match.confidence == 0.0


def test_empty_heading_returns_none():
    match = normalize_heading("")
    assert match.normalized_key is None
    assert match.confidence == 0.0
    assert "empty" in match.reasoning


def test_summary_disambiguates_to_discussion_not_abstract():
    # "summary" is listed under both "discussion" and (as a synonym for)
    # "abstract" in NORMALIZED_SECTIONS — discussion wins, matching the
    # far more common real-paper usage of a closing "Summary" section.
    match = normalize_heading("Summary")
    assert match.normalized_key == "discussion"


def test_abstract_still_reachable_via_its_own_keyword():
    match = normalize_heading("Abstract")
    assert match.normalized_key == "abstract"


def test_new_section_type_is_addable_without_code_changes():
    # Extensibility contract: adding an entry to NORMALIZED_SECTIONS (plus
    # rebuilding the keyword index it's compiled into — the same
    # `normalization._KEYWORD_INDEX = normalization._build_keyword_index()`
    # step a real code change would need to trigger via re-import) is the
    # whole change needed to recognize a new section type. No function in
    # this module or sections.py needs editing.
    from backend.processing import normalization

    NORMALIZED_SECTIONS["ethics"] = ["ethics statement", "ethical considerations"]
    normalization._KEYWORD_INDEX = normalization._build_keyword_index()
    try:
        match = normalize_heading("Ethics Statement")
        assert match.normalized_key == "ethics"
        assert match.confidence == 1.0
    finally:
        del NORMALIZED_SECTIONS["ethics"]
        normalization._KEYWORD_INDEX = normalization._build_keyword_index()
