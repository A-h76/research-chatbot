"""Sprint A — gateway composer + marker extraction + fallback + ACR routing."""

from __future__ import annotations

from backend.ai.ai_ledger import clear_ledger_for_tests, recent_executions
from backend.evidence.writing.gateway_composer import (
    PROMPT_VERSION_LIT_REVIEW,
    PROMPT_VERSION_WRITING,
    extract_allowed_markers,
    make_gateway_composer,
)
from backend.evidence.writing_intelligence import build_writing_intelligence


def _obj(oid: int, **kwargs):
    base = {
        "id": oid,
        "file_id": 9,
        "page": 2,
        "claim": f"Claim {oid} about Drug X",
        "quote": f"Quote {oid}",
        "supports": ["x"],
        "contradicts": [],
        "relation": "supports",
        "confidence_band": "high",
        "study_type": "RCT",
    }
    base.update(kwargs)
    return base


class _FakeGateway:
    def __init__(self, content: str, *, fail: bool = False):
        self.content = content
        self.fail = fail
        self.calls = []

    def call(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("gateway_down")
        return {"content": self.content, "total_tokens": 12, "cost": 0.0}


class _FakeRegistry:
    pass


def test_extract_allowed_markers_strips_unknown_ids():
    text, ids = extract_allowed_markers(
        "Findings improve outcomes [#12][#99] and safety [#17].",
        {12, 17},
    )
    assert ids == [12, 17]
    assert "[#12]" in text and "[#17]" in text
    assert "[#99]" not in text


def test_gateway_composer_requires_markers_and_builds_citations():
    clear_ledger_for_tests()
    gateway = _FakeGateway(
        "Prior trials show HbA1c reductions with Drug X [#1]. "
        "Safety was acceptable at 12 weeks [#2]."
    )
    composer = make_gateway_composer(
        ai_gateway=gateway, model_registry=_FakeRegistry(), mode="balanced"
    )
    paragraph, citations, warnings = composer(
        query={"query_text": "Drug X HbA1c"},
        supporting=[_obj(1), _obj(2)],
        conflict={"has_conflict": False},
        context={
            "title": "Key findings",
            "purpose": "Highlight findings",
            "facet": "consensus",
            "topic": "Drug X",
            "structured_argument": {"theme_clusters": [], "consensus": {}, "conflict": {}},
        },
    )
    assert "[#1]" in paragraph and "[#2]" in paragraph
    assert [c["evidence_id"] for c in citations] == [1, 2]
    assert "gateway_synthesis" in warnings
    assert "acr_routed" in warnings
    assert gateway.calls and gateway.calls[0]["task"] == "section_generator"
    # Capability Router supplies model; gateway must not invent one silently.
    assert gateway.calls[0].get("model")
    prov = composer.acr_last_provenance
    assert prov and prov["ai_execution"]["research_job"] == "writing"
    assert prov["ai_execution"]["prompt_version"] == PROMPT_VERSION_WRITING
    assert prov["ai_execution"]["execution_id"]
    ledger = recent_executions(limit=1)
    assert ledger and ledger[0]["research_job"] == "writing"
    assert ledger[0]["prompt_version"] == PROMPT_VERSION_WRITING
    assert ledger[0]["evaluation"]["citation_markers_ok"] is True


def test_gateway_composer_falls_back_without_markers():
    gateway = _FakeGateway("Nice prose with no citations at all.")
    composer = make_gateway_composer(
        ai_gateway=gateway, model_registry=_FakeRegistry()
    )
    paragraph, citations, warnings = composer(
        query={"query_text": "Drug X", "anchors": {"selected_text": "Drug X"}},
        supporting=[_obj(3)],
        conflict=None,
    )
    assert citations and citations[0]["evidence_id"] == 3
    assert "[#3]" in paragraph
    assert any(w.startswith("gateway_fallback:") for w in warnings)


def test_gateway_composer_falls_back_on_gateway_error():
    gateway = _FakeGateway("", fail=True)
    composer = make_gateway_composer(
        ai_gateway=gateway, model_registry=_FakeRegistry()
    )
    paragraph, citations, warnings = composer(
        query={"query_text": "x"},
        supporting=[_obj(8)],
        conflict=None,
    )
    assert citations[0]["evidence_id"] == 8
    assert any("gateway_fallback" in w for w in warnings)


def test_literature_review_job_routes_and_records_ledger():
    clear_ledger_for_tests()
    gateway = _FakeGateway("Synthesis of Drug X benefit [#1].")
    composer = make_gateway_composer(
        ai_gateway=gateway,
        model_registry=_FakeRegistry(),
        task="literature_review",
        mode="publication",
        project_id=42,
    )
    paragraph, citations, warnings = composer(
        query={"query_text": "Drug X"},
        supporting=[_obj(1)],
        conflict=None,
    )
    assert "[#1]" in paragraph
    assert citations[0]["evidence_id"] == 1
    assert "acr_routed" in warnings
    ai_ex = composer.acr_last_provenance["ai_execution"]
    assert ai_ex["research_job"] == "literature_review"
    assert ai_ex["execution_policy"] == "highest_quality"
    assert ai_ex["prompt_version"] == PROMPT_VERSION_LIT_REVIEW
    entry = recent_executions(limit=1)[0]
    assert entry["extra"].get("project_id") == 42
    assert entry["extra"].get("validation_status") == "cited"


def test_build_writing_uses_gateway_composer_end_to_end():
    clear_ledger_for_tests()
    gateway = _FakeGateway(
        "Themes recur around glycemic benefit [#1][#2]. "
        "Residual uncertainty remains around subgroups [#3]."
    )
    composer = make_gateway_composer(
        ai_gateway=gateway,
        model_registry=_FakeRegistry(),
        task="literature_review",
    )
    objects = [_obj(i) for i in range(1, 7)]
    out = build_writing_intelligence(
        query={
            "query_text": "Drug X HbA1c",
            "section_type": "literature_review",
            "anchors": {"selected_text": "Drug X reduces HbA1c"},
        },
        objects=objects,
        reasoning={"sufficiency": "sufficient", "summary_code": "strong"},
        consensus={
            "label": "strong",
            "supporting_ids": [1, 2, 3, 4, 5, 6],
            "contradicting_ids": [],
        },
        conflict={"has_conflict": False, "mediators": []},
        composer=composer,
    )
    assert out["status"] == "ok"
    assert out["paragraph"]
    assert gateway.calls  # at least one slot used gateway
    assert all(c.get("model") for c in gateway.calls)
    assert composer.acr_last_provenance
    assert composer.acr_last_provenance["ai_execution"]["research_job"] == "literature_review"
    assert recent_executions(limit=5)
    # Binder may strip misaligned markers from the fake shared reply; routing still happened.
    assert any("acr_routed" in (w or "") for s in out["sections"] for w in (s.get("warnings") or []))
