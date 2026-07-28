from pathlib import Path


WRITING_PAGE = Path("d:/chatbot (v1)/frontend/src/features/writing/pages/WritingPage.tsx")


def _text():
    return WRITING_PAGE.read_text(encoding="utf-8")


def test_writing_page_has_live_regions_for_status():
    text = _text()
    assert 'role="status"' in text
    assert 'aria-live="polite"' in text


def test_writing_page_has_alert_for_conflict():
    text = _text()
    assert 'role="alert"' in text
    assert "Another version was saved elsewhere" in text


def test_writing_page_has_editor_and_selector_labels():
    text = _text()
    assert 'aria-label="Select writing document"' in text
    assert 'aria-label="Writing draft editor"' in text

