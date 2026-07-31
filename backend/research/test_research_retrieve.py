"""Tests for Research Engine retrieve + Trust Chat citation payload (W1/W2)."""

from backend.research.citations import passages_to_workspace_references
from backend.research.message_payload import (
    dump_message_sources,
    load_message_sources,
    normalize_sources_for_api,
)
from backend.research.retrieve import PassageHit
from backend.research.scope import ResearchScope


def test_research_scope_for_paper_chat_disables_web():
    scope = ResearchScope.for_chat(
        user_id=1,
        conversation_id=9,
        project_id=None,
        file_id=42,
        search_mode="on",
    )
    assert scope.mode == "paper"
    assert scope.file_id == 42
    assert scope.web == "off"
    assert scope.session_id is None


def test_research_scope_project_mode():
    scope = ResearchScope.for_chat(
        user_id=1,
        conversation_id=9,
        project_id=3,
        file_id=None,
        search_mode="auto",
    )
    assert scope.mode == "project"
    assert scope.web == "auto"


def test_passages_to_workspace_references_clickable():
    hits = [
        PassageHit(
            file_id=7,
            file_name="paper.pdf",
            content="Kupffer cells regulate hepatic immunity.",
            score=0.81,
            chunk_id=101,
            page=4,
            section="Discussion",
        )
    ]
    refs = passages_to_workspace_references(hits, primary_file_id=7)
    assert len(refs) == 1
    r = refs[0]
    assert r["kind"] == "passage"
    assert r["tab"] == "structure"
    assert "p. 4" in r["label"]
    assert "Discussion" in r["label"]
    assert r["href"].startswith("/papers/7?")
    assert "tab=structure" in r["href"]
    assert r["metadata"]["chunk_id"] == 101
    assert "Kupffer" in r["metadata"]["quote_preview"]


def test_message_sources_roundtrip_envelope():
    blob = dump_message_sources(
        web=[{"title": "X", "url": "https://example.com"}],
        references=[{"kind": "passage", "refId": "passage:chunk:1"}],
        scope={"mode": "paper", "file_id": 7, "session_id": None},
    )
    assert blob is not None
    web, refs, scope, grounding = load_message_sources(blob)
    assert web[0]["url"] == "https://example.com"
    assert refs[0]["kind"] == "passage"
    assert scope["mode"] == "paper"
    assert grounding is None

    api = normalize_sources_for_api(blob)
    assert api["sources"][0]["title"] == "X"
    assert api["references"][0]["refId"] == "passage:chunk:1"
    assert api["scope"]["file_id"] == 7


def test_legacy_sources_list_still_loads():
    web, refs, scope, grounding = load_message_sources(
        '[{"title": "Old", "url": "https://legacy.test"}]'
    )
    assert len(web) == 1
    assert refs == []
    assert scope is None
    assert grounding is None
    assert normalize_sources_for_api(web)["sources"][0]["title"] == "Old"


def test_message_sources_with_grounding():
    blob = dump_message_sources(
        web=[],
        references=[{"kind": "passage", "refId": "passage:chunk:1"}],
        scope={"mode": "paper", "file_id": 1},
        grounding={
            "confidence": 0.72,
            "warnings": ["Partial grounding"],
            "skill": "synthesize",
        },
    )
    web, refs, scope, grounding = load_message_sources(blob)
    assert grounding["confidence"] == 0.72
    api = normalize_sources_for_api(blob)
    assert api["confidence"] == 0.72
    assert api["warnings"] == ["Partial grounding"]
    assert api["skill"] == "synthesize"
