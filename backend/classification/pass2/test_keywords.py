from backend.classification.pass2.keywords import extract_detected_keywords


def test_extracts_domain_topics_not_classifier_chrome(document_factory):
    """Primary Topics must not include type/design/reporting lexicon."""
    document = document_factory(
        title="A Randomized Controlled Trial",
        abstract="We conducted a randomized controlled trial following the consort statement.",
        full_text="This case report describes a patient with a rare disease treated with medicine.",
    )
    keywords = extract_detected_keywords(document)

    assert "patient" in keywords
    assert "disease" in keywords
    assert "medicine" in keywords
    # Document-type / study-design / reporting phrases must stay out.
    assert "randomized controlled trial" not in keywords
    assert "we conducted" not in keywords
    assert "consort statement" not in keywords
    assert "case report" not in keywords


def test_deduplicates_and_preserves_first_seen_order(document_factory):
    document = document_factory(full_text="patient patient patient disease")
    keywords = extract_detected_keywords(document)
    assert keywords.count("patient") == 1
    assert keywords.index("patient") < keywords.index("disease")


def test_no_matches_returns_empty_list(document_factory):
    document = document_factory(full_text="nothing relevant here at all")
    assert extract_detected_keywords(document) == []


def test_excludes_editorial_and_letter_boilerplate(document_factory):
    document = document_factory(
        full_text=(
            "This editorial is in response to prior work. Heterogeneity of findings "
            "is discussed. Gene expression and rna in the organism were reviewed."
        )
    )
    keywords = extract_detected_keywords(document)
    assert "editorial" not in keywords
    assert "in response to" not in keywords
    assert "heterogeneity" not in keywords
    assert "gene expression" in keywords
    assert "rna" in keywords
    assert "organism" in keywords
