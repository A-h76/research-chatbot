from backend.classification.pass2.keywords import extract_detected_keywords


def test_extracts_matched_keywords_from_all_four_maps(document_factory):
    document = document_factory(
        title="A Randomized Controlled Trial",
        abstract="We conducted a randomized controlled trial following the consort statement.",
        full_text="This case report describes a patient with a rare disease treated with medicine.",
    )
    keywords = extract_detected_keywords(document)

    assert "randomized controlled trial" in keywords
    assert "we conducted" in keywords
    assert "consort statement" in keywords
    assert "case report" in keywords


def test_deduplicates_and_preserves_first_seen_order(document_factory):
    document = document_factory(full_text="preprint preprint preprint arxiv")
    keywords = extract_detected_keywords(document)
    assert keywords.count("preprint") == 1


def test_no_matches_returns_empty_list(document_factory):
    document = document_factory(full_text="nothing relevant here at all")
    assert extract_detected_keywords(document) == []
