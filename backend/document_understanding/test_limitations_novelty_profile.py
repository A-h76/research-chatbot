"""Unit tests for limitations_novelty_profile (Paper Analysis 2.5)."""

from backend.document_understanding.limitations_novelty_profile import (
    extract_limitations_novelty_profile,
)


def _du_payload(
    *,
    discussion: str = "",
    abstract: str = "",
    intro: str = "",
    limitations: str = "",
    raw_extra: dict | None = None,
) -> dict:
    headings: dict[str, str] = {}
    types: dict[str, str] = {}
    order: list[str] = []
    normalized: dict[str, str] = {}
    if intro:
        order.append("Introduction")
        headings["Introduction"] = intro
        types["Introduction"] = "introduction"
        normalized["introduction"] = intro
    if discussion:
        order.append("Discussion")
        headings["Discussion"] = discussion
        types["Discussion"] = "discussion"
        normalized["discussion"] = discussion
    if limitations:
        order.append("Limitations")
        headings["Limitations"] = limitations
        types["Limitations"] = "discussion"
        normalized["limitations"] = limitations
    if raw_extra:
        for h, body in raw_extra.items():
            order.append(h)
            headings[h] = body
            types[h] = "other"
    return {
        "metadata": {"abstract": abstract, "title": "Study"},
        "structure": {
            "heading_order": order,
            "raw_headings": headings,
            "section_types": types,
            "normalized_headings": normalized,
        },
    }


def test_extracts_author_stated_limitation_and_future():
    discussion = (
        "A limitation of this study is the single-center enrollment of adults. "
        "Future work should examine longer follow-up in multi-site cohorts."
    )
    out = extract_limitations_novelty_profile(_du_payload(discussion=discussion))
    assert out["has_content"] is True
    assert out["limitations"]
    assert all(i.get("author_stated") is True for i in out["limitations"])
    assert any("single-center" in (i.get("text") or "").lower() for i in out["limitations"])
    assert out["future_work"]
    assert all(i.get("author_stated") is True for i in out["future_work"])


def test_extracts_novelty_from_abstract():
    abstract = (
        "To our knowledge, we present a novel framework for grounded paper analysis. "
        "Unlike prior work, our approach reuses Phase 1 signals."
    )
    out = extract_limitations_novelty_profile(_du_payload(abstract=abstract))
    assert out["novelty"]
    assert all(i.get("author_stated") is True for i in out["novelty"])
    assert any("novel" in (i.get("text") or "").lower() or "to our knowledge" in (i.get("text") or "").lower() for i in out["novelty"])


def test_dedicated_limitations_heading_bullets():
    body = "- Small sample size reduces power.\n- Short follow-up period of 4 weeks."
    out = extract_limitations_novelty_profile(
        _du_payload(raw_extra={"Limitations": body})
    )
    assert len(out["limitations"]) >= 2
    assert all(i.get("author_stated") is True for i in out["limitations"])


def test_research_gap_from_intro():
    intro = (
        "Little is known about how researchers reuse Phase 1 analysis outputs. "
        "This knowledge gap motivates our study."
    )
    out = extract_limitations_novelty_profile(_du_payload(intro=intro))
    assert out["research_gaps"]
    assert all(i.get("author_stated") is True for i in out["research_gaps"])


def test_invent_nothing_on_empty():
    out = extract_limitations_novelty_profile({"metadata": {}, "structure": {}})
    assert out["has_content"] is False
    assert out["limitations"] == []
    assert out["novelty"] == []
    assert out["future_work"] == []
    assert out["research_gaps"] == []


def test_narrative_lists_merge_without_inventing():
    base = _du_payload(discussion="Results are discussed without caveats.")
    narrative = {
        "limitations": ["Authors note incomplete outcome ascertainment."],
        "key_contributions": ["First open evaluation of the pipeline."],
        "future_work": ["Extend to non-English corpora."],
    }
    out = extract_limitations_novelty_profile(base, narrative=narrative)
    assert any("ascertainment" in (i.get("text") or "").lower() for i in out["limitations"])
    assert any(i.get("source") == "narrative" for i in out["novelty"])
    assert any("non-English" in (i.get("text") or "") for i in out["future_work"])


def test_attach_on_pipeline_phases():
    from backend.analysis_pipeline.service import _attach_limitations_novelty_profile

    phases = {
        "document_understanding": _du_payload(
            discussion="We acknowledge several limitations including selection bias in recruitment."
        )
    }
    _attach_limitations_novelty_profile(phases)
    profile = phases["document_understanding"]["limitations_novelty_profile"]
    assert profile["has_content"] is True
    assert profile["limitations"]
