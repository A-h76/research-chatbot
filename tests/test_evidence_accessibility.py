"""Stage 4 accessibility structural checks for Evidence Inspector."""

from pathlib import Path


INSPECTOR = Path("frontend/src/features/evidence/components/EvidenceInspectorPanel.tsx")
WRITING_PAGE = Path("frontend/src/features/writing/pages/WritingPage.tsx")


def test_inspector_has_live_region_and_landmark():
    text = INSPECTOR.read_text(encoding="utf-8")
    assert 'aria-label="Evidence inspector"' in text
    assert 'aria-live="polite"' in text
    assert 'role="status"' in text


def test_inspector_mounted_in_writing_studio():
    text = WRITING_PAGE.read_text(encoding="utf-8")
    assert "EvidenceInspectorPanel" in text
    assert 'aria-label="Writing draft editor"' in text


def test_inspector_candidate_and_sufficiency_copy_present():
    text = INSPECTOR.read_text(encoding="utf-8")
    assert "Insufficient evidence" in text
    assert "Candidate" in text
    assert "Link to selection" in text
