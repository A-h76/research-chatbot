"""W3 research skills + W4 chat grounding checks."""

from backend.research.retrieve import PassageHit
from backend.research.skills import get_skill, normalize_skill_id, skill_catalog
from backend.research.verify import verify_chat_grounding


def test_normalize_skill_defaults_and_aliases():
    assert normalize_skill_id(None) == "ask"
    assert normalize_skill_id("SYNTHESIZE") == "synthesize"
    assert normalize_skill_id("nope") == "ask"


def test_get_skill_has_instruction_and_top_k():
    ask = get_skill("ask")
    assert ask.instruction == ""
    assert ask.top_k == 6

    synth = get_skill("synthesize")
    assert "SYNTHESIZE" in synth.instruction
    assert synth.top_k >= ask.top_k

    extract = get_skill("extract")
    assert "PICO" in extract.instruction or "Population" in extract.instruction


def test_skill_catalog_closed_set():
    ids = {s["id"] for s in skill_catalog()}
    assert ids == {"ask", "synthesize", "compare", "extract", "draft"}


def _passage(text: str) -> PassageHit:
    return PassageHit(
        file_id=1,
        file_name="paper.pdf",
        content=text,
        score=0.9,
        chunk_id=1,
        page=2,
        section="Results",
    )


def test_verify_grounding_high_overlap():
    passage = _passage(
        "Kupffer cells regulate hepatic immunity and clear bacterial products "
        "from portal blood in chronic liver disease."
    )
    answer = (
        "Kupffer cells regulate hepatic immunity and help clear bacterial "
        "products from portal blood during chronic liver disease."
    )
    report = verify_chat_grounding(answer, [passage], skill="ask")
    assert report.confidence >= 0.6
    assert report.supported_sentences >= 1
    assert not any("No document passages" in w for w in report.warnings)


def test_verify_grounding_no_passages_warns():
    report = verify_chat_grounding(
        "This claim invents an entire clinical trial outcome.",
        [],
        skill="ask",
    )
    assert report.confidence < 0.3
    assert any("passages" in w.lower() for w in report.warnings)


def test_verify_synthesize_warns_on_few_passages():
    passage = _passage("Sample size was forty patients with cirrhosis.")
    answer = (
        "The study enrolled forty patients with cirrhosis. "
        "Another paper reported conflicting mortality outcomes."
    )
    report = verify_chat_grounding(answer, [passage], skill="synthesize")
    assert any("multi-source" in w.lower() or "Few passages" in w for w in report.warnings)
