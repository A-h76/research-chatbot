from backend.document_understanding.enums import SectionType
from backend.medical_understanding.conftest import make_pdf, process_pdf
from backend.medical_understanding.document_index import build_document_index


def test_builds_paragraphs_per_section_with_exact_offsets(tmp_path):
    path = make_pdf(
        tmp_path,
        [
            "A Trial\n\nAbstract\nPatients with diabetes.\n\nMethods\nWe used metformin.\n\nResults\nSignificant effect.\n"
        ],
    )
    document = process_pdf(path)
    index = build_document_index(document)

    methods = index.get_paragraphs(SectionType.METHODS)
    assert methods
    for paragraph in methods:
        assert document.full_text[paragraph.start : paragraph.end] == paragraph.text


def test_methods_results_discussion_convenience_lists_match_sections(tmp_path):
    path = make_pdf(tmp_path, ["A Trial\n\nMethods\nWe did this.\n\nResults\nWe found that.\n"])
    document = process_pdf(path)
    index = build_document_index(document)

    assert index.methods_sections == index.get_paragraphs(SectionType.METHODS)
    assert index.results_sections == index.get_paragraphs(SectionType.RESULTS)


def test_find_text_returns_exact_matches_and_document_range(tmp_path):
    path = make_pdf(tmp_path, ["A Trial\n\nMethods\nWe used metformin for treatment.\n"])
    document = process_pdf(path)
    index = build_document_index(document)

    matches = index.find_text(r"metformin", [SectionType.METHODS])
    assert len(matches) == 1
    match = matches[0]
    start, end = match.document_range
    assert document.full_text[start:end] == "metformin"


def test_find_text_is_cached(tmp_path):
    path = make_pdf(tmp_path, ["A Trial\n\nMethods\nWe used metformin.\n"])
    document = process_pdf(path)
    index = build_document_index(document)

    first = index.find_text(r"metformin", [SectionType.METHODS])
    second = index.find_text(r"metformin", [SectionType.METHODS])
    assert first is second


def test_find_text_no_match_returns_empty_list(tmp_path):
    path = make_pdf(tmp_path, ["A Trial\n\nMethods\nWe used metformin.\n"])
    document = process_pdf(path)
    index = build_document_index(document)
    assert index.find_text(r"nonexistentterm", [SectionType.METHODS]) == []


def test_evidence_for_builds_full_evidence_reference(tmp_path):
    path = make_pdf(tmp_path, ["A Trial\n\nMethods\nWe used metformin.\n"])
    document = process_pdf(path)
    index = build_document_index(document)

    match = index.find_text(r"metformin", [SectionType.METHODS])[0]
    evidence = index.evidence_for(match, confidence=0.9)

    assert evidence.confidence == 0.9
    assert evidence.section == SectionType.METHODS
    assert evidence.page == 1
    start, end = evidence.character_range
    assert document.full_text[start:end] == "metformin"


def test_references_are_wrapped_with_index(tmp_path):
    path = make_pdf(
        tmp_path,
        ["A Trial\n\nReferences\n[1] A citation.\n[2] Another citation.\n"],
    )
    document = process_pdf(path)
    index = build_document_index(document)
    assert [ref.raw_text for ref in index.references] == ["[1] A citation.", "[2] Another citation."]


def test_tables_and_figures_are_always_empty(tmp_path):
    path = make_pdf(tmp_path, ["A Trial\n\nMethods\nSome text.\n"])
    document = process_pdf(path)
    index = build_document_index(document)
    assert index.tables == []
    assert index.figures == []
